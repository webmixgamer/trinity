"""
Authentication Tests (test_auth.py)

Tests for Trinity authentication endpoints.
Covers REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-003.

FAST TESTS - No agent creation required.
"""

import pytest

# Mark all tests in this module as smoke tests (fast, no agent needed)
pytestmark = pytest.mark.smoke
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestAuthenticationMode:
    """REQ-AUTH-001: Authentication mode endpoint tests."""

    @pytest.mark.smoke
    def test_auth_mode_returns_valid_response(self, unauthenticated_client: TrinityApiClient):
        """GET /api/auth/mode returns valid mode configuration."""
        response = unauthenticated_client.get("/api/auth/mode", auth=False)

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["dev_mode_enabled"])

    def test_auth_mode_returns_dev_or_auth0(self, unauthenticated_client: TrinityApiClient):
        """Auth mode should indicate dev_mode_enabled status."""
        response = unauthenticated_client.get("/api/auth/mode", auth=False)

        assert_status(response, 200)
        data = response.json()
        assert "dev_mode_enabled" in data
        assert isinstance(data["dev_mode_enabled"], bool)

    def test_auth_mode_accessible_without_auth(self, unauthenticated_client: TrinityApiClient):
        """Auth mode endpoint should be accessible without authentication."""
        response = unauthenticated_client.get("/api/auth/mode", auth=False)
        assert_status(response, 200)


class TestLogin:
    """REQ-AUTH-002: Login (dev mode) endpoint tests."""

    @pytest.mark.smoke
    def test_valid_credentials_returns_token(self, api_config, unauthenticated_client: TrinityApiClient):
        """POST /token with valid credentials returns JWT token."""
        response = unauthenticated_client._client.post(
            "/token",
            data={
                "username": api_config.username,
                "password": api_config.password,
            },
        )

        # In dev mode, should return 200; in prod mode (auth0), returns 403
        if response.status_code == 403:
            pytest.skip("Dev mode login disabled (auth0 mode)")

        assert_status(response, 200)
        data = assert_json_response(response)
        assert_has_fields(data, ["access_token", "token_type"])
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_invalid_credentials_returns_401(self, unauthenticated_client: TrinityApiClient):
        """POST /token with invalid credentials returns 401."""
        response = unauthenticated_client._client.post(
            "/token",
            data={
                "username": "invalid_user",
                "password": "wrong_password",
            },
        )

        # Skip if auth0 mode
        if response.status_code == 403:
            pytest.skip("Dev mode login disabled (auth0 mode)")

        assert_status(response, 401)

    def test_missing_credentials_returns_422(self, unauthenticated_client: TrinityApiClient):
        """POST /token with missing credentials returns 422."""
        response = unauthenticated_client._client.post("/token", data={})

        # Skip if auth0 mode
        if response.status_code == 403:
            pytest.skip("Dev mode login disabled (auth0 mode)")

        assert_status(response, 422)

    def test_token_can_be_used_for_auth(self, api_config, unauthenticated_client: TrinityApiClient):
        """Token from login can be used for authenticated requests."""
        # Get token
        response = unauthenticated_client._client.post(
            "/token",
            data={
                "username": api_config.username,
                "password": api_config.password,
            },
        )

        if response.status_code == 403:
            pytest.skip("Dev mode login disabled (auth0 mode)")

        token = response.json()["access_token"]

        # Use token for authenticated request
        auth_response = unauthenticated_client._client.get(
            "/api/agents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert_status(auth_response, 200)


class TestTokenValidation:
    """REQ-AUTH-003: Token validation endpoint tests."""

    def test_valid_token_returns_user_info(self, api_client: TrinityApiClient):
        """GET /api/auth/validate with valid token returns user info."""
        response = api_client.get("/api/auth/validate")

        assert_status(response, 200)
        data = assert_json_response(response)
        # Should have validation status and user info
        assert "status" in data or "valid" in data or "user" in data

    def test_missing_token_returns_401(self, unauthenticated_client: TrinityApiClient):
        """GET /api/auth/validate without token returns 401."""
        response = unauthenticated_client.get("/api/auth/validate", auth=False)
        assert_status_in(response, [401, 403])

    def test_invalid_token_returns_401(self, unauthenticated_client: TrinityApiClient):
        """GET /api/auth/validate with invalid token returns 401."""
        response = unauthenticated_client._client.get(
            "/api/auth/validate",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert_status_in(response, [401, 403])

    def test_malformed_token_returns_401(self, unauthenticated_client: TrinityApiClient):
        """GET /api/auth/validate with malformed token returns 401."""
        response = unauthenticated_client._client.get(
            "/api/auth/validate",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        )
        assert_status_in(response, [401, 403])


class TestUserEndpoint:
    """Tests for user info endpoint."""

    def test_get_current_user(self, api_client: TrinityApiClient):
        """GET /api/users/me returns current user info."""
        response = api_client.get("/api/users/me")

        assert_status(response, 200)
        data = assert_json_response(response)
        # Should have user identification fields
        assert "id" in data or "email" in data or "username" in data


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.smoke
    def test_health_check(self, unauthenticated_client: TrinityApiClient):
        """GET /health returns healthy status."""
        response = unauthenticated_client.get("/health", auth=False)

        assert_status(response, 200)
        data = assert_json_response(response)
        assert data.get("status") == "healthy" or "health" in str(data).lower()
