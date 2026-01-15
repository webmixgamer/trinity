"""
Process Engine Domain Layer

Contains:
- Value Objects (value_objects.py)
- Aggregates (aggregates.py)
- Entities (entities.py)
- Step Configs (step_configs.py)
- Enums (enums.py)
- Domain Events (events.py)
- Domain Exceptions (exceptions.py)
"""

from .value_objects import (
    ProcessId,
    ExecutionId,
    StepId,
    Version,
    Duration,
    Money,
)

from .enums import (
    DefinitionStatus,
    StepType,
    ExecutionStatus,
    StepStatus,
)

from .entities import (
    StepDefinition,
    StepExecution,
    OutputConfig,
)

from .step_configs import (
    StepConfig,
    AgentTaskConfig,
    HumanApprovalConfig,
    GatewayConfig,
    TimerConfig,
    NotificationConfig,
    parse_step_config,
)

from .aggregates import (
    ProcessDefinition,
    ProcessExecution,
)

from .exceptions import (
    ProcessEngineError,
    ProcessDefinitionError,
    ProcessExecutionError,
    ProcessNotFoundError,
    ProcessValidationError,
    CircularDependencyError,
    InvalidStepReferenceError,
    DuplicateStepIdError,
    ExecutionNotFoundError,
    InvalidExecutionStateError,
)

__all__ = [
    # Value Objects
    "ProcessId",
    "ExecutionId",
    "StepId",
    "Version",
    "Duration",
    "Money",
    # Enums
    "DefinitionStatus",
    "StepType",
    "ExecutionStatus",
    "StepStatus",
    # Entities
    "StepDefinition",
    "StepExecution",
    "OutputConfig",
    # Step Configs
    "StepConfig",
    "AgentTaskConfig",
    "HumanApprovalConfig",
    "GatewayConfig",
    "TimerConfig",
    "NotificationConfig",
    "parse_step_config",
    # Aggregates
    "ProcessDefinition",
    "ProcessExecution",
    # Exceptions
    "ProcessEngineError",
    "ProcessDefinitionError",
    "ProcessExecutionError",
    "ProcessNotFoundError",
    "ProcessValidationError",
    "CircularDependencyError",
    "InvalidStepReferenceError",
    "DuplicateStepIdError",
    "ExecutionNotFoundError",
    "InvalidExecutionStateError",
]
