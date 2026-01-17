"""
Human Approval Step Handler

Handles human_approval steps by creating approval requests
and putting the step into a waiting state.

Reference: BACKLOG_CORE.md - E6-01, E6-02
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from ...domain import (
    StepType,
    HumanApprovalConfig,
    ApprovalRequest,
    ApprovalRequested,
)
from ..step_handler import StepHandler, StepResult, StepContext, StepConfig


logger = logging.getLogger(__name__)


class ApprovalStore:
    """
    Simple in-memory store for approval requests.
    In production, this would be backed by a database.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._requests = {}
        return cls._instance
    
    def save(self, request: ApprovalRequest) -> None:
        """Save an approval request."""
        self._requests[request.id] = request
    
    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._requests.get(request_id)
    
    def get_by_execution_step(
        self, execution_id: str, step_id: str
    ) -> Optional[ApprovalRequest]:
        """Get approval request for a specific execution step."""
        for req in self._requests.values():
            if req.execution_id == execution_id and req.step_id == step_id:
                return req
        return None
    
    def get_pending_for_user(self, user: str) -> list[ApprovalRequest]:
        """Get all pending approvals for a user."""
        return [
            req for req in self._requests.values()
            if req.is_pending() and req.can_be_decided_by(user)
        ]
    
    def get_all_pending(self) -> list[ApprovalRequest]:
        """Get all pending approvals."""
        return [req for req in self._requests.values() if req.is_pending()]


# Global store instance
_approval_store = ApprovalStore()


def get_approval_store() -> ApprovalStore:
    """Get the global approval store instance."""
    return _approval_store


class HumanApprovalHandler(StepHandler):
    """
    Handler for human_approval step type.
    
    Creates an approval request and puts the step into
    a waiting state until approval is given via API.
    """
    
    def __init__(self, approval_store: Optional[ApprovalStore] = None):
        """
        Initialize handler.
        
        Args:
            approval_store: Optional store for approval requests.
        """
        self.approval_store = approval_store or get_approval_store()
    
    @property
    def step_type(self) -> StepType:
        return StepType.HUMAN_APPROVAL
    
    async def execute(
        self,
        context: StepContext,
        config: StepConfig,
    ) -> StepResult:
        """
        Execute a human approval step.
        
        Creates an approval request and returns a waiting result.
        The execution engine will pause until the approval is processed.
        """
        if not isinstance(config, HumanApprovalConfig):
            return StepResult.fail(
                f"Invalid config type: {type(config).__name__}",
                error_code="INVALID_CONFIG",
            )
        
        execution_id = str(context.execution.id)
        step_id = str(context.step_definition.id)
        
        # Check if there's already an approval request for this step
        existing = self.approval_store.get_by_execution_step(execution_id, step_id)
        if existing:
            if existing.is_pending():
                # Still waiting for approval
                logger.info(f"Approval still pending for step '{step_id}'")
                return StepResult.wait({"approval_id": existing.id})
            elif existing.status.value == "approved":
                # Already approved - complete the step
                logger.info(f"Approval already completed for step '{step_id}'")
                return StepResult.ok({
                    "approval_id": existing.id,
                    "decision": "approved",
                    "decided_by": existing.decided_by,
                    "comment": existing.decision_comment,
                })
            else:
                # Rejected - fail the step
                return StepResult.fail(
                    f"Approval rejected by {existing.decided_by}: {existing.decision_comment}",
                    error_code="APPROVAL_REJECTED",
                )
        
        # Calculate deadline if timeout is specified
        deadline = None
        if config.timeout:
            deadline = datetime.now(timezone.utc) + timedelta(seconds=config.timeout.seconds)
        
        # Create approval request
        request = ApprovalRequest.create(
            execution_id=execution_id,
            step_id=step_id,
            title=config.title,
            description=config.description,
            assignees=config.assignees,
            deadline=deadline,
        )
        
        # Store the request
        self.approval_store.save(request)
        
        logger.info(
            f"Created approval request '{request.id}' for step '{step_id}' "
            f"(assignees: {config.assignees or 'any'})"
        )
        
        # Return waiting result - the step will be paused
        return StepResult.wait({
            "approval_id": request.id,
            "title": config.title,
            "assignees": config.assignees,
        })
