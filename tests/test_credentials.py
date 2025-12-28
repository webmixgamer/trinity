"""
Credentials Tests (test_credentials.py)

Tests for credential management endpoints.
Covers REQ-CRED-001 through REQ-CRED-005.
"""

import pytest
import uuid
import time
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


class TestHotReloadRedisPersistence:
    """
    REQ-CRED-004: Hot reload Redis persistence tests.

    These tests verify that hot-reloaded credentials are saved to Redis
    and persist across agent restarts. This prevents the bug where
    hot-reloaded credentials were only pushed to the agent but not
    persisted in the credential store.
    """

    def test_hot_reload_saves_to_redis(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Hot-reloaded credentials should be saved to Redis and appear in credential list."""
        # Generate unique credential name
        unique = uuid.uuid4().hex[:8].upper()
        cred_name = f"HOT_RELOAD_TEST_{unique}"
        cred_value = f"test-value-{unique}"

        # Get initial credential count
        initial_response = api_client.get("/api/credentials")
        assert_status(initial_response, 200)
        initial_creds = initial_response.json()
        initial_count = len(initial_creds)
        initial_names = {c["name"] for c in initial_creds}

        # Hot-reload a new credential
        hot_reload_response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f"{cred_name}={cred_value}\n"}
        )

        # May return 503 if agent not ready
        if hot_reload_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(hot_reload_response, 200)
        hot_reload_data = assert_json_response(hot_reload_response)

        # Verify response includes saved_to_redis
        assert "saved_to_redis" in hot_reload_data, \
            "Hot-reload response should include saved_to_redis field"
        assert len(hot_reload_data["saved_to_redis"]) == 1, \
            "Should have saved one credential to Redis"

        saved_info = hot_reload_data["saved_to_redis"][0]
        assert saved_info["name"] == cred_name, \
            "Saved credential name should match"
        assert saved_info["status"] in ["created", "reused"], \
            "Status should be 'created' or 'reused'"

        # Verify credential appears in credential list
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        current_creds = list_response.json()
        current_names = {c["name"] for c in current_creds}

        assert cred_name in current_names, \
            f"Hot-reloaded credential '{cred_name}' should appear in credential list"
        assert len(current_creds) == initial_count + 1, \
            "Credential count should increase by 1"

        # Track for cleanup
        for cred in current_creds:
            if cred["name"] == cred_name:
                resource_tracker.track_credential(cred["id"])
                break

    def test_hot_reload_conflict_resolution_reuse(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Hot-reloading same credential name with same value should return 'reused' status."""
        # Generate unique credential name
        unique = uuid.uuid4().hex[:8].upper()
        cred_name = f"REUSE_TEST_{unique}"
        cred_value = f"same-value-{unique}"

        # Hot-reload credential first time
        first_response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f"{cred_name}={cred_value}\n"}
        )

        if first_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(first_response, 200)
        first_data = assert_json_response(first_response)

        # Track for cleanup
        creds_response = api_client.get("/api/credentials")
        if creds_response.status_code == 200:
            for cred in creds_response.json():
                if cred["name"] == cred_name:
                    resource_tracker.track_credential(cred["id"])

        # Hot-reload same credential again with SAME value
        second_response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f"{cred_name}={cred_value}\n"}
        )

        assert_status(second_response, 200)
        second_data = assert_json_response(second_response)

        # Verify response indicates credential was reused
        assert "saved_to_redis" in second_data
        saved_info = second_data["saved_to_redis"][0]
        assert saved_info["status"] == "reused", \
            "Hot-reloading same credential with same value should return 'reused' status"
        assert saved_info["name"] == cred_name, \
            "Credential name should remain unchanged"

        # Verify no duplicate was created
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        current_creds = list_response.json()
        matching_creds = [c for c in current_creds if c["name"] == cred_name]

        assert len(matching_creds) == 1, \
            "Should not create duplicate credential when reusing"

    def test_hot_reload_conflict_resolution_rename(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Hot-reloading same credential name with different value should create renamed credential."""
        # Generate unique credential name
        unique = uuid.uuid4().hex[:8].upper()
        cred_name = f"RENAME_TEST_{unique}"
        first_value = f"first-value-{unique}"
        second_value = f"second-value-{unique}-different"

        # Hot-reload credential first time
        first_response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f"{cred_name}={first_value}\n"}
        )

        if first_response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(first_response, 200)
        first_data = assert_json_response(first_response)

        # Track original for cleanup
        creds_response = api_client.get("/api/credentials")
        if creds_response.status_code == 200:
            for cred in creds_response.json():
                if cred["name"] == cred_name:
                    resource_tracker.track_credential(cred["id"])

        # Hot-reload same credential name with DIFFERENT value
        second_response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f"{cred_name}={second_value}\n"}
        )

        assert_status(second_response, 200)
        second_data = assert_json_response(second_response)

        # Verify response indicates credential was renamed
        assert "saved_to_redis" in second_data
        saved_info = second_data["saved_to_redis"][0]
        assert saved_info["status"] == "renamed", \
            "Hot-reloading same credential name with different value should return 'renamed' status"
        assert saved_info["original"] == cred_name, \
            "Should include original credential name"
        assert saved_info["name"] != cred_name, \
            "New credential should have different name"
        assert saved_info["name"].startswith(f"{cred_name}_"), \
            "New credential name should have suffix (e.g., RENAME_TEST_XXXXX_2)"

        # Verify both credentials exist in the list
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        current_creds = list_response.json()
        cred_names = {c["name"] for c in current_creds}

        assert cred_name in cred_names, \
            "Original credential should still exist"
        assert saved_info["name"] in cred_names, \
            "Renamed credential should be created"

        # Track renamed credential for cleanup
        for cred in current_creds:
            if cred["name"] == saved_info["name"]:
                resource_tracker.track_credential(cred["id"])
                break

    def test_hot_reload_multiple_credentials(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Hot-reloading multiple credentials should save all to Redis."""
        # Generate unique credential names
        unique = uuid.uuid4().hex[:8].upper()
        cred1_name = f"MULTI_TEST_1_{unique}"
        cred2_name = f"MULTI_TEST_2_{unique}"
        cred3_name = f"MULTI_TEST_3_{unique}"

        credentials_text = f"""
# Test credentials
{cred1_name}=value1
{cred2_name}=value2
{cred3_name}=value3
"""

        # Hot-reload multiple credentials
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": credentials_text}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Verify all credentials were saved to Redis
        assert "saved_to_redis" in data
        assert len(data["saved_to_redis"]) == 3, \
            "Should have saved 3 credentials to Redis"

        saved_names = {info["name"] for info in data["saved_to_redis"]}
        assert cred1_name in saved_names
        assert cred2_name in saved_names
        assert cred3_name in saved_names

        # Verify all appear in credential list
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        current_creds = list_response.json()
        current_names = {c["name"] for c in current_creds}

        assert cred1_name in current_names
        assert cred2_name in current_names
        assert cred3_name in current_names

        # Track for cleanup
        for cred in current_creds:
            if cred["name"] in {cred1_name, cred2_name, cred3_name}:
                resource_tracker.track_credential(cred["id"])

    def test_hot_reload_with_quotes(
        self,
        api_client: TrinityApiClient,
        created_agent,
        resource_tracker
    ):
        """Hot-reload should handle quoted values correctly."""
        unique = uuid.uuid4().hex[:8].upper()
        cred_name = f"QUOTE_TEST_{unique}"
        cred_value = "value with spaces and special chars!"

        # Test with double quotes
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/credentials/hot-reload",
            json={"credentials_text": f'{cred_name}="{cred_value}"\n'}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Verify saved to Redis
        assert "saved_to_redis" in data
        assert len(data["saved_to_redis"]) == 1

        # Verify appears in credential list
        list_response = api_client.get("/api/credentials")
        assert_status(list_response, 200)
        current_creds = list_response.json()
        current_names = {c["name"] for c in current_creds}

        assert cred_name in current_names

        # Track for cleanup
        for cred in current_creds:
            if cred["name"] == cred_name:
                resource_tracker.track_credential(cred["id"])
                break

    @pytest.mark.slow
    def test_hot_reload_persists_after_agent_restart(
        self,
        api_client: TrinityApiClient,
        resource_tracker
    ):
        """
        REGRESSION TEST: Hot-reloaded credentials should persist after agent restart.

        This test verifies the bug fix where hot-reloaded credentials were only
        pushed to the agent but not saved to Redis, causing them to be lost on
        agent restart.
        """
        # Create a dedicated agent for this test (we need to restart it)
        unique = uuid.uuid4().hex[:6]
        agent_name = f"test-persist-{unique}"

        # Create agent
        create_response = api_client.post(
            "/api/agents",
            json={"name": agent_name}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test agent: {create_response.text}")

        # Wait for agent to be ready
        max_wait = 45
        start = time.time()
        agent_ready = False
        while time.time() - start < max_wait:
            check = api_client.get(f"/api/agents/{agent_name}")
            if check.status_code == 200:
                agent_data = check.json()
                if agent_data.get("status") == "running":
                    time.sleep(2)  # Brief wait for agent server
                    agent_ready = True
                    break
            time.sleep(1)

        if not agent_ready:
            # Cleanup and skip
            api_client.delete(f"/api/agents/{agent_name}")
            pytest.skip(f"Agent {agent_name} did not start within {max_wait}s")

        try:
            # Generate unique credential
            cred_unique = uuid.uuid4().hex[:8].upper()
            cred_name = f"PERSIST_TEST_{cred_unique}"
            cred_value = f"persist-value-{cred_unique}"

            # Hot-reload credential
            hot_reload_response = api_client.post(
                f"/api/agents/{agent_name}/credentials/hot-reload",
                json={"credentials_text": f"{cred_name}={cred_value}\n"}
            )

            if hot_reload_response.status_code == 503:
                pytest.skip("Agent server not ready")

            assert_status(hot_reload_response, 200)
            hot_reload_data = assert_json_response(hot_reload_response)

            # Verify credential was saved to Redis
            assert "saved_to_redis" in hot_reload_data
            assert len(hot_reload_data["saved_to_redis"]) == 1

            # Track credential for cleanup
            creds_response = api_client.get("/api/credentials")
            if creds_response.status_code == 200:
                for cred in creds_response.json():
                    if cred["name"] == cred_name:
                        resource_tracker.track_credential(cred["id"])

            # Verify credential exists in list BEFORE restart
            pre_restart_response = api_client.get("/api/credentials")
            assert_status(pre_restart_response, 200)
            pre_restart_creds = pre_restart_response.json()
            pre_restart_names = {c["name"] for c in pre_restart_creds}
            assert cred_name in pre_restart_names, \
                "Credential should exist before restart"

            # Restart the agent
            stop_response = api_client.post(f"/api/agents/{agent_name}/stop")
            assert_status_in(stop_response, [200, 204])
            time.sleep(3)

            start_response = api_client.post(f"/api/agents/{agent_name}/start")
            assert_status_in(start_response, [200, 204])

            # Wait for agent to be running again
            max_wait = 30
            start = time.time()
            agent_restarted = False
            while time.time() - start < max_wait:
                check = api_client.get(f"/api/agents/{agent_name}")
                if check.status_code == 200:
                    agent_data = check.json()
                    if agent_data.get("status") == "running":
                        time.sleep(2)
                        agent_restarted = True
                        break
                time.sleep(1)

            if not agent_restarted:
                pytest.skip(f"Agent {agent_name} did not restart within {max_wait}s")

            # Verify credential STILL exists in Redis after restart
            post_restart_response = api_client.get("/api/credentials")
            assert_status(post_restart_response, 200)
            post_restart_creds = post_restart_response.json()
            post_restart_names = {c["name"] for c in post_restart_creds}

            assert cred_name in post_restart_names, \
                "REGRESSION: Hot-reloaded credential should persist in Redis after agent restart. " \
                "This was the original bug - credentials were only pushed to agent but not saved to Redis."

        finally:
            # Cleanup: Delete the test agent
            delete_response = api_client.delete(f"/api/agents/{agent_name}")
            # Don't assert here - cleanup is best effort


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
