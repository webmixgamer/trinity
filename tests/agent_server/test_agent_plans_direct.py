"""
Agent Server Plans Direct Tests (test_agent_plans_direct.py)

Tests for direct plan endpoints on agent server.
Covers REQ-AS-PLAN-001 through REQ-AS-PLAN-006.
"""

import pytest
import uuid
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
)


class TestCreatePlan:
    """REQ-AS-PLAN-001: Create plan direct tests."""

    def test_create_plan(self, agent_proxy_client):
        """POST /api/plans creates plan with tasks."""
        api_client, agent_name = agent_proxy_client

        plan_data = {
            "name": f"test-direct-{uuid.uuid4().hex[:8]}",
            "tasks": [{"id": "task-1", "name": "Test task"}]
        }

        response = api_client.post(
            f"/api/agents/{agent_name}/plans",
            json=plan_data
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 201])


class TestListPlans:
    """REQ-AS-PLAN-002: List plans direct tests."""

    def test_list_plans(self, agent_proxy_client):
        """GET /api/plans returns plans."""
        api_client, agent_name = agent_proxy_client

        response = api_client.get(f"/api/agents/{agent_name}/plans")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, (list, dict))


class TestGetPlan:
    """REQ-AS-PLAN-003: Get plan direct tests."""

    def test_get_nonexistent_plan(self, agent_proxy_client):
        """GET /api/plans/{id} for non-existent returns 404."""
        api_client, agent_name = agent_proxy_client

        response = api_client.get(
            f"/api/agents/{agent_name}/plans/nonexistent-plan"
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 404)


class TestUpdateTask:
    """REQ-AS-PLAN-004: Update task direct tests."""

    def test_update_task_status(self, agent_proxy_client):
        """PUT /api/plans/{id}/tasks/{task_id} updates status."""
        api_client, agent_name = agent_proxy_client

        # Create a plan first
        plan_data = {
            "name": f"test-update-{uuid.uuid4().hex[:8]}",
            "tasks": [{"id": "task-1", "name": "Test"}]
        }

        create_response = api_client.post(
            f"/api/agents/{agent_name}/plans",
            json=plan_data
        )

        if create_response.status_code == 503:
            pytest.skip("Agent server not ready")

        if create_response.status_code not in [200, 201]:
            pytest.skip("Plan creation failed")

        plan = create_response.json()
        plan_id = plan.get("id", plan.get("name"))

        # Update task
        response = api_client.put(
            f"/api/agents/{agent_name}/plans/{plan_id}/tasks/task-1",
            json={"status": "completed"}
        )

        assert_status(response, 200)


class TestPlansSummary:
    """REQ-AS-PLAN-005: Plans summary direct tests."""

    def test_get_summary(self, agent_proxy_client):
        """GET /api/plans/summary returns stats."""
        api_client, agent_name = agent_proxy_client

        response = api_client.get(f"/api/agents/{agent_name}/plans/summary")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)


class TestDeletePlan:
    """REQ-AS-PLAN-006: Delete plan direct tests."""

    def test_delete_plan(self, agent_proxy_client):
        """DELETE /api/plans/{id} removes plan."""
        api_client, agent_name = agent_proxy_client

        # Create first
        plan_data = {
            "name": f"test-delete-{uuid.uuid4().hex[:8]}",
            "tasks": [{"id": "task-1", "name": "Test"}]
        }

        create_response = api_client.post(
            f"/api/agents/{agent_name}/plans",
            json=plan_data
        )

        if create_response.status_code == 503:
            pytest.skip("Agent server not ready")

        if create_response.status_code not in [200, 201]:
            pytest.skip("Plan creation failed")

        plan = create_response.json()
        plan_id = plan.get("id", plan.get("name"))

        # Delete
        response = api_client.delete(
            f"/api/agents/{agent_name}/plans/{plan_id}"
        )

        assert_status_in(response, [200, 204])
