"""
Trinity MCP injection service for agent-to-agent collaboration.

Supports both Claude Code (.mcp.json) and Gemini CLI (gemini mcp add).
"""
import os
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def inject_trinity_mcp_if_configured() -> bool:
    """
    Inject Trinity MCP server - runtime aware.

    This enables agent-to-agent communication via the Trinity platform.
    Called on agent startup.

    For Claude Code: Writes to ~/.mcp.json
    For Gemini CLI: Uses `gemini mcp add` command
    """
    trinity_mcp_url = os.getenv("TRINITY_MCP_URL")
    trinity_mcp_api_key = os.getenv("TRINITY_MCP_API_KEY")

    if not trinity_mcp_url or not trinity_mcp_api_key:
        logger.info("Trinity MCP not configured - skipping injection")
        return False

    runtime = os.getenv("AGENT_RUNTIME", "claude-code").lower()

    if runtime == "gemini-cli":
        return _inject_gemini_mcp(trinity_mcp_url, trinity_mcp_api_key)
    else:
        return _inject_claude_mcp(trinity_mcp_url, trinity_mcp_api_key)


def _inject_claude_mcp(trinity_mcp_url: str, trinity_mcp_api_key: str) -> bool:
    """Inject Trinity MCP into Claude Code's .mcp.json file."""
    home_dir = Path("/home/developer")
    mcp_file = home_dir / ".mcp.json"

    # Trinity MCP server configuration using HTTP transport
    trinity_mcp_entry = {
        "trinity": {
            "type": "http",
            "url": trinity_mcp_url,
            "headers": {
                "Authorization": f"Bearer {trinity_mcp_api_key}"
            }
        }
    }

    try:
        # Read existing .mcp.json if it exists
        if mcp_file.exists():
            content = mcp_file.read_text()
            if content.strip():
                mcp_config = json.loads(content)
            else:
                mcp_config = {"mcpServers": {}}
        else:
            mcp_config = {"mcpServers": {}}

        # Ensure mcpServers key exists
        if "mcpServers" not in mcp_config:
            mcp_config["mcpServers"] = {}

        # Add Trinity MCP (overwrite if exists)
        mcp_config["mcpServers"]["trinity"] = trinity_mcp_entry["trinity"]

        # Write back to file
        mcp_file.write_text(json.dumps(mcp_config, indent=2))
        logger.info(f"Injected Trinity MCP server into {mcp_file} (Claude Code)")
        return True

    except Exception as e:
        logger.warning(f"Failed to inject Trinity MCP for Claude Code: {e}")
        return False


def _inject_gemini_mcp(trinity_mcp_url: str, trinity_mcp_api_key: str) -> bool:
    """
    Inject Trinity MCP into Gemini CLI using `gemini mcp add` command.

    Gemini CLI uses commands instead of config files:
    gemini mcp add <name> <command> [args...]

    For HTTP MCP servers, we use npx with @anthropic/mcp-server-http
    """
    try:
        # First, remove existing trinity MCP if present
        subprocess.run(
            ["gemini", "mcp", "remove", "trinity"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Gemini CLI can use HTTP MCP servers via the mcp-server-http bridge
        # The command format is: gemini mcp add <name> npx @anthropic/mcp-server-http <url>
        # With auth header passed as environment variable

        # For Gemini, we need to use a wrapper script or environment variable approach
        # Create a wrapper script that sets the auth header
        wrapper_script = Path("/home/developer/.trinity-mcp-wrapper.sh")
        wrapper_content = f"""#!/bin/bash
export MCP_HTTP_AUTH="Bearer {trinity_mcp_api_key}"
exec npx -y @anthropic-ai/mcp-server-fetch "$@"
"""
        # Note: mcp-server-fetch can be used, or we can use a direct HTTP approach

        # Alternative: Use environment variable in Gemini's settings
        # For now, let's try adding with the URL directly
        # Gemini CLI may support HTTP MCP natively in newer versions

        result = subprocess.run(
            [
                "gemini", "mcp", "add", "trinity",
                "npx", "-y", "@anthropic-ai/mcp-server-http",
                "--url", trinity_mcp_url,
                "--header", f"Authorization: Bearer {trinity_mcp_api_key}"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            logger.info("Injected Trinity MCP server via gemini mcp add (Gemini CLI)")
            return True
        else:
            # Try alternative approach - just add the HTTP URL
            logger.warning(f"First injection attempt failed: {result.stderr}")

            # Try simpler command format
            result2 = subprocess.run(
                [
                    "gemini", "mcp", "add", "trinity",
                    "npx", "@anthropic-ai/mcp-server-http", trinity_mcp_url
                ],
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    **os.environ,
                    "MCP_HTTP_HEADERS": json.dumps({"Authorization": f"Bearer {trinity_mcp_api_key}"})
                }
            )

            if result2.returncode == 0:
                logger.info("Injected Trinity MCP server (alternative method)")
                return True
            else:
                logger.warning(f"Gemini MCP injection failed: {result2.stderr}")
                return False

    except subprocess.TimeoutExpired:
        logger.warning("Gemini MCP injection timed out")
        return False
    except Exception as e:
        logger.warning(f"Failed to inject Trinity MCP for Gemini CLI: {e}")
        return False


def configure_mcp_servers(mcp_servers: dict) -> bool:
    """
    Configure additional MCP servers for the agent - runtime aware.

    Args:
        mcp_servers: Dict of server configs from template
                     {"server_name": {"command": "...", "args": [...]}}
    """
    if not mcp_servers:
        return True

    runtime = os.getenv("AGENT_RUNTIME", "claude-code").lower()

    if runtime == "gemini-cli":
        return _configure_gemini_mcp_servers(mcp_servers)
    else:
        return _configure_claude_mcp_servers(mcp_servers)


def _configure_claude_mcp_servers(mcp_servers: dict) -> bool:
    """Configure MCP servers for Claude Code via .mcp.json."""
    home_dir = Path("/home/developer")
    mcp_file = home_dir / ".mcp.json"

    try:
        if mcp_file.exists():
            content = mcp_file.read_text()
            mcp_config = json.loads(content) if content.strip() else {"mcpServers": {}}
        else:
            mcp_config = {"mcpServers": {}}

        if "mcpServers" not in mcp_config:
            mcp_config["mcpServers"] = {}

        # Add each MCP server
        for server_name, config in mcp_servers.items():
            mcp_config["mcpServers"][server_name] = config

        mcp_file.write_text(json.dumps(mcp_config, indent=2))
        logger.info(f"Configured {len(mcp_servers)} MCP servers for Claude Code")
        return True

    except Exception as e:
        logger.warning(f"Failed to configure MCP servers for Claude Code: {e}")
        return False


def _configure_gemini_mcp_servers(mcp_servers: dict) -> bool:
    """Configure MCP servers for Gemini CLI via `gemini mcp add` commands."""
    success_count = 0

    for server_name, config in mcp_servers.items():
        try:
            command = config.get("command", "")
            args = config.get("args", [])

            if not command:
                logger.warning(f"Skipping MCP server '{server_name}': no command specified")
                continue

            # Build the gemini mcp add command
            cmd = ["gemini", "mcp", "add", server_name, command] + args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Added MCP server '{server_name}' for Gemini CLI")
                success_count += 1
            else:
                logger.warning(f"Failed to add MCP server '{server_name}': {result.stderr}")

        except Exception as e:
            logger.warning(f"Error adding MCP server '{server_name}': {e}")

    logger.info(f"Configured {success_count}/{len(mcp_servers)} MCP servers for Gemini CLI")
    return success_count > 0 or len(mcp_servers) == 0
