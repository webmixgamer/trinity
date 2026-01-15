"""
Process Engine Domain Entities

Entities are objects with identity that exist within aggregates.

Reference: IT3 Section 4.2 (Entities)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)

from .enums import StepType, StepStatus
from .value_objects import StepId, Duration
from .step_configs import (
    StepConfig,
    AgentTaskConfig,
    HumanApprovalConfig,
    GatewayConfig,
    parse_step_config,
)


@dataclass
class StepDefinition:
    """
    Entity within ProcessDefinition aggregate.
    
    Defines a single step in a process - what it does, 
    what it depends on, and how it's configured.
    """
    id: StepId
    name: str
    type: StepType
    config: StepConfig
    dependencies: list[StepId] = field(default_factory=list)
    condition: Optional[str] = None  # Expression like "{{steps.review.decision}} == 'approved'"
    
    @classmethod
    def from_dict(cls, data: dict) -> StepDefinition:
        """
        Create StepDefinition from dictionary (YAML parsing).
        
        Example YAML:
        ```yaml
        - id: research
          name: Research Topic
          type: agent_task
          agent: research-agent
          message: Research the following topic: {{input.topic}}
          timeout: 5m
        ```
        """
        step_id = StepId(data["id"])
        step_type = StepType(data["type"])
        
        # Parse config based on step type
        # For agent_task, the config is inlined in the step definition
        if step_type == StepType.AGENT_TASK:
            config_data = {
                "agent": data["agent"],
                "message": data["message"],
                "timeout": data.get("timeout", "5m"),
                "model": data.get("model"),
                "temperature": data.get("temperature"),
            }
        elif step_type == StepType.HUMAN_APPROVAL:
            config_data = {
                "title": data.get("title", data.get("name", "Approval Required")),
                "description": data.get("description", ""),
                "assignees": data.get("assignees", []),
                "timeout": data.get("timeout", "24h"),
            }
        elif step_type == StepType.GATEWAY:
            config_data = {
                "gateway_type": data.get("gateway_type", "exclusive"),
                "routes": data.get("routes", []),
                "default_route": data.get("default_route"),
            }
        else:
            # Generic config extraction
            config_data = data.get("config", {})
        
        config = parse_step_config(step_type.value, config_data)
        
        # Parse dependencies
        depends_on = data.get("depends_on", [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        dependencies = [StepId(dep) for dep in depends_on]
        
        return cls(
            id=step_id,
            name=data.get("name", data["id"]),
            type=step_type,
            config=config,
            dependencies=dependencies,
            condition=data.get("condition"),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "type": self.type.value,
        }
        
        # Inline config for agent_task
        if self.type == StepType.AGENT_TASK and isinstance(self.config, AgentTaskConfig):
            result["agent"] = self.config.agent
            result["message"] = self.config.message
            result["timeout"] = str(self.config.timeout)
            if self.config.model:
                result["model"] = self.config.model
            if self.config.temperature is not None:
                result["temperature"] = self.config.temperature
        elif self.type == StepType.HUMAN_APPROVAL and isinstance(self.config, HumanApprovalConfig):
            result["title"] = self.config.title
            result["description"] = self.config.description
            result["assignees"] = self.config.assignees
            result["timeout"] = str(self.config.timeout)
        else:
            result["config"] = self.config.to_dict()
        
        if self.dependencies:
            result["depends_on"] = [str(dep) for dep in self.dependencies]
        
        if self.condition:
            result["condition"] = self.condition
            
        return result


@dataclass
class StepExecution:
    """
    Entity within ProcessExecution aggregate.
    
    Tracks the runtime state of a single step execution.
    """
    step_id: StepId
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[Duration]:
        """Calculate execution duration if completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return Duration(seconds=int(delta.total_seconds()))
        return None
    
    def start(self) -> None:
        """Mark step as running."""
        self.status = StepStatus.RUNNING
        self.started_at = _utcnow()
    
    def complete(self, output: dict[str, Any]) -> None:
        """Mark step as completed with output."""
        self.status = StepStatus.COMPLETED
        self.completed_at = _utcnow()
        self.output = output
    
    def fail(self, error_message: str, error_code: Optional[str] = None) -> None:
        """Mark step as failed with error."""
        self.status = StepStatus.FAILED
        self.completed_at = _utcnow()
        self.error = {
            "message": error_message,
            "code": error_code,
        }
        self.retry_count += 1
    
    def skip(self, reason: str = "Condition not met") -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.completed_at = _utcnow()
        self.output = {"skipped_reason": reason}
    
    def wait_for_approval(self) -> None:
        """Mark step as waiting for human approval."""
        self.status = StepStatus.WAITING_APPROVAL
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "step_id": str(self.step_id),
            "status": self.status.value,
            "retry_count": self.retry_count,
        }
        
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.output:
            result["output"] = self.output
        if self.error:
            result["error"] = self.error
        if self.duration:
            result["duration_seconds"] = self.duration.seconds
            
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> StepExecution:
        """Create from dictionary (deserialization)."""
        execution = cls(
            step_id=StepId(data["step_id"]),
            status=StepStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            output=data.get("output"),
            error=data.get("error"),
        )
        
        if data.get("started_at"):
            execution.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            execution.completed_at = datetime.fromisoformat(data["completed_at"])
            
        return execution


@dataclass
class OutputConfig:
    """
    Configuration for process outputs.
    
    Defines what data should be captured as process output
    and where it should be stored.
    """
    name: str
    source: str  # Expression like "{{steps.final.response}}"
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> OutputConfig:
        """Create from dictionary (YAML parsing)."""
        if isinstance(data, str):
            # Simple format: just the source expression
            return cls(name="output", source=data)
        return cls(
            name=data.get("name", "output"),
            source=data["source"],
            description=data.get("description", ""),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "source": self.source,
            "description": self.description,
        }
