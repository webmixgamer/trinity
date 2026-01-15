"""
Process Engine Enumerations

Defines the status and type enums used throughout the process engine.
"""

from enum import Enum


class DefinitionStatus(str, Enum):
    """Status of a process definition."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(str, Enum):
    """Types of steps in a process."""
    AGENT_TASK = "agent_task"
    HUMAN_APPROVAL = "human_approval"  # Stub for Core phase
    GATEWAY = "gateway"  # Stub for Core phase
    TIMER = "timer"  # Stub for Advanced phase
    NOTIFICATION = "notification"  # Stub for Advanced phase


class ExecutionStatus(str, Enum):
    """Status of a process execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of a step execution."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OnErrorAction(str, Enum):
    """Action to take when a step fails after all retries."""
    FAIL_PROCESS = "fail_process"
    SKIP_STEP = "skip_step"
    GOTO_STEP = "goto_step"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
