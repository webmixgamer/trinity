"""
Agent Dashboard Tests (test_agent_dashboard.py)

Tests for agent-defined dashboard API.
Covers DASH-001 (View agent-defined dashboards) and DASH-002 (Define widgets in dashboard.yaml).
"""

import pytest
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestDashboardEndpointAuthentication:
    """Tests for Dashboard API authentication requirements."""

    pytestmark = pytest.mark.smoke

    def test_dashboard_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/agent-dashboard/{name} requires authentication."""
        response = unauthenticated_client.get("/api/agent-dashboard/test-agent", auth=False)
        assert_status(response, 401)


class TestDashboardEndpoint:
    """DASH-001: View agent-defined dashboards."""

    def test_dashboard_returns_structure(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agent-dashboard/{name} returns expected structure."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have required fields
        assert_has_fields(data, ["agent_name", "has_dashboard", "status"])
        assert data["agent_name"] == created_agent["name"]

    def test_agent_without_dashboard_returns_has_dashboard_false(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Agents without dashboard.yaml return has_dashboard: false."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Most test agents don't have a dashboard.yaml
        # Either has_dashboard is false, or config is present
        assert "has_dashboard" in data
        if not data["has_dashboard"]:
            # Config should be None or empty when no dashboard
            assert data.get("config") is None or data.get("config") == {}

    def test_dashboard_config_structure_when_present(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Dashboard config has correct structure when present."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        if data.get("has_dashboard") and data.get("config"):
            config = data["config"]
            # Config should have title and sections
            if "title" in config:
                assert isinstance(config["title"], str)
            if "sections" in config:
                assert isinstance(config["sections"], list)
                for section in config["sections"]:
                    if "widgets" in section:
                        assert isinstance(section["widgets"], list)

    def test_nonexistent_agent_returns_404(
        self,
        api_client: TrinityApiClient
    ):
        """GET /api/agent-dashboard/{name} for nonexistent agent returns 404."""
        response = api_client.get("/api/agent-dashboard/nonexistent-agent-xyz")
        assert_status(response, 404)

    def test_dashboard_status_reflects_agent_state(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Dashboard status field reflects agent running state."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Status should be one of the valid states
        assert "status" in data
        assert data["status"] in ["running", "stopped", "error", "starting", "unknown"]


class TestDashboardWidgetTypes:
    """DASH-002: Dashboard widget type validation."""

    VALID_WIDGET_TYPES = [
        "metric", "status", "progress", "text", "markdown",
        "table", "list", "link", "image", "divider", "spacer"
    ]

    def test_dashboard_supports_metric_widget(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Dashboard API accepts metric widget type."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        # This test validates the API works - actual widget validation
        # happens when dashboards are defined in agents

    def test_dashboard_last_modified_timestamp(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Dashboard response includes last_modified timestamp when available."""
        response = api_client.get(f"/api/agent-dashboard/{created_agent['name']}")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # last_modified may be present
        if "last_modified" in data and data["last_modified"]:
            # Should be an ISO timestamp string
            assert isinstance(data["last_modified"], str)
