"""
Per-Agent API Key Setting Tests (test_agent_api_key_setting.py)

Tests for Trinity per-agent API key control endpoints (Req 11.7).
Covers: Platform API key vs terminal authentication selection.

These tests verify the API key setting CRUD operations and validation.
"""

import pytest

from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


# Use trinity-system which is always available - no agent creation needed
SYSTEM_AGENT_NAME = "trinity-system"


class TestApiKeySettingAuthentication:
    """Tests for API key setting endpoint authentication requirements."""

    pytestmark = pytest.mark.smoke

    def test_get_api_key_setting_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """GET /api/agents/{name}/api-key-setting requires authentication."""
        response = unauthenticated_client.get(
            f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            auth=False
        )
        assert_status_in(response, [401, 403])

    def test_put_api_key_setting_requires_auth(self, unauthenticated_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting requires authentication."""
        response = unauthenticated_client.put(
            f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            json={"use_platform_api_key": True},
            auth=False
        )
        assert_status_in(response, [401, 403])


class TestApiKeySettingCRUD:
    """Tests for API key setting CRUD operations using trinity-system agent."""

    pytestmark = pytest.mark.smoke

    def test_get_api_key_setting_returns_structure(self, api_client: TrinityApiClient):
        """GET /api/agents/{name}/api-key-setting returns expected structure."""
        response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["use_platform_api_key", "agent_name"])
        assert data["agent_name"] == SYSTEM_AGENT_NAME
        assert isinstance(data["use_platform_api_key"], bool)

    def test_get_api_key_setting_default_is_true(self, api_client: TrinityApiClient):
        """Agents should default to using platform API key."""
        response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")

        assert_status(response, 200)
        data = response.json()
        # Default should be True (use platform API key)
        assert data["use_platform_api_key"] is True

    def test_get_api_key_setting_nonexistent_agent_returns_404(self, api_client: TrinityApiClient):
        """GET /api/agents/{name}/api-key-setting returns 404 for nonexistent agent."""
        response = api_client.get("/api/agents/nonexistent-agent-xyz/api-key-setting")
        assert_status(response, 404)

    def test_put_api_key_setting_update_and_restore(self, api_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting updates the setting."""
        # Get current setting first
        current = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")
        assert_status(current, 200)
        original_value = current.json()["use_platform_api_key"]

        try:
            # Update to opposite value
            response = api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": not original_value}
            )

            assert_status(response, 200)
            data = assert_json_response(response)
            assert data["use_platform_api_key"] is (not original_value)

            # Verify the change persisted
            get_response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")
            assert_status(get_response, 200)
            assert get_response.json()["use_platform_api_key"] is (not original_value)

        finally:
            # Always restore original value
            api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": original_value}
            )

    def test_put_api_key_setting_nonexistent_agent_returns_404(self, api_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting returns 404 for nonexistent agent."""
        response = api_client.put(
            "/api/agents/nonexistent-agent-xyz/api-key-setting",
            json={"use_platform_api_key": False}
        )
        assert_status(response, 404)

    def test_put_api_key_setting_missing_field_returns_error(self, api_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting with missing field returns error."""
        response = api_client.put(
            f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            json={}
        )

        # Should reject with 400, 422 (validation), or 500 (key error)
        assert_status_in(response, [400, 422, 500])


class TestApiKeySettingValidation:
    """Tests for API key setting input validation using trinity-system agent."""

    pytestmark = pytest.mark.smoke

    def test_put_api_key_setting_string_value_handled(self, api_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting handles string value."""
        # String instead of boolean
        response = api_client.put(
            f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            json={"use_platform_api_key": "true"}
        )

        # Should either accept (JSON parsing coerces) or reject (type validation)
        # The API may coerce strings to booleans or reject
        assert_status_in(response, [200, 400, 422])

    def test_put_api_key_setting_invalid_json(self, api_client: TrinityApiClient):
        """PUT /api/agents/{name}/api-key-setting rejects invalid JSON."""
        response = api_client._client.put(
            f"{api_client.config.base_url}/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            headers={
                **api_client._get_headers(),
                "Content-Type": "application/json"
            },
            content="not valid json"
        )

        assert_status(response, 422)


class TestApiKeySettingPermissions:
    """Tests for API key setting permission checks using trinity-system agent."""

    pytestmark = pytest.mark.smoke

    def test_admin_can_read_api_key_setting(self, api_client: TrinityApiClient):
        """Admin can read API key setting."""
        response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")
        assert_status(response, 200)

    def test_admin_can_update_api_key_setting(self, api_client: TrinityApiClient):
        """Admin can update API key setting."""
        # Get current value
        current = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting").json()
        original_value = current["use_platform_api_key"]

        try:
            # Update to opposite value
            response = api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": not original_value}
            )
            assert_status(response, 200)

        finally:
            # Restore original value
            api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": original_value}
            )


class TestApiKeySettingAgentState:
    """Tests for API key setting with different agent states."""

    pytestmark = pytest.mark.smoke

    def test_api_key_setting_readable_for_running_agent(self, api_client: TrinityApiClient):
        """API key setting can be read for running agent (trinity-system)."""
        # First verify trinity-system is running
        status_response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}")
        if status_response.status_code != 200:
            pytest.skip("trinity-system agent not available")

        agent_data = status_response.json()
        if agent_data.get("status") != "running":
            pytest.skip("trinity-system agent not running")

        response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")
        assert_status(response, 200)
        data = response.json()
        assert "use_platform_api_key" in data

    def test_api_key_setting_update_response_structure(self, api_client: TrinityApiClient):
        """Changing API key setting returns proper response structure."""
        # Get current value
        current = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting").json()
        original_value = current["use_platform_api_key"]

        try:
            # Update to opposite value
            response = api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": not original_value}
            )

            assert_status(response, 200)
            data = response.json()

            # Response should have the updated value
            assert "use_platform_api_key" in data
            # Response may include additional info like restart_required
            # Just verify it's a valid response

        finally:
            # Restore original value
            api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": original_value}
            )


class TestApiKeySettingIntegration:
    """Integration tests for API key setting.

    Note: Tests requiring agent restart are skipped to avoid disrupting trinity-system.
    Full integration tests should use created_agent fixture.
    """

    pytestmark = pytest.mark.smoke

    def test_api_key_setting_get_put_consistency(self, api_client: TrinityApiClient):
        """GET and PUT return consistent data structure."""
        # GET
        get_response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")
        assert_status(get_response, 200)
        get_data = get_response.json()

        # PUT with same value (no actual change)
        put_response = api_client.put(
            f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
            json={"use_platform_api_key": get_data["use_platform_api_key"]}
        )
        assert_status(put_response, 200)
        put_data = put_response.json()

        # Both should have same core fields
        assert "use_platform_api_key" in get_data
        assert "use_platform_api_key" in put_data
        assert get_data["use_platform_api_key"] == put_data["use_platform_api_key"]


class TestApiKeySettingResponseFormat:
    """Tests for API key setting response format consistency using trinity-system agent."""

    pytestmark = pytest.mark.smoke

    def test_get_response_has_agent_name(self, api_client: TrinityApiClient):
        """GET response includes agent_name field."""
        response = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting")

        assert_status(response, 200)
        data = response.json()
        assert "agent_name" in data
        assert data["agent_name"] == SYSTEM_AGENT_NAME

    def test_put_response_has_updated_value(self, api_client: TrinityApiClient):
        """PUT response includes the updated value."""
        # Get current value
        current = api_client.get(f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting").json()
        original_value = current["use_platform_api_key"]

        try:
            # Update
            response = api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": not original_value}
            )

            assert_status(response, 200)
            data = response.json()
            assert "use_platform_api_key" in data
            assert data["use_platform_api_key"] is (not original_value)

        finally:
            # Restore
            api_client.put(
                f"/api/agents/{SYSTEM_AGENT_NAME}/api-key-setting",
                json={"use_platform_api_key": original_value}
            )
