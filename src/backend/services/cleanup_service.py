"""
Cleanup Service for Trinity platform.

Background service that periodically cleans up stale resources:
- Marks stale executions (running > threshold) as failed
- Marks stale activities (started > threshold) as failed
- Cleans up stale Redis slots

Runs every 5 minutes with a one-shot startup sweep.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict

from database import db
from services.slot_service import get_slot_service

logger = logging.getLogger(__name__)

# Configuration
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
EXECUTION_STALE_TIMEOUT_MINUTES = 120  # SCHED-ASYNC-001: increased from 30 to support long-running tasks
ACTIVITY_STALE_TIMEOUT_MINUTES = 120  # SCHED-ASYNC-001: increased from 30 to support long-running tasks
NO_SESSION_TIMEOUT_SECONDS = 60  # Issue #106: fast-fail executions that never got a Claude session


@dataclass
class CleanupReport:
    """Results from a single cleanup cycle."""
    stale_executions: int = 0
    no_session_executions: int = 0
    orphaned_skipped: int = 0
    stale_activities: int = 0
    stale_slots: int = 0

    @property
    def total(self) -> int:
        return (self.stale_executions + self.no_session_executions +
                self.orphaned_skipped + self.stale_activities + self.stale_slots)

    def to_dict(self) -> Dict:
        return {
            "stale_executions": self.stale_executions,
            "no_session_executions": self.no_session_executions,
            "orphaned_skipped": self.orphaned_skipped,
            "stale_activities": self.stale_activities,
            "stale_slots": self.stale_slots,
            "total": self.total,
        }


class CleanupService:
    """Background service that cleans up stale resources."""

    def __init__(self, poll_interval: int = CLEANUP_INTERVAL_SECONDS):
        self.poll_interval = poll_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.last_run_at: Optional[str] = None
        self.last_report: Optional[CleanupReport] = None

    def start(self):
        """Start the background cleanup loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Cleanup service started (interval={self.poll_interval}s)")

    def stop(self):
        """Stop the background cleanup loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Cleanup service stopped")

    async def run_cleanup(self) -> CleanupReport:
        """Run a single cleanup cycle. Called by loop and on startup."""
        from utils.helpers import utc_now_iso

        report = CleanupReport()

        # 1. Mark stale executions as failed
        try:
            count = db.mark_stale_executions_failed(EXECUTION_STALE_TIMEOUT_MINUTES)
            report.stale_executions = count
            if count > 0:
                logger.info(f"[Cleanup] Marked {count} stale executions as failed")
        except Exception as e:
            logger.error(f"[Cleanup] Error marking stale executions: {e}")

        # 1b. Fast-fail running executions with no Claude session (Issue #106)
        try:
            count = db.mark_no_session_executions_failed(NO_SESSION_TIMEOUT_SECONDS)
            report.no_session_executions = count
            if count > 0:
                logger.info(f"[Cleanup] Marked {count} no-session executions as failed")
        except Exception as e:
            logger.error(f"[Cleanup] Error marking no-session executions: {e}")

        # 1c. Finalize orphaned skipped executions (Issue #106)
        try:
            count = db.finalize_orphaned_skipped_executions()
            report.orphaned_skipped = count
            if count > 0:
                logger.info(f"[Cleanup] Finalized {count} orphaned skipped executions")
        except Exception as e:
            logger.error(f"[Cleanup] Error finalizing orphaned skipped executions: {e}")

        # 2. Mark stale activities as failed
        try:
            count = db.mark_stale_activities_failed(ACTIVITY_STALE_TIMEOUT_MINUTES)
            report.stale_activities = count
            if count > 0:
                logger.info(f"[Cleanup] Marked {count} stale activities as failed")
        except Exception as e:
            logger.error(f"[Cleanup] Error marking stale activities: {e}")

        # 3. Cleanup stale Redis slots
        try:
            slot_service = get_slot_service()
            count = await slot_service.cleanup_stale_slots()
            report.stale_slots = count
        except Exception as e:
            logger.error(f"[Cleanup] Error cleaning stale slots: {e}")

        self.last_run_at = utc_now_iso()
        self.last_report = report

        if report.total > 0:
            logger.info(f"[Cleanup] Cycle complete: {report.to_dict()}")

        return report

    async def _cleanup_loop(self):
        """Main cleanup loop."""
        # Run initial cleanup on startup
        try:
            startup_report = await self.run_cleanup()
            if startup_report.total > 0:
                logger.info(f"[Cleanup] Startup sweep: {startup_report.to_dict()}")
            else:
                logger.info("[Cleanup] Startup sweep: no stale resources found")
        except Exception as e:
            logger.error(f"[Cleanup] Startup sweep error: {e}")

        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

            try:
                await self.run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Cleanup] Cycle error: {e}")


# Global service instance
cleanup_service = CleanupService()
