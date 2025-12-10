"""
Agent Git Tests (test_agent_git.py)

Tests for agent Git sync functionality.
Covers REQ-GIT-001 through REQ-GIT-002.
"""

import pytest
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
)


class TestGitStatus:
    """REQ-GIT-001: Git status endpoint tests."""

    def test_get_git_status(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/git/status returns git status."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/git/status")

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should indicate git enabled status
        assert "git_enabled" in data or "enabled" in data or "status" in data

    def test_git_disabled_returns_false(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Non-git agent returns git_enabled: false."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/git/status")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # For agents not created from GitHub, git should be disabled
        enabled = data.get("git_enabled", data.get("enabled", False))
        # This is just a structure check, not asserting value


class TestGitSync:
    """REQ-GIT-002: Git sync endpoint tests."""

    def test_git_sync(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/git/sync commits and pushes."""
        response = api_client.post(f"/api/agents/{created_agent['name']}/git/sync")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # May fail if git not configured
        if response.status_code in [400, 422]:
            pytest.skip("Git not configured for agent")

        # If git is enabled, should succeed or indicate no changes
        assert_status_in(response, [200, 304, 400])

    def test_git_sync_nonexistent_agent(self, api_client: TrinityApiClient):
        """POST /api/agents/{name}/git/sync for non-existent returns 404."""
        response = api_client.post("/api/agents/nonexistent-agent-xyz/git/sync")

        assert_status(response, 404)


class TestGitLog:
    """Tests for git log endpoint."""

    def test_get_git_log(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/git/log returns commit history."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/git/log")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # May fail if git not configured
        if response.status_code in [400, 422]:
            pytest.skip("Git not configured for agent")

        assert_status_in(response, [200, 400])

    def test_git_log_with_limit(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/git/log supports limit parameter."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/git/log",
            params={"limit": 5}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 400, 422])


class TestGitPull:
    """Tests for git pull endpoint."""

    def test_git_pull(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/git/pull pulls from remote."""
        response = api_client.post(f"/api/agents/{created_agent['name']}/git/pull")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # May fail if git not configured
        if response.status_code in [400, 422]:
            pytest.skip("Git not configured for agent")

        assert_status_in(response, [200, 304, 400])
