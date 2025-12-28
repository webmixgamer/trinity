# Gemini Integration - Refactoring Plan

This document tracks necessary refactoring to fully support Gemini CLI as a runtime alongside Claude Code.

## Status: Planned

The core Gemini runtime is functional. These are polish items for full parity.

---

## 1. Instruction File Name - Make Runtime-Aware

### Current State
- `CLAUDE.md` is hardcoded throughout the codebase
- Gemini CLI uses the same file but the name is misleading

### Files to Update
- `docker/base-image/startup.sh` (lines 124-126)
- `docker/base-image/agent_server/routers/trinity.py` (lines 56, 166, 287)
- Template documentation

### Proposed Solution
Option A: Support both `CLAUDE.md` and `GEMINI.md` (runtime-specific)
Option B: Rename to generic `INSTRUCTIONS.md` or `AGENT.md`
Option C: Keep `CLAUDE.md` for backward compatibility (both runtimes read it)

**Recommendation**: Option C for now - both Claude Code and Gemini CLI can read `CLAUDE.md`. Document this in the guide.

---

## 2. MCP Injection - Add Gemini Support

### Current State
- `trinity_mcp.py` only writes to `.mcp.json` (Claude Code format)
- Gemini CLI uses `gemini mcp add <name> <command>` commands
- Agent-to-agent communication broken for Gemini agents

### Files to Update
- `docker/base-image/agent_server/services/trinity_mcp.py`
- `docker/base-image/agent_server/services/gemini_runtime.py`

### Proposed Solution
```python
def inject_trinity_mcp_if_configured() -> bool:
    """Inject Trinity MCP server - runtime aware."""
    runtime = os.getenv("AGENT_RUNTIME", "claude-code")

    if runtime == "gemini-cli":
        # Use: gemini mcp add trinity npx @anthropic/mcp-server-http ...
        return _inject_gemini_mcp()
    else:
        # Existing .mcp.json logic
        return _inject_claude_mcp()
```

---

## 3. Complete Gemini MCP Configuration

### Current State
- `GeminiRuntime.configure_mcp()` exists but is incomplete
- MCP servers from templates are not being configured

### Files to Update
- `docker/base-image/agent_server/services/gemini_runtime.py`

### Implementation
```python
def configure_mcp(self, mcp_servers: Dict) -> bool:
    """Configure MCP servers via Gemini CLI commands."""
    for server_name, config in mcp_servers.items():
        command = config.get("command", "")
        args = config.get("args", [])

        # gemini mcp add <name> <command> [args...]
        subprocess.run(["gemini", "mcp", "add", server_name, command] + args)

    return True
```

---

## 4. Tool Name Mapping (Low Priority)

### Current State
- Template `tools` array uses generic names: `["filesystem", "web_search"]`
- Both runtimes have similar built-in tools

### Assessment
- **Claude Code tools**: Read, Write, Edit, Bash, WebSearch, etc.
- **Gemini CLI tools**: read_file, write_file, run_shell_command, google_web_search, etc.

### Recommendation
No immediate action needed - both runtimes have equivalent built-in tools. The `tools` array in templates is informational, not used for actual tool restriction.

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 1 | MCP injection for Gemini | Medium | High - enables agent-to-agent |
| 2 | Complete `configure_mcp` | Low | Medium - enables custom MCP |
| 3 | Instruction file docs | Low | Low - clarity |
| 4 | Tool name mapping | Low | Low - cosmetic |

---

## Testing Checklist

After implementing:
- [ ] Gemini agent can chat with Trinity MCP
- [ ] Gemini agent can delegate to other agents
- [ ] Custom MCP servers work with Gemini agents
- [ ] Template MCP configurations apply correctly
- [ ] Vector memory (Chroma MCP) works with Gemini

---

## Related Documentation
- [Gemini Support Guide](../GEMINI_SUPPORT.md)
- [Trinity Compatible Agent Guide](../TRINITY_COMPATIBLE_AGENT_GUIDE.md)
- [Multi-Runtime Architecture](../memory/requirements.md#12-multi-runtime-support)

