"""
Process Engine Repository Interfaces

Abstract base classes defining the repository contracts.

Reference: IT3 Section 7 (Repositories)
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    ProcessId,
    ExecutionId,
    Version,
    DefinitionStatus,
    ExecutionStatus,
)


class ProcessDefinitionRepository(ABC):
    """
    Repository interface for process definitions.
    
    Stores and retrieves process definitions. Definitions are identified
    by both their unique ID and by name+version combination.
    """

    @abstractmethod
    def save(self, definition: ProcessDefinition) -> None:
        """
        Save or update a process definition.
        
        If a definition with the same ID exists, it will be updated.
        Otherwise, a new definition is created.
        """
        ...

    @abstractmethod
    def get_by_id(self, id: ProcessId) -> Optional[ProcessDefinition]:
        """
        Get definition by its unique ID.
        
        Returns None if not found.
        """
        ...

    @abstractmethod
    def get_by_name(
        self,
        name: str,
        version: Optional[Version] = None
    ) -> Optional[ProcessDefinition]:
        """
        Get definition by name, optionally for a specific version.
        
        If version is not specified, returns the latest published version.
        Returns None if not found.
        """
        ...

    @abstractmethod
    def get_latest_version(self, name: str) -> Optional[ProcessDefinition]:
        """
        Get the latest published version of a process by name.
        
        Returns None if no published version exists.
        """
        ...

    @abstractmethod
    def list_all(
        self,
        status: Optional[DefinitionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessDefinition]:
        """
        List all definitions, optionally filtered by status.
        
        Results are ordered by updated_at descending.
        """
        ...

    @abstractmethod
    def list_by_name(self, name: str) -> list[ProcessDefinition]:
        """
        List all versions of a process by name.
        
        Returns all versions (draft, published, archived) ordered by version.
        """
        ...

    @abstractmethod
    def delete(self, id: ProcessId) -> bool:
        """
        Delete a process definition by ID.
        
        Returns True if deleted, False if not found.
        """
        ...

    @abstractmethod
    def exists(self, id: ProcessId) -> bool:
        """
        Check if a definition exists by ID.
        """
        ...

    @abstractmethod
    def count(self, status: Optional[DefinitionStatus] = None) -> int:
        """
        Count definitions, optionally filtered by status.
        """
        ...


class ProcessExecutionRepository(ABC):
    """
    Repository interface for process executions.
    
    Stores and retrieves execution state. Executions track the runtime
    state of a process instance.
    """

    @abstractmethod
    def save(self, execution: ProcessExecution) -> None:
        """
        Save execution state.
        
        Called after each state change (step start, step complete, etc.)
        """
        ...

    @abstractmethod
    def get_by_id(self, id: ExecutionId) -> Optional[ProcessExecution]:
        """
        Get execution by ID.
        
        Returns None if not found.
        """
        ...

    @abstractmethod
    def get_active_for_process(self, process_id: ProcessId) -> list[ProcessExecution]:
        """
        Get all active (running/paused) executions for a process.
        """
        ...

    @abstractmethod
    def get_history(
        self,
        process_id: ProcessId,
        limit: int = 100
    ) -> list[ProcessExecution]:
        """
        Get execution history for a process.
        
        Returns recent executions ordered by started_at descending.
        """
        ...

    @abstractmethod
    def list_by_status(
        self,
        status: ExecutionStatus,
        limit: int = 100
    ) -> list[ProcessExecution]:
        """
        List executions by status.
        """
        ...

    @abstractmethod
    def delete(self, id: ExecutionId) -> bool:
        """
        Delete an execution by ID.
        
        Returns True if deleted, False if not found.
        """
        ...
