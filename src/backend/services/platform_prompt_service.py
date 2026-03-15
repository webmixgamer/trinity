"""
Platform Prompt Service — Single source of truth for platform instructions.

Builds the system prompt that is injected into every Claude Code invocation
via --append-system-prompt. Replaces the old file-based CLAUDE.local.md injection.
"""
import logging
from database import db

logger = logging.getLogger(__name__)

# Static platform instructions — moved from agent-side trinity.py
PLATFORM_INSTRUCTIONS = """# Trinity Platform Instructions

## Trinity Agent System

This agent is part of the Trinity Deep Agent Orchestration Platform.

### Agent Collaboration

You can collaborate with other agents using the Trinity MCP tools:

- `mcp__trinity__list_agents()` - See agents you can communicate with
- `mcp__trinity__chat_with_agent(agent_name, message)` - Delegate tasks to other agents

**Note**: You can only communicate with agents you have been granted permission to access.
Use `list_agents` to discover your available collaborators.

### Operator Communication

See @.trinity/prompt.md for the full operator communication protocol.

### Package Persistence

When installing system packages (apt-get, npm -g, etc.), add them to your setup script so they persist across container updates:

```bash
# Install package
sudo apt-get install -y ffmpeg

# Add to persistent setup script
mkdir -p ~/.trinity
echo "sudo apt-get install -y ffmpeg" >> ~/.trinity/setup.sh
```

This script runs automatically on container start. Always update it when installing system-level packages."""


def get_platform_system_prompt() -> str:
    """
    Build the full platform system prompt.

    Combines static platform instructions with the operator's custom prompt
    from the trinity_prompt database setting.

    Returns:
        Combined system prompt string
    """
    parts = [PLATFORM_INSTRUCTIONS]

    # Append custom prompt from database setting (operator-configurable)
    custom_prompt = db.get_setting_value("trinity_prompt", default=None)
    if custom_prompt and custom_prompt.strip():
        parts.append(f"\n\n## Custom Instructions\n\n{custom_prompt.strip()}")
        logger.debug(f"Including custom trinity_prompt ({len(custom_prompt)} chars)")

    return "".join(parts)
