"""
Test resource cleanup utilities.

Ensures test resources are properly cleaned up after tests.
"""

import re
from typing import List, Set
from .api_client import TrinityApiClient

# Pattern for test resources
TEST_RESOURCE_PATTERN = re.compile(r"^test-api-.*")


def get_test_agents(client: TrinityApiClient) -> List[str]:
    """Get list of test agent names that should be cleaned up."""
    response = client.get("/api/agents")
    if response.status_code != 200:
        return []

    agents = response.json()
    return [
        agent["name"]
        for agent in agents
        if TEST_RESOURCE_PATTERN.match(agent["name"])
    ]


def cleanup_test_agent(client: TrinityApiClient, name: str) -> bool:
    """Delete a test agent. Returns True if successful."""
    # First try to stop if running
    client.post(f"/api/agents/{name}/stop")

    # Then delete
    response = client.delete(f"/api/agents/{name}")
    return response.status_code in [200, 204, 404]


def cleanup_all_test_agents(client: TrinityApiClient) -> int:
    """Clean up all test agents. Returns count of deleted agents."""
    agents = get_test_agents(client)
    count = 0
    for name in agents:
        if cleanup_test_agent(client, name):
            count += 1
    return count


def get_test_credentials(client: TrinityApiClient) -> List[str]:
    """Get list of test credential IDs that should be cleaned up."""
    response = client.get("/api/credentials")
    if response.status_code != 200:
        return []

    credentials = response.json()
    return [
        cred["id"]
        for cred in credentials
        if cred.get("name", "").startswith("TEST_API_")
    ]


def cleanup_test_credential(client: TrinityApiClient, cred_id: str) -> bool:
    """Delete a test credential. Returns True if successful."""
    response = client.delete(f"/api/credentials/{cred_id}")
    return response.status_code in [200, 204, 404]


def cleanup_all_test_credentials(client: TrinityApiClient) -> int:
    """Clean up all test credentials. Returns count of deleted."""
    creds = get_test_credentials(client)
    count = 0
    for cred_id in creds:
        if cleanup_test_credential(client, cred_id):
            count += 1
    return count


def get_test_mcp_keys(client: TrinityApiClient) -> List[str]:
    """Get list of test MCP API key IDs that should be cleaned up."""
    response = client.get("/api/mcp/keys")
    if response.status_code != 200:
        return []

    keys = response.json()
    return [
        key["id"]
        for key in keys
        if key.get("name", "").startswith("test-api-")
    ]


def cleanup_test_mcp_key(client: TrinityApiClient, key_id: str) -> bool:
    """Delete a test MCP API key. Returns True if successful."""
    response = client.delete(f"/api/mcp/keys/{key_id}")
    return response.status_code in [200, 204, 404]


def cleanup_all_test_resources(client: TrinityApiClient) -> dict:
    """Clean up all test resources. Returns summary of deleted items."""
    return {
        "agents_deleted": cleanup_all_test_agents(client),
        "credentials_deleted": cleanup_all_test_credentials(client),
        "mcp_keys_deleted": len([
            key_id for key_id in get_test_mcp_keys(client)
            if cleanup_test_mcp_key(client, key_id)
        ]),
    }


class ResourceTracker:
    """Track created resources for cleanup."""

    def __init__(self):
        self.agents: Set[str] = set()
        self.credentials: Set[str] = set()
        self.mcp_keys: Set[str] = set()
        self.schedules: Set[tuple] = set()  # (agent_name, schedule_id)

    def track_agent(self, name: str):
        """Track an agent for cleanup."""
        self.agents.add(name)

    def track_credential(self, cred_id: str):
        """Track a credential for cleanup."""
        self.credentials.add(cred_id)

    def track_mcp_key(self, key_id: str):
        """Track an MCP key for cleanup."""
        self.mcp_keys.add(key_id)

    def track_schedule(self, agent_name: str, schedule_id: str):
        """Track a schedule for cleanup."""
        self.schedules.add((agent_name, schedule_id))

    def cleanup(self, client: TrinityApiClient) -> dict:
        """Clean up all tracked resources."""
        results = {
            "agents": 0,
            "credentials": 0,
            "mcp_keys": 0,
            "schedules": 0,
        }

        # Clean schedules first (they depend on agents)
        for agent_name, schedule_id in self.schedules:
            resp = client.delete(f"/api/agents/{agent_name}/schedules/{schedule_id}")
            if resp.status_code in [200, 204, 404]:
                results["schedules"] += 1

        # Clean agents
        for name in self.agents:
            if cleanup_test_agent(client, name):
                results["agents"] += 1

        # Clean credentials
        for cred_id in self.credentials:
            if cleanup_test_credential(client, cred_id):
                results["credentials"] += 1

        # Clean MCP keys
        for key_id in self.mcp_keys:
            if cleanup_test_mcp_key(client, key_id):
                results["mcp_keys"] += 1

        # Reset tracking
        self.agents.clear()
        self.credentials.clear()
        self.mcp_keys.clear()
        self.schedules.clear()

        return results
