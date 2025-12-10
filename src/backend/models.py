"""
Pydantic models for the Trinity backend API.
"""
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class AgentConfig(BaseModel):
    """Configuration for creating a new agent."""
    name: str
    type: Optional[str] = "business-assistant"
    base_image: str = "trinity-agent-base:latest"
    resources: Optional[dict] = {"cpu": "2", "memory": "4g"}
    tools: Optional[List[str]] = ["filesystem", "web_search"]
    mcp_servers: Optional[List[str]] = []
    custom_instructions: Optional[str] = None
    port: Optional[int] = None  # SSH port (auto-assigned if None)
    template: Optional[str] = None  # Template to initialize agent from
    # GitHub-native agent support
    github_repo: Optional[str] = None  # GitHub repo (e.g., "Abilityai/agent-ruby")
    github_credential_id: Optional[str] = None  # Credential ID for GitHub PAT


class AgentStatus(BaseModel):
    """Status of an agent container."""
    name: str
    type: str
    status: str
    port: int  # SSH port only - UI no longer exposed externally
    created: datetime
    resources: dict
    container_id: Optional[str] = None
    template: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class User(BaseModel):
    """Authenticated user."""
    id: int
    username: str
    email: Optional[str] = None
    role: str = "user"


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str


class Auth0TokenExchange(BaseModel):
    """Request model for Auth0 token exchange."""
    auth0_token: str


class BulkCredentialImport(BaseModel):
    """Request model for bulk credential import."""
    content: str  # .env-style content: KEY=VALUE pairs


class BulkCredentialResult(BaseModel):
    """Result of bulk credential import."""
    created: int
    skipped: int
    errors: List[str]
    credentials: List[dict]


class HotReloadCredentialsRequest(BaseModel):
    """Request model for hot-reloading credentials."""
    credentials_text: str  # .env-style KEY=VALUE text


class ChatMessageRequest(BaseModel):
    """Request model for chat messages."""
    message: str
    model: Optional[str] = None  # Model alias: sonnet, opus, haiku, or full model name


class ModelChangeRequest(BaseModel):
    """Request model for changing agent's model."""
    model: str  # Model alias: sonnet, opus, haiku, or full model name


# ============================================================================
# Activity Stream Models
# ============================================================================

class ActivityType(str, Enum):
    """Types of activities that can be tracked."""
    # Chat activities
    CHAT_START = "chat_start"
    CHAT_END = "chat_end"
    TOOL_CALL = "tool_call"

    # Schedule activities
    SCHEDULE_START = "schedule_start"
    SCHEDULE_END = "schedule_end"

    # Collaboration activities
    AGENT_COLLABORATION = "agent_collaboration"

    # Future activity types (not yet implemented)
    FILE_ACCESS = "file_access"
    MODEL_CHANGE = "model_change"
    CREDENTIAL_RELOAD = "credential_reload"
    GIT_SYNC = "git_sync"


class ActivityState(str, Enum):
    """State of an activity."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ActivityCreate(BaseModel):
    """Request model for creating a new activity."""
    agent_name: str
    activity_type: ActivityType
    activity_state: ActivityState = ActivityState.STARTED
    parent_activity_id: Optional[str] = None
    user_id: Optional[int] = None
    triggered_by: str = "user"  # user, schedule, agent, system
    related_chat_message_id: Optional[str] = None
    related_execution_id: Optional[str] = None
    details: Optional[Dict] = None
    error: Optional[str] = None


class Activity(BaseModel):
    """Activity record from database."""
    id: str
    agent_name: str
    activity_type: str
    activity_state: str
    parent_activity_id: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    user_id: Optional[int] = None
    triggered_by: str
    related_chat_message_id: Optional[str] = None
    related_execution_id: Optional[str] = None
    details: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Execution Queue Models (Parallel Execution Prevention)
# ============================================================================

class ExecutionSource(str, Enum):
    """Source of an execution request."""
    USER = "user"       # User chat via UI
    SCHEDULE = "schedule"  # Scheduled task
    AGENT = "agent"     # Agent-to-agent via MCP


class ExecutionStatus(str, Enum):
    """Status of an execution request."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Execution(BaseModel):
    """
    Represents an execution request in the agent queue.

    Used to track and serialize requests for platform-level queuing.
    Only one execution can run per agent at a time.
    """
    id: str                                    # UUID
    agent_name: str
    source: ExecutionSource
    source_agent: Optional[str] = None         # If source == AGENT
    source_user_id: Optional[str] = None       # User who triggered
    source_user_email: Optional[str] = None    # User email for tracking
    message: str                               # The chat message
    queued_at: datetime
    started_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.QUEUED

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class QueueStatus(BaseModel):
    """Status of an agent's execution queue."""
    agent_name: str
    is_busy: bool
    current_execution: Optional[Execution] = None
    queue_length: int
    queued_executions: List[Execution] = []
