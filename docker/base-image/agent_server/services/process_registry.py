"""
Process Registry for tracking running subprocess handles.

Enables termination of executions by execution_id.
Used by both Claude Code and Gemini runtimes.
"""

import signal
import subprocess
import logging
from datetime import datetime
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class ProcessRegistry:
    """
    Registry for tracking running subprocess handles.
    Enables termination of executions by execution_id.

    Thread-safe via mutex lock for all operations.
    """

    def __init__(self):
        self._processes: Dict[str, dict] = {}
        self._lock = Lock()

    def register(self, execution_id: str, process: subprocess.Popen, metadata: dict = None):
        """
        Register a running process.

        Args:
            execution_id: Unique identifier for this execution
            process: The subprocess.Popen handle
            metadata: Optional metadata (type, message preview, etc.)
        """
        with self._lock:
            self._processes[execution_id] = {
                "process": process,
                "started_at": datetime.utcnow(),
                "metadata": metadata or {}
            }
            logger.info(f"[ProcessRegistry] Registered execution {execution_id}")

    def unregister(self, execution_id: str):
        """Unregister a completed process."""
        with self._lock:
            if execution_id in self._processes:
                del self._processes[execution_id]
                logger.info(f"[ProcessRegistry] Unregistered execution {execution_id}")

    def terminate(self, execution_id: str, graceful_timeout: int = 5) -> dict:
        """
        Terminate a running process.

        Uses graceful termination (SIGINT) first, then force kills (SIGKILL)
        if the process doesn't respond within the timeout.

        Args:
            execution_id: The execution to terminate
            graceful_timeout: Seconds to wait after SIGINT before SIGKILL

        Returns:
            dict with termination status:
            - {"success": True, "returncode": int} on success
            - {"success": False, "reason": "not_found"} if not registered
            - {"success": False, "reason": "already_finished", "returncode": int}
            - {"success": False, "reason": "error", "error": str}
        """
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return {"success": False, "reason": "not_found"}

            process = entry["process"]
            if process.poll() is not None:
                # Already finished
                returncode = process.returncode
                del self._processes[execution_id]
                return {"success": False, "reason": "already_finished", "returncode": returncode}

        # Terminate outside lock to avoid blocking other operations
        try:
            # Graceful termination first (SIGINT = Ctrl+C)
            # Claude Code handles SIGINT gracefully, finishing current tool
            logger.info(f"[ProcessRegistry] Sending SIGINT to execution {execution_id}")
            process.send_signal(signal.SIGINT)

            try:
                process.wait(timeout=graceful_timeout)
                logger.info(f"[ProcessRegistry] Execution {execution_id} terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful didn't work
                logger.warning(f"[ProcessRegistry] Force killing execution {execution_id}")
                process.kill()
                process.wait(timeout=2)

            returncode = process.returncode

            with self._lock:
                if execution_id in self._processes:
                    del self._processes[execution_id]

            return {"success": True, "returncode": returncode}

        except Exception as e:
            logger.error(f"[ProcessRegistry] Error terminating {execution_id}: {e}")
            return {"success": False, "reason": "error", "error": str(e)}

    def get_status(self, execution_id: str) -> Optional[dict]:
        """
        Get status of a registered process.

        Returns None if execution not found.
        """
        with self._lock:
            entry = self._processes.get(execution_id)
            if not entry:
                return None

            process = entry["process"]
            poll_result = process.poll()

            return {
                "execution_id": execution_id,
                "running": poll_result is None,
                "returncode": poll_result,
                "started_at": entry["started_at"].isoformat(),
                "metadata": entry["metadata"]
            }

    def list_running(self) -> list:
        """List all currently running executions."""
        with self._lock:
            result = []
            for exec_id, entry in self._processes.items():
                process = entry["process"]
                if process.poll() is None:
                    result.append({
                        "execution_id": exec_id,
                        "started_at": entry["started_at"].isoformat(),
                        "metadata": entry["metadata"]
                    })
            return result

    def cleanup_finished(self) -> int:
        """
        Remove entries for finished processes.

        Returns the count of cleaned up entries.
        """
        with self._lock:
            finished = [
                exec_id for exec_id, entry in self._processes.items()
                if entry["process"].poll() is not None
            ]
            for exec_id in finished:
                del self._processes[exec_id]
            if finished:
                logger.info(f"[ProcessRegistry] Cleaned up {len(finished)} finished processes")
            return len(finished)


# Global instance
_process_registry: Optional[ProcessRegistry] = None


def get_process_registry() -> ProcessRegistry:
    """Get the global process registry instance."""
    global _process_registry
    if _process_registry is None:
        _process_registry = ProcessRegistry()
    return _process_registry
