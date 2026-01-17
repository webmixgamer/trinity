"""
Core scheduler service for Trinity platform.

Manages scheduled task execution for agents using APScheduler.
Uses distributed locks to prevent duplicate executions.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Optional, List, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from croniter import croniter
import pytz
import redis

import httpx

from .config import config
from .models import Schedule, ScheduleExecution, SchedulerStatus, ProcessSchedule
from .database import SchedulerDatabase
from .agent_client import get_agent_client, AgentNotReachableError, AgentRequestError
from .locking import get_lock_manager, LockManager

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled task execution for agents.

    Key features:
    - APScheduler with AsyncIO for non-blocking execution
    - Distributed locking to prevent duplicate executions
    - Event publishing for WebSocket compatibility
    """

    def __init__(
        self,
        database: SchedulerDatabase = None,
        lock_manager: LockManager = None,
        redis_url: str = None
    ):
        """
        Initialize the scheduler service.

        Args:
            database: Database access instance
            lock_manager: Distributed lock manager
            redis_url: Redis URL for event publishing
        """
        self.db = database or SchedulerDatabase()
        self.lock_manager = lock_manager or get_lock_manager()
        self.redis_url = redis_url or config.redis_url

        self.scheduler: Optional[AsyncIOScheduler] = None
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._instance_id: str = f"scheduler-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    @property
    def redis(self) -> redis.Redis:
        """Get or create Redis connection for events."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def initialize(self):
        """Initialize the scheduler and load all enabled schedules."""
        if self._initialized:
            logger.warning("Scheduler already initialized")
            return

        # Ensure process schedules table exists
        self.db.ensure_process_schedules_table()

        # Create scheduler with memory job store
        jobstores = {
            'default': MemoryJobStore()
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone=pytz.UTC
        )

        # Load all enabled agent schedules from database
        schedules = self.db.list_all_enabled_schedules()
        for schedule in schedules:
            self._add_job(schedule)

        # Load all enabled process schedules from database
        process_schedules = self.db.list_all_enabled_process_schedules()
        for process_schedule in process_schedules:
            self._add_process_job(process_schedule)

        # Start the scheduler
        self.scheduler.start()
        self._initialized = True
        self._start_time = datetime.utcnow()

        logger.info(f"Scheduler initialized with {len(schedules)} agent schedules, {len(process_schedules)} process schedules")
        logger.info(f"Instance ID: {self._instance_id}")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._initialized = False
            logger.info("Scheduler shutdown")

        if self._redis:
            self._redis.close()
            self._redis = None

        self.lock_manager.close()

    async def run_forever(self):
        """Run the scheduler until interrupted."""
        self.initialize()

        try:
            # Keep the service running with periodic heartbeat
            while True:
                self.lock_manager.set_heartbeat(self._instance_id)
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Scheduler received cancel signal")
        finally:
            self.shutdown()

    # =========================================================================
    # Job Management
    # =========================================================================

    def _get_job_id(self, schedule_id: str) -> str:
        """Generate a unique job ID for APScheduler."""
        return f"schedule_{schedule_id}"

    def _parse_cron(self, cron_expression: str) -> Dict:
        """
        Parse a cron expression into APScheduler CronTrigger kwargs.

        Format: minute hour day month day_of_week
        Examples:
          - "0 9 * * *" = Every day at 9:00 AM
          - "*/15 * * * *" = Every 15 minutes
          - "0 0 * * 0" = Every Sunday at midnight
        """
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}. Expected 5 parts.")

        return {
            'minute': parts[0],
            'hour': parts[1],
            'day': parts[2],
            'month': parts[3],
            'day_of_week': parts[4]
        }

    def _add_job(self, schedule: Schedule):
        """Add a schedule as an APScheduler job."""
        if not self.scheduler:
            return

        job_id = self._get_job_id(schedule.id)

        try:
            # Parse cron expression
            cron_kwargs = self._parse_cron(schedule.cron_expression)

            # Create timezone-aware trigger
            timezone = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC
            trigger = CronTrigger(timezone=timezone, **cron_kwargs)

            # Add the job
            self.scheduler.add_job(
                self._execute_schedule,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                replace_existing=True,
                name=f"{schedule.agent_name}:{schedule.name}"
            )

            # Calculate and store next run time
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            if next_run:
                self.db.update_schedule_run_times(schedule.id, next_run_at=next_run)

            logger.info(f"Added schedule job: {job_id} ({schedule.name}) for agent {schedule.agent_name}")
        except Exception as e:
            logger.error(f"Failed to add schedule job {job_id}: {e}")

    def _remove_job(self, schedule_id: str):
        """Remove a schedule job from APScheduler."""
        if not self.scheduler:
            return

        job_id = self._get_job_id(schedule_id)
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove schedule job {job_id}: {e}")

    def _get_next_run_time(self, cron_expression: str, timezone: str = "UTC") -> Optional[datetime]:
        """Calculate the next run time for a cron expression."""
        try:
            tz = pytz.timezone(timezone) if timezone else pytz.UTC
            now = datetime.now(tz)
            cron = croniter(cron_expression, now)
            next_time = cron.get_next(datetime)
            return next_time
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            return None

    # =========================================================================
    # Schedule Execution
    # =========================================================================

    async def _execute_schedule(self, schedule_id: str):
        """
        Execute a scheduled task.

        This is called by APScheduler when a schedule is due.
        Uses distributed locking to prevent duplicate executions.
        """
        # Try to acquire lock - if failed, another instance is executing
        lock = self.lock_manager.try_acquire_schedule_lock(schedule_id)
        if not lock:
            logger.info(f"Schedule {schedule_id} already being executed by another instance")
            return

        try:
            await self._execute_schedule_with_lock(schedule_id)
        finally:
            lock.release()

    async def _execute_schedule_with_lock(self, schedule_id: str):
        """Execute schedule after acquiring lock."""
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        if not schedule.enabled:
            logger.info(f"Schedule {schedule_id} is disabled, skipping")
            return

        # Check if agent has autonomy enabled
        if not self.db.get_autonomy_enabled(schedule.agent_name):
            logger.info(f"Schedule {schedule_id} skipped: agent {schedule.agent_name} autonomy is disabled")
            return

        logger.info(f"Executing schedule: {schedule.name} for agent {schedule.agent_name}")

        # Create execution record
        execution = self.db.create_execution(
            schedule_id=schedule.id,
            agent_name=schedule.agent_name,
            message=schedule.message,
            triggered_by="schedule"
        )

        if not execution:
            logger.error(f"Failed to create execution record for schedule {schedule_id}")
            return

        # Broadcast execution started
        await self._publish_event({
            "type": "schedule_execution_started",
            "agent": schedule.agent_name,
            "schedule_id": schedule.id,
            "execution_id": execution.id,
            "schedule_name": schedule.name
        })

        try:
            # Send task to agent
            client = get_agent_client(schedule.agent_name)
            task_response = await client.task(schedule.message, execution_id=execution.id)

            # Update execution status with parsed response
            self.db.update_execution_status(
                execution_id=execution.id,
                status="success",
                response=task_response.response_text,
                context_used=task_response.metrics.context_used,
                context_max=task_response.metrics.context_max,
                cost=task_response.metrics.cost_usd,
                tool_calls=task_response.metrics.tool_calls_json,
                execution_log=task_response.metrics.execution_log_json
            )

            # Update schedule last run time
            now = datetime.utcnow()
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            self.db.update_schedule_run_times(schedule.id, last_run_at=now, next_run_at=next_run)

            logger.info(f"Schedule {schedule.name} executed successfully")

            # Broadcast execution completed
            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "success"
            })

        except AgentNotReachableError as e:
            error_msg = f"Agent not reachable: {str(e)}"
            logger.error(f"Schedule {schedule.name} execution failed: {error_msg}")

            self.db.update_execution_status(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Schedule {schedule.name} execution failed: {error_msg}")

            self.db.update_execution_status(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "schedule_execution_completed",
                "agent": schedule.agent_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

    # =========================================================================
    # Schedule Management (for runtime updates)
    # =========================================================================

    def add_schedule(self, schedule: Schedule):
        """Add a new schedule to the scheduler."""
        if schedule.enabled:
            self._add_job(schedule)

    def remove_schedule(self, schedule_id: str):
        """Remove a schedule from the scheduler."""
        self._remove_job(schedule_id)

    def update_schedule(self, schedule: Schedule):
        """Update an existing schedule in the scheduler."""
        self._remove_job(schedule.id)
        if schedule.enabled:
            self._add_job(schedule)

    def reload_schedules(self):
        """Reload all schedules from the database."""
        if not self.scheduler:
            return

        # Remove all existing jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("schedule_") or job.id.startswith("process_schedule_"):
                self.scheduler.remove_job(job.id)

        # Reload agent schedules from database
        schedules = self.db.list_all_enabled_schedules()
        for schedule in schedules:
            self._add_job(schedule)

        # Reload process schedules from database
        process_schedules = self.db.list_all_enabled_process_schedules()
        for process_schedule in process_schedules:
            self._add_process_job(process_schedule)

        logger.info(f"Reloaded {len(schedules)} agent schedules, {len(process_schedules)} process schedules")

    # =========================================================================
    # Process Schedule Management
    # =========================================================================

    def _get_process_job_id(self, schedule_id: str) -> str:
        """Generate a unique job ID for process schedules."""
        return f"process_schedule_{schedule_id}"

    def _add_process_job(self, schedule: ProcessSchedule):
        """Add a process schedule as an APScheduler job."""
        if not self.scheduler:
            return

        job_id = self._get_process_job_id(schedule.id)

        try:
            # Parse cron expression
            cron_kwargs = self._parse_cron(schedule.cron_expression)

            # Create timezone-aware trigger
            timezone = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC
            trigger = CronTrigger(timezone=timezone, **cron_kwargs)

            # Add the job
            self.scheduler.add_job(
                self._execute_process_schedule,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                replace_existing=True,
                name=f"process:{schedule.process_name}:{schedule.trigger_id}"
            )

            # Calculate and store next run time
            next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
            if next_run:
                self.db.update_process_schedule_run_times(schedule.id, next_run_at=next_run)

            logger.info(f"Added process schedule job: {job_id} ({schedule.process_name}/{schedule.trigger_id})")
        except Exception as e:
            logger.error(f"Failed to add process schedule job {job_id}: {e}")

    def _remove_process_job(self, schedule_id: str):
        """Remove a process schedule job from APScheduler."""
        if not self.scheduler:
            return

        job_id = self._get_process_job_id(schedule_id)
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed process schedule job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove process schedule job {job_id}: {e}")

    async def _execute_process_schedule(self, schedule_id: str):
        """
        Execute a scheduled process.

        This is called by APScheduler when a process schedule is due.
        Uses distributed locking to prevent duplicate executions.
        """
        # Try to acquire lock - if failed, another instance is executing
        lock = self.lock_manager.try_acquire_schedule_lock(f"process_{schedule_id}")
        if not lock:
            logger.info(f"Process schedule {schedule_id} already being executed by another instance")
            return

        try:
            await self._execute_process_schedule_with_lock(schedule_id)
        finally:
            lock.release()

    async def _execute_process_schedule_with_lock(self, schedule_id: str):
        """Execute process schedule after acquiring lock."""
        schedule = self.db.get_process_schedule(schedule_id)
        if not schedule:
            logger.error(f"Process schedule {schedule_id} not found")
            return

        if not schedule.enabled:
            logger.info(f"Process schedule {schedule_id} is disabled, skipping")
            return

        logger.info(f"Executing process schedule: {schedule.process_name}/{schedule.trigger_id}")

        # Create execution record
        execution = self.db.create_process_schedule_execution(
            schedule_id=schedule.id,
            process_id=schedule.process_id,
            process_name=schedule.process_name,
            triggered_by="schedule"
        )

        if not execution:
            logger.error(f"Failed to create execution record for process schedule {schedule_id}")
            return

        # Broadcast execution started
        await self._publish_event({
            "type": "process_schedule_execution_started",
            "process_id": schedule.process_id,
            "process_name": schedule.process_name,
            "schedule_id": schedule.id,
            "trigger_id": schedule.trigger_id,
            "execution_id": execution.id
        })

        try:
            # Call backend API to start process execution
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.backend_url}/api/processes/{schedule.process_id}/execute",
                    json={
                        "triggered_by": "schedule",
                        "input_data": {
                            "trigger": {
                                "type": "schedule",
                                "id": schedule.trigger_id,
                                "schedule_id": schedule.id,
                            }
                        }
                    },
                    timeout=60.0
                )

                if response.status_code == 200 or response.status_code == 201:
                    result = response.json()
                    process_execution_id = result.get("id")

                    # Update execution status
                    self.db.update_process_schedule_execution(
                        execution_id=execution.id,
                        status="success",
                        process_execution_id=process_execution_id
                    )

                    # Update schedule last run time
                    now = datetime.utcnow()
                    next_run = self._get_next_run_time(schedule.cron_expression, schedule.timezone)
                    self.db.update_process_schedule_run_times(schedule.id, last_run_at=now, next_run_at=next_run)

                    logger.info(f"Process schedule {schedule.process_name}/{schedule.trigger_id} executed successfully, execution_id={process_execution_id}")

                    # Broadcast execution completed
                    await self._publish_event({
                        "type": "process_schedule_execution_completed",
                        "process_id": schedule.process_id,
                        "process_name": schedule.process_name,
                        "schedule_id": schedule.id,
                        "execution_id": execution.id,
                        "process_execution_id": process_execution_id,
                        "status": "success"
                    })

                else:
                    error_msg = f"Backend returned {response.status_code}: {response.text[:200]}"
                    logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

                    self.db.update_process_schedule_execution(
                        execution_id=execution.id,
                        status="failed",
                        error=error_msg
                    )

                    await self._publish_event({
                        "type": "process_schedule_execution_completed",
                        "process_id": schedule.process_id,
                        "process_name": schedule.process_name,
                        "schedule_id": schedule.id,
                        "execution_id": execution.id,
                        "status": "failed",
                        "error": error_msg
                    })

        except httpx.TimeoutException:
            error_msg = "Backend request timed out"
            logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

            self.db.update_process_schedule_execution(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "process_schedule_execution_completed",
                "process_id": schedule.process_id,
                "process_name": schedule.process_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Process schedule {schedule.process_name} execution failed: {error_msg}")

            self.db.update_process_schedule_execution(
                execution_id=execution.id,
                status="failed",
                error=error_msg
            )

            await self._publish_event({
                "type": "process_schedule_execution_completed",
                "process_id": schedule.process_id,
                "process_name": schedule.process_name,
                "schedule_id": schedule.id,
                "execution_id": execution.id,
                "status": "failed",
                "error": error_msg
            })

    def add_process_schedule(self, schedule: ProcessSchedule):
        """Add a new process schedule to the scheduler."""
        if schedule.enabled:
            self._add_process_job(schedule)

    def remove_process_schedule(self, schedule_id: str):
        """Remove a process schedule from the scheduler."""
        self._remove_process_job(schedule_id)

    def update_process_schedule(self, schedule: ProcessSchedule):
        """Update an existing process schedule in the scheduler."""
        self._remove_process_job(schedule.id)
        if schedule.enabled:
            self._add_process_job(schedule)

    # =========================================================================
    # Event Publishing
    # =========================================================================

    async def _publish_event(self, event: dict):
        """
        Publish an event to Redis for WebSocket compatibility.

        Events are published to a channel that the backend can subscribe to.
        """
        if not config.publish_events:
            return

        try:
            event_json = json.dumps(event)
            self.redis.publish("scheduler:events", event_json)
            logger.debug(f"Published event: {event['type']}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    # =========================================================================
    # Status & Health
    # =========================================================================

    def get_status(self) -> SchedulerStatus:
        """Get current scheduler status."""
        if not self.scheduler:
            return SchedulerStatus(
                running=False,
                jobs_count=0,
                last_check=datetime.utcnow(),
                uptime_seconds=0
            )

        jobs = self.scheduler.get_jobs()
        uptime = (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0

        return SchedulerStatus(
            running=self.scheduler.running,
            jobs_count=len(jobs),
            last_check=datetime.utcnow(),
            uptime_seconds=uptime,
            jobs=[
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        )

    def is_healthy(self) -> bool:
        """Check if the scheduler is healthy."""
        if not self._initialized:
            return False
        if not self.scheduler or not self.scheduler.running:
            return False
        return True
