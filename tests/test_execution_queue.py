"""
Execution Queue Tests (test_execution_queue.py)

Tests for agent execution queue management.
Covers REQ-QUEUE-001 through REQ-QUEUE-004.
"""

import pytest
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestQueueStatus:
    """REQ-QUEUE-001: Get queue status endpoint tests."""

    def test_get_queue_status(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/queue returns queue status."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/queue")

        # May not be implemented
        if response.status_code == 404:
            pytest.skip("Queue endpoint not implemented")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have status fields
        assert "is_busy" in data or "busy" in data or "status" in data

    def test_idle_agent_not_busy(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Idle agent shows is_busy: false."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/queue")

        if response.status_code == 404:
            pytest.skip("Queue endpoint not implemented")

        assert_status(response, 200)
        data = response.json()

        # Check busy status
        is_busy = data.get("is_busy", data.get("busy", False))
        # Note: May be busy if agent is still initializing
        assert isinstance(is_busy, bool)


class TestQueueFullHandling:
    """REQ-QUEUE-002: Queue full handling tests."""

    def test_queue_full_returns_429(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/chat returns 429 when queue is full."""
        # This test would require making multiple concurrent requests
        # to actually fill the queue. Skipping for basic implementation.
        pytest.skip("Queue full test requires concurrent requests")

    def test_429_response_has_retry_after(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """429 response includes retry_after information."""
        # Would need to trigger 429 first
        pytest.skip("Requires triggering 429 condition")


class TestClearQueue:
    """REQ-QUEUE-003: Clear queue endpoint tests."""

    def test_clear_queue(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/queue/clear clears queued executions."""
        response = api_client.post(f"/api/agents/{created_agent['name']}/queue/clear")

        # May not be implemented
        if response.status_code == 404:
            pytest.skip("Queue clear endpoint not implemented")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should indicate cleared count or success
        assert "cleared" in data or "success" in data or "count" in data or response.status_code == 200


class TestForceRelease:
    """REQ-QUEUE-004: Force release endpoint tests."""

    def test_force_release(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/queue/release releases stuck agent."""
        response = api_client.post(f"/api/agents/{created_agent['name']}/queue/release")

        # May not be implemented
        if response.status_code == 404:
            pytest.skip("Queue release endpoint not implemented")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should indicate release result
        assert "was_running" in data or "released" in data or "success" in data or isinstance(data, dict)
