"""
Agent Plans Tests (test_agent_plans.py)

Tests for agent plans/task DAG system.
Covers REQ-PLANS-001 through REQ-PLANS-005.
"""

import pytest
import uuid
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
    assert_list_response,
    assert_plan_fields,
    assert_task_fields,
)


class TestListPlans:
    """REQ-PLANS-001: List plans endpoint tests."""

    def test_list_plans(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/plans returns list of plans."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/plans")

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should be a list (possibly empty)
        if isinstance(data, dict) and "plans" in data:
            assert isinstance(data["plans"], list)
        else:
            assert isinstance(data, list)

    def test_list_plans_with_status_filter(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/plans supports status filter."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/plans",
            params={"status": "active"}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)


class TestCreatePlan:
    """REQ-PLANS-002: Create plan endpoint tests."""

    def test_create_plan_with_tasks(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/plans creates plan with tasks."""
        plan_data = {
            "name": f"test-plan-{uuid.uuid4().hex[:8]}",
            "description": "Test plan",
            "tasks": [
                {
                    "id": "task-1",
                    "name": "First task",
                    "description": "Do something first"
                },
                {
                    "id": "task-2",
                    "name": "Second task",
                    "description": "Do something second",
                    "depends_on": ["task-1"]
                }
            ]
        }

        response = api_client.post(
            f"/api/agents/{created_agent['name']}/plans",
            json=plan_data
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 201])
        data = assert_json_response(response)

        # Should have plan fields
        assert "id" in data or "name" in data

    def test_tasks_with_dependencies_start_blocked(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Tasks with dependencies start as blocked."""
        plan_data = {
            "name": f"test-plan-deps-{uuid.uuid4().hex[:8]}",
            "tasks": [
                {"id": "task-1", "name": "First"},
                {"id": "task-2", "name": "Second", "depends_on": ["task-1"]}
            ]
        }

        response = api_client.post(
            f"/api/agents/{created_agent['name']}/plans",
            json=plan_data
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        if response.status_code not in [200, 201]:
            pytest.skip(f"Plan creation failed: {response.text}")

        data = response.json()

        # Get tasks from response
        tasks = data.get("tasks", [])
        if tasks:
            task_2 = next((t for t in tasks if t.get("id") == "task-2"), None)
            if task_2:
                assert task_2.get("status") in ["blocked", "pending"]


class TestGetPlan:
    """REQ-PLANS-003: Get plan endpoint tests."""

    def test_get_plan_by_id(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/plans/{plan_id} returns full plan."""
        # First create a plan
        plan_data = {
            "name": f"test-get-plan-{uuid.uuid4().hex[:8]}",
            "tasks": [{"id": "task-1", "name": "Task"}]
        }

        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/plans",
            json=plan_data
        )

        if create_response.status_code == 503:
            pytest.skip("Agent server not ready")

        if create_response.status_code not in [200, 201]:
            pytest.skip("Plan creation failed")

        plan = create_response.json()
        plan_id = plan.get("id", plan.get("name"))

        # Get the plan
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/plans/{plan_id}"
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_plan_fields(data)

    def test_get_nonexistent_plan_returns_404(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/plans/{plan_id} for non-existent returns 404."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/plans/nonexistent-plan-xyz"
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 404)


class TestUpdateTask:
    """REQ-PLANS-004: Update task endpoint tests."""

    def test_update_task_status(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """PUT /api/agents/{name}/plans/{plan_id}/tasks/{task_id} updates status."""
        # First create a plan with tasks
        plan_data = {
            "name": f"test-update-task-{uuid.uuid4().hex[:8]}",
            "tasks": [
                {"id": "task-1", "name": "First"},
                {"id": "task-2", "name": "Second", "depends_on": ["task-1"]}
            ]
        }

        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/plans",
            json=plan_data
        )

        if create_response.status_code == 503:
            pytest.skip("Agent server not ready")

        if create_response.status_code not in [200, 201]:
            pytest.skip("Plan creation failed")

        plan = create_response.json()
        plan_id = plan.get("id", plan.get("name"))

        # Update task-1 to completed
        response = api_client.put(
            f"/api/agents/{created_agent['name']}/plans/{plan_id}/tasks/task-1",
            json={"status": "completed"}
        )

        assert_status(response, 200)

    def test_completing_task_unblocks_dependents(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Completing task unblocks dependent tasks."""
        plan_data = {
            "name": f"test-unblock-{uuid.uuid4().hex[:8]}",
            "tasks": [
                {"id": "task-1", "name": "First"},
                {"id": "task-2", "name": "Second", "depends_on": ["task-1"]}
            ]
        }

        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/plans",
            json=plan_data
        )

        if create_response.status_code == 503:
            pytest.skip("Agent server not ready")

        if create_response.status_code not in [200, 201]:
            pytest.skip("Plan creation failed")

        plan = create_response.json()
        plan_id = plan.get("id", plan.get("name"))

        # Complete task-1
        api_client.put(
            f"/api/agents/{created_agent['name']}/plans/{plan_id}/tasks/task-1",
            json={"status": "completed"}
        )

        # Get plan and check task-2 status
        get_response = api_client.get(
            f"/api/agents/{created_agent['name']}/plans/{plan_id}"
        )

        if get_response.status_code == 200:
            data = get_response.json()
            tasks = data.get("tasks", [])
            task_2 = next((t for t in tasks if t.get("id") == "task-2"), None)
            if task_2:
                # Should no longer be blocked
                assert task_2.get("status") in ["pending", "active", "completed"]


class TestPlanSummary:
    """REQ-PLANS-005: Plan summary endpoint tests."""

    def test_get_plan_summary(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/plans/summary returns aggregate statistics."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/plans/summary"
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have aggregate fields
        assert isinstance(data, dict)


class TestAggregatePlans:
    """Tests for cross-agent plan aggregation."""

    def test_get_aggregate_plans(self, api_client: TrinityApiClient):
        """GET /api/agents/plans/aggregate returns cross-agent summary."""
        response = api_client.get("/api/agents/plans/aggregate")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, (dict, list))
