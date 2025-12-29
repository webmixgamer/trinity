"""
Executions Tests (test_executions.py)

Tests for task execution history and persistence.
Covers the Tasks tab functionality and execution tracking.

Feature Flow: tasks-tab.md, execution-queue.md
"""

import pytest
import time
import uuid
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
    assert_list_response,
)


class TestExecutionsEndpoint:
    """Tests for GET /api/agents/{name}/executions endpoint."""

    def test_get_executions_returns_list(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/executions returns a list."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, list), "Executions should be a list"

    def test_get_executions_with_limit(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/executions respects limit parameter."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            params={"limit": 5}
        )

        assert_status(response, 200)
        data = response.json()
        assert len(data) <= 5, "Should respect limit parameter"

    def test_get_executions_nonexistent_agent_returns_404(
        self,
        api_client: TrinityApiClient
    ):
        """GET /api/agents/{name}/executions for non-existent agent returns 404."""
        response = api_client.get("/api/agents/nonexistent-agent-xyz123/executions")
        assert_status(response, 404)

    def test_get_executions_requires_auth(
        self,
        unauthenticated_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/executions requires authentication."""
        response = unauthenticated_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            auth=False
        )
        assert_status(response, 401)


class TestExecutionFields:
    """Tests for execution record structure."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_execution_has_required_fields(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Execution records have expected fields."""
        # First, create an execution by running a task
        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "What is 1+1?"},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)

        # Wait for persistence
        time.sleep(2)

        # Get executions
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        assert len(executions) > 0, "Should have at least one execution"

        # Check fields on most recent execution
        execution = executions[0]
        assert_has_fields(execution, [
            "id",
            "agent_name",
            "status",
            "started_at",
            "message",
            "triggered_by"
        ])

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_successful_execution_has_response(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Successful execution includes response field."""
        # Run a task
        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Say hello"},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)
        time.sleep(2)

        # Get executions
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        # Find successful execution
        successful = [e for e in executions if e.get("status") == "success"]
        if successful:
            execution = successful[0]
            # Response should be present for successful executions
            assert "response" in execution, "Successful execution should have response"


class TestTaskPersistence:
    """Tests for task persistence to database."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_appears_in_executions(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task submitted via /task appears in executions list."""
        # Get initial execution count
        initial_response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            params={"limit": 100}
        )
        initial_count = len(initial_response.json()) if initial_response.status_code == 200 else 0

        # Submit a task with unique message
        unique_id = uuid.uuid4().hex[:8]
        task_message = f"Test persistence task {unique_id}"

        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": task_message},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)

        # Wait for database write
        time.sleep(3)

        # Get executions again
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            params={"limit": 100}
        )
        assert_status(response, 200)
        executions = response.json()

        # Should have more executions now
        assert len(executions) > initial_count, "New execution should be persisted"

        # Find our specific task
        matching = [e for e in executions if task_message in e.get("message", "")]
        assert len(matching) > 0, f"Task '{task_message}' should appear in executions"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_has_manual_trigger(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task submitted via API has triggered_by='manual'."""
        unique_id = uuid.uuid4().hex[:8]
        task_message = f"Manual trigger test {unique_id}"

        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": task_message},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)
        time.sleep(2)

        # Get executions
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        # Find our task
        matching = [e for e in executions if task_message in e.get("message", "")]
        assert len(matching) > 0, "Should find our task"

        execution = matching[0]
        assert execution.get("triggered_by") == "manual", \
            f"Expected triggered_by='manual', got '{execution.get('triggered_by')}'"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_records_duration(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Completed task has duration_ms recorded."""
        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Quick test"},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)
        time.sleep(2)

        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        # Check most recent completed execution
        completed = [e for e in executions if e.get("status") == "success"]
        if completed:
            execution = completed[0]
            duration = execution.get("duration_ms")
            assert duration is not None, "Completed execution should have duration_ms"
            assert duration > 0, "Duration should be positive"

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_records_cost(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Completed task has cost recorded (if available)."""
        task_response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Cost tracking test"},
            timeout=120.0
        )

        if task_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(task_response, 200)
        time.sleep(2)

        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        # Check most recent completed execution
        completed = [e for e in executions if e.get("status") == "success"]
        if completed:
            execution = completed[0]
            # Cost may be null if not tracked, but field should exist
            assert "cost" in execution, "Execution should have cost field"


class TestAgentToAgentTask:
    """Tests for agent-to-agent task execution via X-Source-Agent header."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_task_with_source_agent_header(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task with X-Source-Agent header is accepted."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": "Agent-to-agent test"},
            headers={"X-Source-Agent": "orchestrator-agent"},
            timeout=120.0
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Should work - 200 or 202
        assert_status_in(response, [200, 202])

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_agent_task_has_agent_trigger(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Task with X-Source-Agent has triggered_by='agent'."""
        unique_id = uuid.uuid4().hex[:8]
        task_message = f"Agent trigger test {unique_id}"

        response = api_client.post(
            f"/api/agents/{created_agent['name']}/task",
            json={"message": task_message},
            headers={"X-Source-Agent": "test-orchestrator"},
            timeout=120.0
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        time.sleep(2)

        # Get executions
        exec_response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(exec_response, 200)
        executions = exec_response.json()

        # Find our task
        matching = [e for e in executions if task_message in e.get("message", "")]
        assert len(matching) > 0, "Should find our task"

        execution = matching[0]
        assert execution.get("triggered_by") == "agent", \
            f"Expected triggered_by='agent', got '{execution.get('triggered_by')}'"


class TestExecutionOrdering:
    """Tests for execution list ordering."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_executions_ordered_by_time_desc(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Executions are returned in descending time order (newest first)."""
        # Run two tasks in sequence
        for i in range(2):
            task_response = api_client.post(
                f"/api/agents/{created_agent['name']}/task",
                json={"message": f"Ordering test task {i}"},
                timeout=120.0
            )
            if task_response.status_code == 503:
                pytest.skip("Agent server not ready")
            time.sleep(1)

        time.sleep(2)

        # Get executions
        response = api_client.get(f"/api/agents/{created_agent['name']}/executions")
        assert_status(response, 200)
        executions = response.json()

        if len(executions) >= 2:
            # Check ordering - newer should be first
            timestamps = [e.get("started_at") for e in executions if e.get("started_at")]
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i + 1], \
                    "Executions should be ordered by time descending"


class TestExecutionFiltering:
    """Tests for execution filtering (if implemented)."""

    def test_executions_filter_by_status(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Executions can be filtered by status (if supported)."""
        # Try filtering by status - may not be implemented
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            params={"status": "success"}
        )

        # Should work or be ignored (200 in either case)
        assert_status(response, 200)
        data = response.json()
        assert isinstance(data, list)

    def test_executions_filter_by_triggered_by(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Executions can be filtered by triggered_by (if supported)."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/executions",
            params={"triggered_by": "manual"}
        )

        # Should work or be ignored
        assert_status(response, 200)
        data = response.json()
        assert isinstance(data, list)
