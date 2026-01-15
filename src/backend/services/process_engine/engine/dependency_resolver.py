"""
Dependency Resolver

Determines execution order based on step dependencies.
Implements topological sorting for dependency resolution.

Reference: IT3 Section 6 (Domain Services - DependencyResolver)
"""

from typing import Optional

from ..domain import (
    ProcessDefinition,
    ProcessExecution,
    StepDefinition,
    StepId,
    StepStatus,
)


class DependencyResolver:
    """
    Resolves step execution order based on dependencies.
    
    Uses the step dependencies defined in the process definition
    to determine which steps are ready to execute.
    """
    
    def __init__(self, definition: ProcessDefinition):
        """
        Initialize resolver with a process definition.
        
        Args:
            definition: The process definition to resolve
        """
        self.definition = definition
        self._step_map = {str(step.id): step for step in definition.steps}
    
    def get_ready_steps(self, execution: ProcessExecution) -> list[StepId]:
        """
        Get steps that are ready to execute.
        
        A step is ready when:
        1. It has not started yet (PENDING status)
        2. All its dependencies are COMPLETED
        
        Args:
            execution: Current execution state
            
        Returns:
            List of step IDs ready to execute
        """
        ready = []
        completed_steps = set(execution.get_completed_step_ids())
        
        for step in self.definition.steps:
            step_exec = execution.step_executions.get(str(step.id))
            
            # Skip if not pending
            if step_exec is None or step_exec.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = all(
                str(dep) in completed_steps
                for dep in step.dependencies
            )
            
            if deps_satisfied:
                ready.append(step.id)
        
        return ready
    
    def get_next_step(self, execution: ProcessExecution) -> Optional[StepId]:
        """
        Get the next step to execute (for sequential execution).
        
        Returns the first ready step, or None if no steps are ready.
        
        Args:
            execution: Current execution state
            
        Returns:
            Next step ID to execute, or None
        """
        ready = self.get_ready_steps(execution)
        return ready[0] if ready else None
    
    def get_execution_order(self) -> list[StepId]:
        """
        Get the full execution order using topological sort.
        
        Returns steps in an order that respects all dependencies.
        
        Returns:
            List of step IDs in execution order
        """
        # Build in-degree map
        in_degree = {str(step.id): 0 for step in self.definition.steps}
        for step in self.definition.steps:
            for dep in step.dependencies:
                # Count how many steps depend on each step
                pass
            in_degree[str(step.id)] = len(step.dependencies)
        
        # Find steps with no dependencies (in-degree 0)
        queue = [
            step.id for step in self.definition.steps
            if in_degree[str(step.id)] == 0
        ]
        
        result = []
        while queue:
            # Take first step
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree for dependent steps
            for step in self.definition.steps:
                if current in step.dependencies:
                    in_degree[str(step.id)] -= 1
                    if in_degree[str(step.id)] == 0:
                        queue.append(step.id)
        
        return result
    
    def get_step_definition(self, step_id: StepId) -> Optional[StepDefinition]:
        """
        Get step definition by ID.
        
        Args:
            step_id: Step ID to look up
            
        Returns:
            StepDefinition or None if not found
        """
        return self._step_map.get(str(step_id))
    
    def is_complete(self, execution: ProcessExecution) -> bool:
        """
        Check if execution is complete.
        
        Returns True if all steps are completed or skipped.
        
        Args:
            execution: Current execution state
            
        Returns:
            True if all steps are done
        """
        return execution.all_steps_completed()
    
    def has_failed_steps(self, execution: ProcessExecution) -> bool:
        """
        Check if execution has any failed steps.
        
        Args:
            execution: Current execution state
            
        Returns:
            True if any step has failed
        """
        return len(execution.get_failed_step_ids()) > 0
