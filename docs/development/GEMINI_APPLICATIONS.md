# Gemini Integration - Refactoring Plan

This document tracks necessary refactoring to fully support Gemini CLI as a runtime alongside Claude Code.

## Status: ✅ Implemented (2025-12-28)

The core Gemini runtime is functional. All priority items have been implemented.

---

## 1. Instruction File Name - Make Runtime-Aware

### Status: ✅ Documented (Option C selected)

**Decision**: Keep `CLAUDE.md` for backward compatibility - both runtimes read it.

- Both Claude Code and Gemini CLI understand markdown instruction files
- No code changes needed - documented in [GEMINI_SUPPORT.md](../GEMINI_SUPPORT.md)
- Renaming would break existing templates without benefit

---

## 2. MCP Injection - Add Gemini Support

### Status: ✅ Implemented

**Files Updated**:
- `docker/base-image/agent_server/services/trinity_mcp.py`

**Implementation**:
```python
def inject_trinity_mcp_if_configured() -> bool:
    """Inject Trinity MCP server - runtime aware."""
    runtime = os.getenv("AGENT_RUNTIME", "claude-code")

    if runtime == "gemini-cli":
        return _inject_gemini_mcp(url, key)  # gemini mcp add
    else:
        return _inject_claude_mcp(url, key)  # .mcp.json
```

New functions added:
- `_inject_claude_mcp()` - writes to `.mcp.json`
- `_inject_gemini_mcp()` - uses `gemini mcp add` command
- `configure_mcp_servers()` - shared runtime-aware MCP config
- `_configure_claude_mcp_servers()` - Claude-specific
- `_configure_gemini_mcp_servers()` - Gemini-specific

---

## 3. Complete Gemini MCP Configuration

### Status: ✅ Implemented

**Files Updated**:
- `docker/base-image/agent_server/services/gemini_runtime.py`

**Implementation**:
`GeminiRuntime.configure_mcp()` now delegates to shared `_configure_gemini_mcp_servers()` function for consistency.

---

## 4. Tool Name Mapping (Low Priority)

### Status: ⏸️ Deferred

No action needed - both runtimes have equivalent built-in tools:

| Generic Name | Claude Code | Gemini CLI |
|--------------|-------------|------------|
| filesystem | Read, Write, Edit | read_file, write_file, replace |
| shell | Bash | run_shell_command |
| web_search | WebSearch | google_web_search |
| memory | Task | save_memory |

The `tools` array in templates is informational only.

---

## Implementation Summary

| Priority | Item | Status | Commit |
|----------|------|--------|--------|
| 1 | MCP injection for Gemini | ✅ Done | 2025-12-28 |
| 2 | Complete `configure_mcp` | ✅ Done | 2025-12-28 |
| 3 | Instruction file docs | ✅ Done | 2025-12-28 |
| 4 | Tool name mapping | ⏸️ Deferred | N/A |

---

## Testing Checklist

After implementing:
- [x] Gemini agent can use Trinity MCP (via `gemini mcp add`)
- [ ] Gemini agent can delegate to other agents (needs testing)
- [x] Custom MCP servers work with Gemini agents
- [x] Template MCP configurations apply correctly
- [ ] Vector memory (Chroma MCP) works with Gemini (needs testing)

---

## Related Documentation
- [Gemini Support Guide](../GEMINI_SUPPORT.md)
- [Trinity Compatible Agent Guide](../TRINITY_COMPATIBLE_AGENT_GUIDE.md)
- [Multi-Runtime Architecture](../memory/requirements.md#12-multi-runtime-support)
- [Delegation Best Practices](../MULTI_AGENT_SYSTEM_GUIDE.md#delegation-best-practices)

