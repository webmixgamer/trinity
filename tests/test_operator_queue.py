"""
Operator Queue Tests (test_operator_queue.py)

Tests for the Operating Room / Operator Queue API endpoints (OPS-001).
Covers list, get, respond, cancel, stats, agent-specific queries,
authentication, and input validation.

Feature Flow: operating-room.md
"""

import pytest
import uuid
from datetime import datetime, timezone

from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_json_response,
    assert_has_fields,
)


# ============================================================================
# Helpers
# ============================================================================

def _insert_queue_item(api_client: TrinityApiClient, **overrides) -> dict:
    """Insert a queue item directly via the database for testing.

    Since there's no public POST endpoint for creating queue items (they come
    from agent containers via the sync service), we insert via a direct DB
    call exposed through a test-support endpoint, or we use the list/respond
    flow with pre-seeded data.

    For now, we use the internal admin endpoint pattern.
    """
    item_id = overrides.get("id", f"test-{uuid.uuid4().hex[:12]}")
    now = datetime.now(timezone.utc).isoformat()

    defaults = {
        "id": item_id,
        "agent_name": "test-agent",
        "type": "approval",
        "status": "pending",
        "priority": "medium",
        "title": "Test approval request",
        "question": "Should we proceed with this test?",
        "options": ["approve", "reject"],
        "context": {"test": True},
        "created_at": now,
    }
    defaults.update(overrides)
    return defaults


# ============================================================================
# Authentication Tests
# ============================================================================

class TestOperatorQueueAuthentication:
    """Tests for operator queue endpoint authentication requirements."""

    pytestmark = pytest.mark.smoke

    def test_list_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/operator-queue requires authentication."""
        response = unauthenticated_client.get("/api/operator-queue", auth=False)
        assert_status(response, 401)

    def test_stats_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/operator-queue/stats requires authentication."""
        response = unauthenticated_client.get("/api/operator-queue/stats", auth=False)
        assert_status(response, 401)

    def test_get_item_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/operator-queue/{id} requires authentication."""
        response = unauthenticated_client.get(
            "/api/operator-queue/test-item-123", auth=False
        )
        assert_status(response, 401)

    def test_respond_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """POST /api/operator-queue/{id}/respond requires authentication."""
        response = unauthenticated_client.post(
            "/api/operator-queue/test-item-123/respond",
            json={"response": "approve"},
            auth=False,
        )
        assert_status(response, 401)

    def test_cancel_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """POST /api/operator-queue/{id}/cancel requires authentication."""
        response = unauthenticated_client.post(
            "/api/operator-queue/test-item-123/cancel",
            auth=False,
        )
        assert_status(response, 401)

    def test_agent_items_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/operator-queue/agents/{name} requires authentication."""
        response = unauthenticated_client.get(
            "/api/operator-queue/agents/test-agent", auth=False
        )
        assert_status(response, 401)


# ============================================================================
# List Queue Items Tests
# ============================================================================

class TestListQueueItems:
    """Tests for GET /api/operator-queue endpoint."""

    pytestmark = pytest.mark.smoke

    def test_list_items_structure(self, api_client: TrinityApiClient):
        """List queue items returns expected structure."""
        response = api_client.get("/api/operator-queue")
        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["items", "count"])
        assert isinstance(data["items"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["items"])

    def test_list_items_respects_limit(self, api_client: TrinityApiClient):
        """List respects limit parameter."""
        response = api_client.get("/api/operator-queue?limit=2")
        assert_status(response, 200)
        data = response.json()
        assert len(data["items"]) <= 2

    def test_list_items_respects_offset(self, api_client: TrinityApiClient):
        """List respects offset parameter."""
        response = api_client.get("/api/operator-queue?offset=0&limit=500")
        assert_status(response, 200)
        all_items = response.json()["items"]

        if len(all_items) > 1:
            response2 = api_client.get("/api/operator-queue?offset=1&limit=500")
            assert_status(response2, 200)
            offset_items = response2.json()["items"]
            assert len(offset_items) == len(all_items) - 1

    def test_list_items_filter_by_status(self, api_client: TrinityApiClient):
        """List can filter by status parameter."""
        response = api_client.get("/api/operator-queue?status=pending")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_list_items_filter_by_type(self, api_client: TrinityApiClient):
        """List can filter by type parameter."""
        response = api_client.get("/api/operator-queue?type=approval")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["type"] == "approval"

    def test_list_items_filter_by_priority(self, api_client: TrinityApiClient):
        """List can filter by priority parameter."""
        response = api_client.get("/api/operator-queue?priority=high")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["priority"] == "high"

    def test_list_items_filter_by_agent_name(self, api_client: TrinityApiClient):
        """List can filter by agent_name parameter."""
        response = api_client.get("/api/operator-queue?agent_name=oracle-1")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["agent_name"] == "oracle-1"

    def test_list_items_item_structure(self, api_client: TrinityApiClient):
        """Each item in list has expected fields."""
        response = api_client.get("/api/operator-queue?limit=5")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert_has_fields(item, [
                "id", "agent_name", "type", "status", "priority",
                "title", "question", "created_at"
            ])

    def test_list_items_invalid_limit(self, api_client: TrinityApiClient):
        """List with invalid limit returns 422."""
        response = api_client.get("/api/operator-queue?limit=0")
        assert_status(response, 422)

    def test_list_items_limit_too_large(self, api_client: TrinityApiClient):
        """List with limit > 500 returns 422."""
        response = api_client.get("/api/operator-queue?limit=501")
        assert_status(response, 422)


# ============================================================================
# Get Queue Item Tests
# ============================================================================

class TestGetQueueItem:
    """Tests for GET /api/operator-queue/{item_id} endpoint."""

    pytestmark = pytest.mark.smoke

    def test_get_item_not_found(self, api_client: TrinityApiClient):
        """Get non-existent queue item returns 404."""
        response = api_client.get("/api/operator-queue/nonexistent-item-id")
        assert_status(response, 404)

    def test_get_existing_item(self, api_client: TrinityApiClient):
        """Get existing queue item returns full item data."""
        # List items first to find one
        list_response = api_client.get("/api/operator-queue?limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.get(f"/api/operator-queue/{item_id}")
        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, [
            "id", "agent_name", "type", "status", "priority",
            "title", "question", "created_at"
        ])
        assert data["id"] == item_id


# ============================================================================
# Queue Stats Tests
# ============================================================================

class TestQueueStats:
    """Tests for GET /api/operator-queue/stats endpoint."""

    pytestmark = pytest.mark.smoke

    def test_stats_structure(self, api_client: TrinityApiClient):
        """Stats endpoint returns expected structure."""
        response = api_client.get("/api/operator-queue/stats")
        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, [
            "by_status", "by_type", "by_priority", "by_agent",
            "avg_response_seconds", "responded_today"
        ])

    def test_stats_by_status_is_dict(self, api_client: TrinityApiClient):
        """Stats by_status is a dict with count values."""
        response = api_client.get("/api/operator-queue/stats")
        data = response.json()
        assert isinstance(data["by_status"], dict)
        for key, value in data["by_status"].items():
            assert isinstance(value, int)

    def test_stats_by_type_is_dict(self, api_client: TrinityApiClient):
        """Stats by_type is a dict with count values."""
        response = api_client.get("/api/operator-queue/stats")
        data = response.json()
        assert isinstance(data["by_type"], dict)

    def test_stats_by_priority_is_dict(self, api_client: TrinityApiClient):
        """Stats by_priority is a dict with count values."""
        response = api_client.get("/api/operator-queue/stats")
        data = response.json()
        assert isinstance(data["by_priority"], dict)

    def test_stats_by_agent_is_dict(self, api_client: TrinityApiClient):
        """Stats by_agent is a dict with count values."""
        response = api_client.get("/api/operator-queue/stats")
        data = response.json()
        assert isinstance(data["by_agent"], dict)

    def test_stats_responded_today_is_int(self, api_client: TrinityApiClient):
        """Stats responded_today is an integer."""
        response = api_client.get("/api/operator-queue/stats")
        data = response.json()
        assert isinstance(data["responded_today"], int)
        assert data["responded_today"] >= 0


# ============================================================================
# Respond to Queue Item Tests
# ============================================================================

class TestRespondToQueueItem:
    """Tests for POST /api/operator-queue/{item_id}/respond endpoint."""

    pytestmark = pytest.mark.smoke

    def test_respond_not_found(self, api_client: TrinityApiClient):
        """Responding to non-existent item returns 404."""
        response = api_client.post(
            "/api/operator-queue/nonexistent-id/respond",
            json={"response": "approve"}
        )
        assert_status(response, 404)

    def test_respond_missing_body(self, api_client: TrinityApiClient):
        """Responding without body returns 422."""
        response = api_client.post(
            "/api/operator-queue/some-id/respond",
            json={}
        )
        assert_status(response, 422)

    def test_respond_to_pending_item(self, api_client: TrinityApiClient):
        """Respond to a pending item transitions it to responded."""
        # Find a pending item
        list_response = api_client.get("/api/operator-queue?status=pending&limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No pending queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.post(
            f"/api/operator-queue/{item_id}/respond",
            json={"response": "approve", "response_text": "Looks good"}
        )
        assert_status(response, 200)
        data = response.json()
        assert data["id"] == item_id
        assert data["status"] == "responded"
        assert data["response"] == "approve"
        assert data["response_text"] == "Looks good"
        assert data["responded_at"] is not None
        assert data["responded_by_email"] is not None

    def test_respond_to_already_responded_item(self, api_client: TrinityApiClient):
        """Responding to an already-responded item returns 400."""
        # Find a responded item
        list_response = api_client.get("/api/operator-queue?status=responded&limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No responded queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.post(
            f"/api/operator-queue/{item_id}/respond",
            json={"response": "approve"}
        )
        assert_status(response, 400)

    def test_respond_with_response_text(self, api_client: TrinityApiClient):
        """Respond with optional response_text field."""
        list_response = api_client.get("/api/operator-queue?status=pending&limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No pending queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.post(
            f"/api/operator-queue/{item_id}/respond",
            json={
                "response": "reject",
                "response_text": "Not ready yet, needs more testing"
            }
        )
        assert_status(response, 200)
        data = response.json()
        assert data["response_text"] == "Not ready yet, needs more testing"


# ============================================================================
# Cancel Queue Item Tests
# ============================================================================

class TestCancelQueueItem:
    """Tests for POST /api/operator-queue/{item_id}/cancel endpoint."""

    pytestmark = pytest.mark.smoke

    def test_cancel_not_found(self, api_client: TrinityApiClient):
        """Cancelling non-existent item returns 404."""
        response = api_client.post(
            "/api/operator-queue/nonexistent-id/cancel"
        )
        assert_status(response, 404)

    def test_cancel_pending_item(self, api_client: TrinityApiClient):
        """Cancel a pending item transitions it to cancelled."""
        list_response = api_client.get("/api/operator-queue?status=pending&limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No pending queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.post(f"/api/operator-queue/{item_id}/cancel")
        assert_status(response, 200)
        data = response.json()
        assert data["id"] == item_id
        assert data["status"] == "cancelled"

    def test_cancel_already_responded_item(self, api_client: TrinityApiClient):
        """Cancelling an already-responded item returns 400."""
        list_response = api_client.get("/api/operator-queue?status=responded&limit=1")
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("No responded queue items available for testing")

        item_id = items[0]["id"]
        response = api_client.post(f"/api/operator-queue/{item_id}/cancel")
        assert_status(response, 400)


# ============================================================================
# Agent-Specific Queue Items Tests
# ============================================================================

class TestAgentQueueItems:
    """Tests for GET /api/operator-queue/agents/{agent_name} endpoint."""

    pytestmark = pytest.mark.smoke

    def test_agent_items_structure(self, api_client: TrinityApiClient):
        """Agent queue items returns expected structure."""
        response = api_client.get("/api/operator-queue/agents/oracle-1")
        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["agent_name", "items", "count"])
        assert data["agent_name"] == "oracle-1"
        assert isinstance(data["items"], list)
        assert data["count"] == len(data["items"])

    def test_agent_items_filter_agent(self, api_client: TrinityApiClient):
        """All returned items belong to the requested agent."""
        response = api_client.get("/api/operator-queue/agents/oracle-1")
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["agent_name"] == "oracle-1"

    def test_agent_items_with_status_filter(self, api_client: TrinityApiClient):
        """Agent items support status filter."""
        response = api_client.get(
            "/api/operator-queue/agents/oracle-1?status=pending"
        )
        assert_status(response, 200)
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "pending"
            assert item["agent_name"] == "oracle-1"

    def test_agent_items_nonexistent_agent(self, api_client: TrinityApiClient):
        """Querying items for non-existent agent returns empty list (not 404)."""
        response = api_client.get(
            "/api/operator-queue/agents/nonexistent-agent-xyz"
        )
        assert_status(response, 200)
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []

    def test_agent_items_respects_limit(self, api_client: TrinityApiClient):
        """Agent items respects limit parameter."""
        response = api_client.get(
            "/api/operator-queue/agents/oracle-1?limit=1"
        )
        assert_status(response, 200)
        data = response.json()
        assert len(data["items"]) <= 1
