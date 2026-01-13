"""
Database access layer for the scheduler service.

Provides read-only access to schedules and write access to executions.
Uses the same SQLite database as the main backend.
"""

import json
import secrets
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List

from .config import config
from .models import Schedule, ScheduleExecution

logger = logging.getLogger(__name__)


class SchedulerDatabase:
    """
    Database access for the scheduler service.

    Thread-safe SQLite access with connection pooling.
    """

    def __init__(self, database_path: str = None):
        """Initialize database with path."""
        self.database_path = database_path or config.database_path
        logger.info(f"Scheduler database initialized: {self.database_path}")

    @contextmanager
    def get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> Schedule:
        """Convert a database row to a Schedule model."""
        return Schedule(
            id=row["id"],
            agent_name=row["agent_name"],
            name=row["name"],
            cron_expression=row["cron_expression"],
            message=row["message"],
            enabled=bool(row["enabled"]),
            timezone=row["timezone"],
            description=row["description"],
            owner_id=row["owner_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None
        )

    @staticmethod
    def _row_to_execution(row: sqlite3.Row) -> ScheduleExecution:
        """Convert a database row to a ScheduleExecution model."""
        row_keys = row.keys()
        return ScheduleExecution(
            id=row["id"],
            schedule_id=row["schedule_id"],
            agent_name=row["agent_name"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
            message=row["message"],
            response=row["response"],
            error=row["error"],
            triggered_by=row["triggered_by"],
            context_used=row["context_used"] if "context_used" in row_keys else None,
            context_max=row["context_max"] if "context_max" in row_keys else None,
            cost=row["cost"] if "cost" in row_keys else None,
            tool_calls=row["tool_calls"] if "tool_calls" in row_keys else None,
            execution_log=row["execution_log"] if "execution_log" in row_keys else None
        )

    # =========================================================================
    # Schedule Read Operations
    # =========================================================================

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()
            return self._row_to_schedule(row) if row else None

    def list_all_enabled_schedules(self) -> List[Schedule]:
        """List all enabled schedules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE enabled = 1
                ORDER BY agent_name, name
            """)
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def list_agent_schedules(self, agent_name: str) -> List[Schedule]:
        """List all schedules for a specific agent."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_schedules WHERE agent_name = ?
                ORDER BY name
            """, (agent_name,))
            return [self._row_to_schedule(row) for row in cursor.fetchall()]

    def get_autonomy_enabled(self, agent_name: str) -> bool:
        """Check if autonomy is enabled for an agent."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT autonomy_enabled FROM agent_ownership WHERE agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            return bool(row["autonomy_enabled"]) if row else False

    # =========================================================================
    # Schedule Update Operations
    # =========================================================================

    def update_schedule_run_times(
        self,
        schedule_id: str,
        last_run_at: datetime = None,
        next_run_at: datetime = None
    ) -> bool:
        """Update schedule run timestamps."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ["updated_at = ?"]
            params = [datetime.utcnow().isoformat()]

            if last_run_at:
                updates.append("last_run_at = ?")
                params.append(last_run_at.isoformat())
            if next_run_at:
                updates.append("next_run_at = ?")
                params.append(next_run_at.isoformat())

            params.append(schedule_id)
            cursor.execute(f"""
                UPDATE agent_schedules SET {", ".join(updates)} WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    # =========================================================================
    # Execution Operations
    # =========================================================================

    def create_execution(
        self,
        schedule_id: str,
        agent_name: str,
        message: str,
        triggered_by: str = "schedule"
    ) -> Optional[ScheduleExecution]:
        """Create a new execution record."""
        execution_id = self._generate_id()
        now = datetime.utcnow().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule_executions (
                    id, schedule_id, agent_name, status, started_at, message, triggered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                schedule_id,
                agent_name,
                "running",
                now,
                message,
                triggered_by
            ))
            conn.commit()

            return ScheduleExecution(
                id=execution_id,
                schedule_id=schedule_id,
                agent_name=agent_name,
                status="running",
                started_at=datetime.fromisoformat(now),
                message=message,
                triggered_by=triggered_by
            )

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        response: str = None,
        error: str = None,
        context_used: int = None,
        context_max: int = None,
        cost: float = None,
        tool_calls: str = None,
        execution_log: str = None
    ) -> bool:
        """Update execution status when completed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get started_at for duration calculation
            cursor.execute("SELECT started_at FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            if not row:
                return False

            started_at = datetime.fromisoformat(row["started_at"])
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            cursor.execute("""
                UPDATE schedule_executions
                SET status = ?, completed_at = ?, duration_ms = ?, response = ?, error = ?,
                    context_used = ?, context_max = ?, cost = ?, tool_calls = ?, execution_log = ?
                WHERE id = ?
            """, (
                status,
                completed_at.isoformat(),
                duration_ms,
                response,
                error,
                context_used,
                context_max,
                cost,
                tool_calls,
                execution_log,
                execution_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
        """Get an execution by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            return self._row_to_execution(row) if row else None

    def get_recent_executions(self, limit: int = 50) -> List[ScheduleExecution]:
        """Get recent executions across all schedules."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schedule_executions
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_execution(row) for row in cursor.fetchall()]
