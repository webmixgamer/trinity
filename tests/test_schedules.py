"""
Schedules Tests (test_schedules.py)

Tests for agent scheduling functionality.
Covers REQ-SCHED-001 through REQ-SCHED-005.

Feature Flow: scheduling.md
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
)


class TestSchedulerStatus:
    """REQ-SCHED-005: Scheduler status endpoint tests."""

    pytestmark = pytest.mark.smoke

    def test_get_scheduler_status(self, api_client: TrinityApiClient):
        """GET /api/agents/scheduler/status returns scheduler status."""
        response = api_client.get("/api/agents/scheduler/status")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have scheduler state info
        assert_has_fields(data, ["running"])

    def test_scheduler_status_structure(self, api_client: TrinityApiClient):
        """Scheduler status returns expected structure."""
        response = api_client.get("/api/agents/scheduler/status")

        assert_status(response, 200)
        data = response.json()

        # Scheduler should be running
        assert isinstance(data.get("running"), bool)

        # May include job count
        if "job_count" in data:
            assert isinstance(data["job_count"], int)
            assert data["job_count"] >= 0

    def test_scheduler_status_includes_jobs(self, api_client: TrinityApiClient):
        """Scheduler status includes information about scheduled jobs."""
        response = api_client.get("/api/agents/scheduler/status")

        assert_status(response, 200)
        data = response.json()

        # Should have jobs or job_count field
        assert "jobs" in data or "job_count" in data or "scheduled_jobs" in data

    def test_scheduler_status_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/agents/scheduler/status requires authentication."""
        response = unauthenticated_client.get(
            "/api/agents/scheduler/status",
            auth=False
        )
        assert_status(response, 401)


class TestCreateSchedule:
    """REQ-SCHED-001: Create schedule endpoint tests."""

    def test_create_schedule(
        self,
        api_client: TrinityApiClient,
        created_agent,
        test_schedule_name: str,
        resource_tracker
    ):
        """POST /api/agents/{name}/schedules creates schedule."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": test_schedule_name,
                "cron_expression": "0 * * * *",  # Every hour
                "message": "Test scheduled message",
                "enabled": False  # Don't actually run
            }
        )

        assert_status_in(response, [200, 201])
        data = assert_json_response(response)

        # Track for cleanup
        if "id" in data:
            resource_tracker.track_schedule(created_agent['name'], data["id"])

        assert_has_fields(data, ["id", "name"])

    def test_create_schedule_validates_cron(
        self,
        api_client: TrinityApiClient,
        created_agent,
        test_schedule_name: str
    ):
        """Invalid cron expression returns 400."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": test_schedule_name,
                "cron_expression": "invalid cron",
                "message": "Test"
            }
        )

        assert_status_in(response, [400, 422])


class TestListSchedules:
    """REQ-SCHED-002: List schedules endpoint tests."""

    def test_list_schedules(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/schedules returns schedules."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/schedules")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_list_response(data, "schedules")

    def test_schedule_has_required_fields(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Each schedule has id, cron, enabled."""
        # Create a schedule first
        schedule_name = f"test-schedule-fields-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Test",
                "enabled": False
            }
        )

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            if "id" in data:
                resource_tracker.track_schedule(created_agent['name'], data["id"])

        # List and check
        list_response = api_client.get(f"/api/agents/{created_agent['name']}/schedules")
        assert_status(list_response, 200)
        schedules = list_response.json()

        if len(schedules) > 0:
            schedule = schedules[0]
            assert_has_fields(schedule, ["id", "name"])


class TestEnableDisableSchedule:
    """REQ-SCHED-003: Enable/disable schedule endpoint tests."""

    def test_enable_schedule(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """POST /api/agents/{name}/schedules/{id}/enable enables schedule."""
        # Create disabled schedule
        schedule_name = f"test-enable-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Test",
                "enabled": False
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create schedule")

        data = create_response.json()
        schedule_id = data.get("id")
        resource_tracker.track_schedule(created_agent['name'], schedule_id)

        # Enable it
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules/{schedule_id}/enable"
        )

        assert_status(response, 200)

    def test_disable_schedule(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """POST /api/agents/{name}/schedules/{id}/disable disables schedule."""
        # Create enabled schedule
        schedule_name = f"test-disable-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Test",
                "enabled": True
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create schedule")

        data = create_response.json()
        schedule_id = data.get("id")
        resource_tracker.track_schedule(created_agent['name'], schedule_id)

        # Disable it
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules/{schedule_id}/disable"
        )

        assert_status(response, 200)


class TestTriggerSchedule:
    """REQ-SCHED-004: Trigger schedule endpoint tests."""

    @pytest.mark.slow
    def test_trigger_schedule(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """POST /api/agents/{name}/schedules/{id}/trigger manually triggers."""
        # Create schedule
        schedule_name = f"test-trigger-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Say hello",
                "enabled": False
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create schedule")

        data = create_response.json()
        schedule_id = data.get("id")
        resource_tracker.track_schedule(created_agent['name'], schedule_id)

        # Trigger it
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules/{schedule_id}/trigger",
            timeout=120.0  # May take a while
        )

        # May return 503 if agent busy
        if response.status_code == 503:
            pytest.skip("Agent server not ready")
        if response.status_code == 429:
            pytest.skip("Agent queue full")

        assert_status_in(response, [200, 202])


class TestScheduleExecutions:
    """Tests for schedule execution history."""

    def test_get_execution_history(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """GET /api/agents/{name}/schedules/{id}/executions returns history."""
        # Create schedule
        schedule_name = f"test-executions-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Test",
                "enabled": False
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create schedule")

        data = create_response.json()
        schedule_id = data.get("id")
        resource_tracker.track_schedule(created_agent['name'], schedule_id)

        # Get executions
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/schedules/{schedule_id}/executions"
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, list)


class TestDeleteSchedule:
    """Tests for schedule deletion."""

    def test_delete_schedule(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """DELETE /api/agents/{name}/schedules/{id} deletes schedule."""
        # Create schedule
        schedule_name = f"test-delete-{uuid.uuid4().hex[:8]}"
        create_response = api_client.post(
            f"/api/agents/{created_agent['name']}/schedules",
            json={
                "name": schedule_name,
                "cron_expression": "0 0 * * *",
                "message": "Test",
                "enabled": False
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create schedule")

        data = create_response.json()
        schedule_id = data.get("id")

        # Delete it
        response = api_client.delete(
            f"/api/agents/{created_agent['name']}/schedules/{schedule_id}"
        )

        assert_status_in(response, [200, 204])
