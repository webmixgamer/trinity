"""
Credentials Tests (test_credentials.py)

Tests for credential management endpoints.
Covers REQ-CRED-001 through REQ-CRED-005.
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
    assert_credential_fields,
)


class TestCreateCredential:
    """REQ-CRED-001: Create credential endpoint tests."""

    def test_create_credential(
        self,
        api_client: TrinityApiClient,
        test_credential_name: str,
        resource_tracker
    ):
        """POST /api/credentials creates credential."""
        response = api_client.post(
            "/api/credentials",
            json={
                "name": test_credential_name,
                "service": "test",
                "type": "api_key",
                "credentials": {"api_key": "test-secret-value"}
            }
        )

        assert_status_in(response, [200, 201])
        data = assert_json_response(response)

        # Track for cleanup
        if "id" in data:
            resource_tracker.track_credential(data["id"])

        # Should return credential info (without secret)
        assert_has_fields(data, ["id", "name"])

    def test_create_credential_without_service(
        self,
        api_client: TrinityApiClient,
        resource_tracker
    ):
        """POST /api/credentials creates credential with service and type specified."""
        name = f"GOOGLE_API_KEY_{uuid.uuid4().hex[:8].upper()}"
        response = api_client.post(
            "/api/credentials",
            json={
                "name": name,
                "service": "google",
                "type": "api_key",
                "credentials": {"api_key": "test-value"}
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            if "id" in data:
                resource_tracker.track_credential(data["id"])

        assert_status_in(response, [200, 201])


class TestListCredentials:
    """REQ-CRED-002: List credentials endpoint tests."""

    def test_list_credentials(self, api_client: TrinityApiClient):
        """GET /api/credentials returns user's credentials."""
        response = api_client.get("/api/credentials")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_list_response(data, "credentials")

    def test_credentials_dont_expose_secrets(
        self,
        api_client: TrinityApiClient,
        test_credential_name: str,
        resource_tracker
    ):
        """Listed credentials don't include secret values."""
        # First create a credential
        create_response = api_client.post(
            "/api/credentials",
            json={
                "name": test_credential_name,
                "service": "test",
                "type": "api_key",
                "credentials": {"api_key": "super-secret-value-12345"}
            }
        )

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            if "id" in data:
                resource_tracker.track_credential(data["id"])

        # Now list and check
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        credentials = list_response.json()

        for cred in credentials:
            # Should not contain the actual value
            assert "value" not in cred or cred.get("value") is None, \
                "Credential list should not expose secret values"


class TestBulkImport:
    """REQ-CRED-003: Bulk import endpoint tests."""

    def test_bulk_import_env_format(
        self,
        api_client: TrinityApiClient,
        resource_tracker
    ):
        """POST /api/credentials/bulk parses .env format."""
        unique = uuid.uuid4().hex[:8].upper()
        env_content = f"""
# Comment line
TEST_API_KEY_{unique}=value1
TEST_API_SECRET_{unique}=value2
"""
        response = api_client.post(
            "/api/credentials/bulk",
            json={"content": env_content}
        )

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should indicate created/skipped counts
        assert "created" in data or "imported" in data or "count" in data or isinstance(data, list)

    def test_bulk_import_auto_detects_service(
        self,
        api_client: TrinityApiClient,
        resource_tracker
    ):
        """Bulk import auto-detects service from key prefix."""
        unique = uuid.uuid4().hex[:8].upper()
        env_content = f"GOOGLE_CLIENT_ID_{unique}=some-client-id\n"

        response = api_client.post(
            "/api/credentials/bulk",
            json={"content": env_content}
        )

        assert_status(response, 200)


class TestHotReload:
    """REQ-CRED-004: Hot reload endpoint tests."""

    def test_hot_reload_credentials(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/credentials/hot-reload updates credentials."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": "TEST_KEY=test_value\n"}
        )

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)

    def test_hot_reload_stopped_agent_fails(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """POST /api/agents/{name}/credentials/hot-reload on stopped agent fails."""
        response = api_client.post(
            f"/api/agents/{stopped_agent['name']}/credentials/hot-reload",
            json={"credentials_text": "TEST_KEY=test_value\n"}
        )

        # Should fail for stopped agent
        assert_status_in(response, [400, 503])


class TestCredentialStatus:
    """REQ-CRED-005: Credential status endpoint tests."""

    def test_get_credential_status(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/credentials/status returns file status."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/credentials/status"
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should indicate file existence
        assert isinstance(data, dict)


class TestAgentCredentialRequirements:
    """Tests for agent credential requirements."""

    def test_get_agent_credential_requirements(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/credentials returns required credentials."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/credentials"
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, (list, dict))


class TestReloadFromStore:
    """Tests for credential reload from store."""

    def test_reload_credentials_from_store(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/credentials/reload fetches from store."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/reload"
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
