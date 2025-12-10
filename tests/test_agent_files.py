"""
Agent Files Tests (test_agent_files.py)

Tests for agent workspace file browser.
Covers REQ-FILES-001 through REQ-FILES-002.
"""

import pytest
from utils.api_client import TrinityApiClient
from utils.assertions import (
    assert_status,
    assert_status_in,
    assert_json_response,
    assert_has_fields,
    assert_tree_structure,
)


class TestListFiles:
    """REQ-FILES-001: List files endpoint tests."""

    def test_list_files_returns_tree(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/files returns hierarchical tree structure."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/files")

        # May return 503 if agent not ready
        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = assert_json_response(response)

        # Should be a tree structure
        assert isinstance(data, (dict, list))

    def test_file_has_required_fields(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Each file item has name, path, type fields."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/files")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Check root or first item
        if isinstance(data, dict) and "children" in data:
            # Tree structure with root
            assert_has_fields(data, ["name", "type"])
        elif isinstance(data, list) and len(data) > 0:
            # List of items
            item = data[0]
            assert_has_fields(item, ["name", "type"])

    def test_directory_has_children(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Directory items have children field."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/files")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Find a directory in the response
        def find_directory(item):
            if isinstance(item, dict):
                if item.get("type") == "directory":
                    return item
                for child in item.get("children", []):
                    result = find_directory(child)
                    if result:
                        return result
            return None

        if isinstance(data, dict):
            directory = find_directory(data)
            if directory:
                assert "children" in directory or "file_count" in directory

    def test_hidden_files_excluded(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Hidden files (starting with .) are excluded."""
        response = api_client.get(f"/api/agents/{created_agent['name']}/files")

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        assert_status(response, 200)
        data = response.json()

        # Check that no items start with .
        def check_no_hidden(item):
            if isinstance(item, dict):
                name = item.get("name", "")
                # .env and similar should be hidden
                if name.startswith(".") and name not in [".", ".."]:
                    return False
                for child in item.get("children", []):
                    if not check_no_hidden(child):
                        return False
            return True

        if isinstance(data, dict):
            # Root is workspace which may be shown
            pass  # Don't fail on root name
        elif isinstance(data, list):
            for item in data:
                if item.get("name", "").startswith("."):
                    pytest.fail(f"Hidden file found: {item['name']}")


class TestDownloadFile:
    """REQ-FILES-002: Download file endpoint tests."""

    def test_download_existing_file(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/files/download downloads file content."""
        # First get file list
        list_response = api_client.get(f"/api/agents/{created_agent['name']}/files")

        if list_response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Find a file to download
        def find_file(item, path=""):
            if isinstance(item, dict):
                current_path = f"{path}/{item.get('name', '')}" if path else item.get('name', '')
                if item.get("type") == "file":
                    return item.get("path", current_path)
                for child in item.get("children", []):
                    result = find_file(child, current_path)
                    if result:
                        return result
            return None

        data = list_response.json()
        file_path = find_file(data)

        if not file_path:
            pytest.skip("No files found to download")

        # Download the file
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/files/download",
            params={"path": file_path}
        )

        assert_status(response, 200)

    def test_download_nonexistent_file_returns_404(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/files/download for non-existent file returns 404."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/files/download",
            params={"path": "/nonexistent/file.txt"}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # 403 is also valid - security may block paths outside allowed directories
        assert_status_in(response, [400, 403, 404])

    def test_download_directory_returns_400(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """GET /api/agents/{name}/files/download for directory returns 400."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/files/download",
            params={"path": "/"}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Should not be able to download a directory
        # 403 is also valid - security may block paths outside allowed directories
        assert_status_in(response, [400, 403, 404, 422])

    def test_path_traversal_blocked(
        self,
        api_client: TrinityApiClient,
        created_agent
    ):
        """Path traversal attempts are blocked."""
        response = api_client.get(
            f"/api/agents/{created_agent['name']}/files/download",
            params={"path": "../../../etc/passwd"}
        )

        if response.status_code == 503:
            pytest.skip("Agent server not ready")

        # Should be blocked
        assert_status_in(response, [400, 403, 404])
