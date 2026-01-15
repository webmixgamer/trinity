"""
Process Engine Step Configurations

Configuration classes for different step types.
These are Value Objects that define step behavior.

Reference: IT3 Section 4.3 (Value Objects - StepConfig)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .value_objects import Duration


@dataclass(frozen=True)
class AgentTaskConfig:
    """
    Configuration for agent_task step type.
    
    Defines which agent to use and what message to send.
    """
    agent: str  # Agent name to execute the task
    message: str  # Message/prompt to send to agent (supports {{}} templating)
    timeout: Duration = field(default_factory=lambda: Duration.from_minutes(5))
    
    # Optional: specific model or parameters
    model: Optional[str] = None
    temperature: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> AgentTaskConfig:
        """Create from dictionary (YAML parsing)."""
        timeout = data.get("timeout", "5m")
        if isinstance(timeout, str):
            timeout = Duration.from_string(timeout)
        elif isinstance(timeout, int):
            timeout = Duration.from_seconds(timeout)
        
        return cls(
            agent=data["agent"],
            message=data["message"],
            timeout=timeout,
            model=data.get("model"),
            temperature=data.get("temperature"),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "agent": self.agent,
            "message": self.message,
            "timeout": str(self.timeout),
        }
        if self.model:
            result["model"] = self.model
        if self.temperature is not None:
            result["temperature"] = self.temperature
        return result


@dataclass(frozen=True)
class HumanApprovalConfig:
    """
    Configuration for human_approval step type (stub for Core phase).
    
    Defines approval requirements and assignees.
    """
    title: str  # Title shown in approval UI
    description: str  # Description of what needs approval
    assignees: list[str] = field(default_factory=list)  # User IDs or emails
    timeout: Duration = field(default_factory=lambda: Duration.from_hours(24))
    
    # Options for approval
    allow_comments: bool = True
    require_reason_on_reject: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> HumanApprovalConfig:
        """Create from dictionary (YAML parsing)."""
        timeout = data.get("timeout", "24h")
        if isinstance(timeout, str):
            timeout = Duration.from_string(timeout)
        elif isinstance(timeout, int):
            timeout = Duration.from_seconds(timeout)
            
        return cls(
            title=data.get("title", "Approval Required"),
            description=data.get("description", ""),
            assignees=data.get("assignees", []),
            timeout=timeout,
            allow_comments=data.get("allow_comments", True),
            require_reason_on_reject=data.get("require_reason_on_reject", True),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "assignees": self.assignees,
            "timeout": str(self.timeout),
            "allow_comments": self.allow_comments,
            "require_reason_on_reject": self.require_reason_on_reject,
        }


@dataclass(frozen=True)
class GatewayConfig:
    """
    Configuration for gateway step type (stub for Core phase).
    
    Defines conditional routing based on expressions.
    """
    gateway_type: str = "exclusive"  # exclusive, parallel, inclusive
    routes: list[dict] = field(default_factory=list)  # List of {condition, target}
    default_route: Optional[str] = None  # Default target if no condition matches
    
    @classmethod
    def from_dict(cls, data: dict) -> GatewayConfig:
        """Create from dictionary (YAML parsing)."""
        return cls(
            gateway_type=data.get("gateway_type", "exclusive"),
            routes=data.get("routes", []),
            default_route=data.get("default_route"),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "gateway_type": self.gateway_type,
            "routes": self.routes,
        }
        if self.default_route:
            result["default_route"] = self.default_route
        return result


@dataclass(frozen=True)
class TimerConfig:
    """
    Configuration for timer step type (stub for Advanced phase).
    
    Defines delays or scheduled execution.
    """
    delay: Duration = field(default_factory=lambda: Duration.from_minutes(1))
    
    @classmethod
    def from_dict(cls, data: dict) -> TimerConfig:
        """Create from dictionary (YAML parsing)."""
        delay = data.get("delay", "1m")
        if isinstance(delay, str):
            delay = Duration.from_string(delay)
        elif isinstance(delay, int):
            delay = Duration.from_seconds(delay)
        return cls(delay=delay)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {"delay": str(self.delay)}


@dataclass(frozen=True)
class NotificationConfig:
    """
    Configuration for notification step type (stub for Advanced phase).
    
    Defines notification targets and message.
    """
    channel: str = "email"  # email, slack, webhook
    recipients: list[str] = field(default_factory=list)
    template: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> NotificationConfig:
        """Create from dictionary (YAML parsing)."""
        return cls(
            channel=data.get("channel", "email"),
            recipients=data.get("recipients", []),
            template=data.get("template", ""),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "channel": self.channel,
            "recipients": self.recipients,
            "template": self.template,
        }


# Type alias for step configuration
StepConfig = AgentTaskConfig | HumanApprovalConfig | GatewayConfig | TimerConfig | NotificationConfig


# =============================================================================
# Trigger Configurations
# =============================================================================


@dataclass(frozen=True)
class WebhookTriggerConfig:
    """
    Configuration for webhook triggers.
    
    Allows processes to be started via HTTP POST.
    
    Reference: BACKLOG_CORE.md - E8-01
    """
    id: str  # Unique trigger ID (used in webhook URL)
    enabled: bool = True
    secret: Optional[str] = None  # Optional secret for authentication
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "WebhookTriggerConfig":
        """Create from dictionary (YAML parsing)."""
        return cls(
            id=data.get("id", ""),
            enabled=data.get("enabled", True),
            secret=data.get("secret"),
            description=data.get("description", ""),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "type": "webhook",
            "id": self.id,
            "enabled": self.enabled,
            "description": self.description,
        }
        # Don't serialize secret in output
        return result


@dataclass(frozen=True)
class ScheduleTriggerConfig:
    """
    Configuration for scheduled triggers (stub for Advanced phase).
    
    Allows processes to run on a cron schedule.
    """
    id: str
    cron: str = ""  # Cron expression (e.g., "0 9 * * 1-5")
    enabled: bool = True
    timezone: str = "UTC"
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleTriggerConfig":
        """Create from dictionary (YAML parsing)."""
        return cls(
            id=data.get("id", ""),
            cron=data.get("cron", ""),
            enabled=data.get("enabled", True),
            timezone=data.get("timezone", "UTC"),
            description=data.get("description", ""),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "type": "schedule",
            "id": self.id,
            "cron": self.cron,
            "enabled": self.enabled,
            "timezone": self.timezone,
            "description": self.description,
        }


# Type alias for trigger configurations
TriggerConfig = WebhookTriggerConfig | ScheduleTriggerConfig


def parse_trigger_config(trigger_data: dict) -> TriggerConfig:
    """
    Parse trigger configuration based on type.
    
    Args:
        trigger_data: Dictionary with trigger configuration
        
    Returns:
        Appropriate TriggerConfig subclass instance
    """
    trigger_type = trigger_data.get("type", "webhook")
    
    if trigger_type == "webhook":
        return WebhookTriggerConfig.from_dict(trigger_data)
    elif trigger_type == "schedule":
        return ScheduleTriggerConfig.from_dict(trigger_data)
    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")


def parse_step_config(step_type: str, config_data: dict) -> StepConfig:
    """
    Parse step configuration based on step type.
    
    Args:
        step_type: The type of step (agent_task, human_approval, etc.)
        config_data: Dictionary with configuration data
        
    Returns:
        Appropriate StepConfig subclass instance
    """
    parsers = {
        "agent_task": AgentTaskConfig.from_dict,
        "human_approval": HumanApprovalConfig.from_dict,
        "gateway": GatewayConfig.from_dict,
        "timer": TimerConfig.from_dict,
        "notification": NotificationConfig.from_dict,
    }
    
    parser = parsers.get(step_type)
    if not parser:
        raise ValueError(f"Unknown step type: {step_type}")
    
    return parser(config_data)
