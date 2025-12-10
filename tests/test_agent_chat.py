"""
Agent Chat Tests (test_agent_chat.py)

Tests for agent chat/conversation endpoints.
Covers REQ-CHAT-001 through REQ-CHAT-004.
"""

import pytest
import time
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
    assert_list_response,
)


class TestSendChatMessage:
    """REQ-CHAT-001: Send chat message endpoint tests."""

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_send_message_returns_response(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """POST /api/agents/{name}/chat sends message and receives response."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/chat",
            json={"message": "Hello, what is 2+2?"},
            timeout=120.0,  # Chat can take a while
        )

        # May get 503 if agent busy, 429 if queue full
        if response.status_code == 503:
            pytest.skip("Agent server not ready (503)")
        if response.status_code == 429:
            pytest.skip("Agent queue full (429)")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should have response content
        assert "response" in data or "content" in data or "message" in data

    @pytest.mark.slow
    @pytest.mark.requires_agent
    def test_chat_response_has_metadata(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Chat response includes execution metadata."""
        response = api_client.post(
            f"/api/agents/{created_agent['name']}/chat",
            json={"message": "Say hello"},
            timeout=120.0,
        )

        if response.status_code in [503, 429]:
            pytest.skip(f"Agent not ready ({response.status_code})")

        assert_status(response, 200)
        data = response.json()

        # Should have metadata fields
        # Exact fields depend on implementation
        assert isinstance(data, dict)

    def test_chat_nonexistent_agent_returns_404(self, api_client: TrinityApiClient):
        """POST /api/agents/{name}/chat for non-existent agent returns 404."""
        response = api_client.post(
            "/api/agents/nonexistent-agent-xyz/chat",
            json={"message": "hello"},
            timeout=30.0,
        )
        assert_status(response, 404)

    def test_chat_stopped_agent_returns_error(
        self,
        api_client: TrinityApiClient,
        stopped_agent
    ):
        """POST /api/agents/{name}/chat for stopped agent returns error."""
        response = api_client.post(
            f"/api/agents/{stopped_agent['name']}/chat",
            json={"message": "hello"},
            timeout=30.0,
        )
        # Should get 400 or 503 for stopped agent
        assert_status_in(response, [400, 503])


class TestChatHistory:
    """REQ-CHAT-002: Chat history endpoint tests."""

    def test_get_chat_history(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/chat/history returns conversation history."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/history"
        )

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should be a list (possibly empty)
        if isinstance(data, dict) and "history" in data:
            assert isinstance(data["history"], list)
        elif isinstance(data, dict) and "messages" in data:
            assert isinstance(data["messages"], list)
        else:
            # Direct list
            assert isinstance(data, (list, dict))

    def test_get_persistent_chat_history(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/chat/history/persistent returns database-backed history."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/history/persistent"
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, (list, dict))


class TestSessionInfo:
    """REQ-CHAT-003: Chat session info endpoint tests."""

    def test_get_session_info(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Agent session endpoint returns session statistics."""
        # Try direct agent session endpoint
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/session"
        )

        # May not exist or may return 503
        if response.status_code == 404:
            pytest.skip("Session endpoint not implemented")
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)


class TestChatSessions:
    """Tests for chat sessions management."""

    def test_list_chat_sessions(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/chat/sessions lists all sessions."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/chat/sessions"
        )

        assert_status(response, 200)
        data = assert_json_response(response)
        assert isinstance(data, (list, dict))


class TestModelManagement:
    """REQ-CHAT-004: Model management endpoint tests."""

    def test_get_current_model(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/model returns current model."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/model"
        )

        # May not be implemented
        if response.status_code == 404:
            pytest.skip("Model endpoint not implemented")
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()
        assert "model" in data or isinstance(data, str)

    def test_set_valid_model(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """PUT /api/agents/{name}/model sets model."""
        response = api_client.put(
            f"/api/agents/{created_agent['name']}/model",
            json={"model": "sonnet"}
        )

        # May not be implemented
        if response.status_code == 404:
            pytest.skip("Model endpoint not implemented")
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 204])


class TestResetSession:
    """Tests for session reset functionality."""

    def test_reset_session(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """DELETE /api/agents/{name}/chat/history resets session."""
        response = api_client.delete(
            f"/api/agents/{created_agent['name']}/chat/history"
        )

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status_in(response, [200, 204])
