"""
Execution Queue Service for Trinity platform.

Implements platform-level queueing to prevent parallel execution on the same agent.
Only one execution can run per agent at a time; additional requests are queued.

Redis-backed for:
- Multi-worker support (uvicorn with multiple workers)
- Persistence across backend restarts
- Already deployed infrastructure (reuse existing Redis)

Queue Rules:
- One execution at a time per agent (enforced at platform level)
- Queue max 3 waiting requests per agent
- Reject (429) if queue full
- Timeout queued requests after 120s of waiting
- Track source (user/schedule/agent) for observability
"""

import json
import logging
from datetime import datetime
from typing import Optional, List
import redis
import uuid

from models import Execution, ExecutionSource, ExecutionStatus, QueueStatus

logger = logging.getLogger(__name__)

# Configuration
MAX_QUEUE_SIZE = 3           # Max queued requests per agent
EXECUTION_TTL = 600          # 10 minutes max execution time (Redis TTL)
QUEUE_WAIT_TIMEOUT = 120     # 120 seconds max wait in queue


class QueueFullError(Exception):
    """Raised when an agent's queue is full."""
    def __init__(self, agent_name: str, queue_length: int):
        self.agent_name = agent_name
        self.queue_length = queue_length
        super().__init__(f"Agent '{agent_name}' queue is full ({queue_length} waiting)")


class AgentBusyError(Exception):
    """Raised when an agent is busy and caller doesn't want to wait."""
    def __init__(self, agent_name: str, current_execution: Optional[Execution] = None):
        self.agent_name = agent_name
        self.current_execution = current_execution
        super().__init__(f"Agent '{agent_name}' is currently executing")


class ExecutionQueue:
    """
    Redis-backed execution queue for agents.

    Ensures only one execution runs per agent at a time.
    Additional requests are queued (up to MAX_QUEUE_SIZE) or rejected.
    """

    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.running_prefix = "agent:running:"
        self.queue_prefix = "agent:queue:"

    def _running_key(self, agent_name: str) -> str:
        """Redis key for currently running execution."""
        return f"{self.running_prefix}{agent_name}"

    def _queue_key(self, agent_name: str) -> str:
        """Redis key for waiting queue (list)."""
        return f"{self.queue_prefix}{agent_name}"

    def _serialize_execution(self, execution: Execution) -> str:
        """Serialize execution to JSON for Redis storage."""
        return execution.model_dump_json()

    def _deserialize_execution(self, data: str) -> Execution:
        """Deserialize execution from JSON."""
        return Execution.model_validate_json(data)

    def create_execution(
        self,
        agent_name: str,
        message: str,
        source: ExecutionSource,
        source_agent: Optional[str] = None,
        source_user_id: Optional[str] = None,
        source_user_email: Optional[str] = None
    ) -> Execution:
        """Create a new execution request (not yet submitted)."""
        return Execution(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            source=source,
            source_agent=source_agent,
            source_user_id=source_user_id,
            source_user_email=source_user_email,
            message=message,
            queued_at=datetime.utcnow(),
            status=ExecutionStatus.QUEUED
        )

    async def submit(
        self,
        execution: Execution,
        wait_if_busy: bool = True
    ) -> tuple[str, Execution]:
        """
        Submit execution request for an agent.

        Args:
            execution: The execution request to submit
            wait_if_busy: If True, queue the request if busy. If False, raise AgentBusyError.

        Returns:
            Tuple of (status, execution):
            - ("running", execution) - Started immediately
            - ("queued:N", execution) - Queued at position N

        Raises:
            QueueFullError: If queue is at MAX_QUEUE_SIZE
            AgentBusyError: If wait_if_busy=False and agent is busy
        """
        running_key = self._running_key(execution.agent_name)
        queue_key = self._queue_key(execution.agent_name)

        # Check if agent is free
        current = self.redis.get(running_key)
        if current is None:
            # Agent is free - start immediately
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            self.redis.set(running_key, self._serialize_execution(execution), ex=EXECUTION_TTL)
            logger.info(f"[Queue] Agent '{execution.agent_name}' execution started: {execution.id}")
            return ("running", execution)

        # Agent is busy
        if not wait_if_busy:
            current_exec = self._deserialize_execution(current)
            raise AgentBusyError(execution.agent_name, current_exec)

        # Check queue length
        queue_len = self.redis.llen(queue_key)
        if queue_len >= MAX_QUEUE_SIZE:
            logger.warning(f"[Queue] Agent '{execution.agent_name}' queue full ({queue_len} waiting)")
            raise QueueFullError(execution.agent_name, queue_len)

        # Add to queue (left push for FIFO - rpop will get oldest)
        self.redis.lpush(queue_key, self._serialize_execution(execution))
        position = queue_len + 1
        logger.info(f"[Queue] Agent '{execution.agent_name}' execution queued at position {position}: {execution.id}")
        return (f"queued:{position}", execution)

    async def complete(self, agent_name: str, success: bool = True) -> Optional[Execution]:
        """
        Mark current execution done and start next if queued.

        Args:
            agent_name: The agent that completed execution
            success: Whether execution succeeded

        Returns:
            Next execution that was started (if any), or None
        """
        running_key = self._running_key(agent_name)
        queue_key = self._queue_key(agent_name)

        # Get and log completed execution
        completed = self.redis.get(running_key)
        if completed:
            completed_exec = self._deserialize_execution(completed)
            status = "completed" if success else "failed"
            logger.info(f"[Queue] Agent '{agent_name}' execution {status}: {completed_exec.id}")

        # Get next from queue (right pop for FIFO)
        next_item = self.redis.rpop(queue_key)
        if next_item:
            next_exec = self._deserialize_execution(next_item)
            next_exec.status = ExecutionStatus.RUNNING
            next_exec.started_at = datetime.utcnow()
            self.redis.set(running_key, self._serialize_execution(next_exec), ex=EXECUTION_TTL)
            logger.info(f"[Queue] Agent '{agent_name}' starting next execution: {next_exec.id}")
            return next_exec
        else:
            # No more in queue - clear running state
            self.redis.delete(running_key)
            logger.info(f"[Queue] Agent '{agent_name}' queue empty, now idle")
            return None

    async def get_status(self, agent_name: str) -> QueueStatus:
        """Get current queue status for an agent."""
        running_key = self._running_key(agent_name)
        queue_key = self._queue_key(agent_name)

        # Get current execution
        running = self.redis.get(running_key)
        current_execution = self._deserialize_execution(running) if running else None

        # Get queued executions
        queue_items = self.redis.lrange(queue_key, 0, -1)
        queued_executions = [self._deserialize_execution(item) for item in queue_items]
        # Reverse to show oldest first (FIFO order)
        queued_executions.reverse()

        return QueueStatus(
            agent_name=agent_name,
            is_busy=current_execution is not None,
            current_execution=current_execution,
            queue_length=len(queued_executions),
            queued_executions=queued_executions
        )

    async def is_busy(self, agent_name: str) -> bool:
        """Check if agent is currently executing."""
        running_key = self._running_key(agent_name)
        return self.redis.exists(running_key) > 0

    async def clear_queue(self, agent_name: str) -> int:
        """
        Clear all queued executions for an agent (not current execution).

        Returns the number of cleared items.
        """
        queue_key = self._queue_key(agent_name)
        count = self.redis.llen(queue_key)
        if count > 0:
            self.redis.delete(queue_key)
            logger.info(f"[Queue] Cleared {count} queued executions for agent '{agent_name}'")
        return count

    async def force_release(self, agent_name: str) -> bool:
        """
        Force release an agent (emergency use - clears running state).

        Use this if an execution is stuck or the agent died without completing.
        Returns True if there was a running execution.
        """
        running_key = self._running_key(agent_name)
        existed = self.redis.exists(running_key) > 0
        if existed:
            self.redis.delete(running_key)
            logger.warning(f"[Queue] Force released agent '{agent_name}' from running state")
        return existed

    async def get_all_busy_agents(self) -> List[str]:
        """Get list of all agents currently executing."""
        pattern = f"{self.running_prefix}*"
        keys = self.redis.keys(pattern)
        agents = [key.replace(self.running_prefix, "") for key in keys]
        return agents


# Global instance (initialized on import if Redis is available)
_execution_queue: Optional[ExecutionQueue] = None


def get_execution_queue() -> ExecutionQueue:
    """Get the global execution queue instance."""
    global _execution_queue
    if _execution_queue is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        _execution_queue = ExecutionQueue(redis_url)
    return _execution_queue
