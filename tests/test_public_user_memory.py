"""
Per-User Persistent Memory for Public Link Agents (test_public_user_memory.py)

Tests for MEM-001: per-user memory scoped to (agent_name, user_email),
injected into system prompt for email-verified sessions and updated via
background summarization every 5 messages.

Feature: Issue #147
"""

import os
import sys
import sqlite3
import pytest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

# Add backend to sys.path for direct imports
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ============================================================================
# Helpers
# ============================================================================

def _make_in_memory_conn():
    """In-memory SQLite connection with public_user_memory schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE public_user_memory (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            user_email TEXT NOT NULL,
            memory_text TEXT NOT NULL DEFAULT '',
            message_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(agent_name, user_email)
        )
    """)
    conn.commit()
    return conn


def _fake_db_for(conn):
    """Return a get_db_connection replacement that yields the given conn."""
    @contextmanager
    def _ctx():
        yield conn
        conn.commit()
    return _ctx


# ============================================================================
# DB layer unit tests
# ============================================================================

@pytest.mark.unit
class TestPublicUserMemoryDB:
    """Unit tests for PublicLinkOperations user-memory methods."""

    def setup_method(self):
        """Fresh in-memory DB per test."""
        self.conn = _make_in_memory_conn()
        self.fake_db = _fake_db_for(self.conn)

    def _ops(self):
        """Import (or re-use cached) PublicLinkOperations with DB patched."""
        # Ensure the module is importable. The patch replaces get_db_connection
        # at the db.connection level so all callers pick it up.
        with patch("db.connection.get_db_connection", self.fake_db):
            import importlib
            import db.public_links as mod
            importlib.reload(mod)
            return mod.PublicLinkOperations()

    def test_get_or_create_creates_empty_record(self):
        """First call creates a row with empty memory_text."""
        conn = self.conn
        fake_db = self.fake_db

        # Patch get_db_connection in the module under test
        import importlib
        import db.public_links as mod

        # Monkeypatch at module level
        original = mod.get_db_connection
        mod.get_db_connection = fake_db
        try:
            ops = mod.PublicLinkOperations()
            record = ops.get_or_create_user_memory("agent1", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert record["agent_name"] == "agent1"
        assert record["user_email"] == "user@example.com"
        assert record["memory_text"] == ""
        assert record["message_count"] == 0
        assert record["id"]

    def test_get_or_create_is_idempotent(self):
        """Second call returns the same row — no duplicate created."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            r1 = ops.get_or_create_user_memory("agent1", "user@example.com")
            r2 = ops.get_or_create_user_memory("agent1", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert r1["id"] == r2["id"]

    def test_update_user_memory_persists_text(self):
        """update_user_memory writes new text and returns True."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            ops.get_or_create_user_memory("agent1", "user@example.com")
            updated = ops.update_user_memory("agent1", "user@example.com", "- Prefers Python\n- Name: Alice")
            record = ops.get_or_create_user_memory("agent1", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert updated is True
        assert record["memory_text"] == "- Prefers Python\n- Name: Alice"

    def test_update_nonexistent_returns_false(self):
        """update_user_memory returns False when no row exists."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            result = ops.update_user_memory("ghost-agent", "nobody@example.com", "text")
        finally:
            mod.get_db_connection = original

        assert result is False

    def test_increment_message_count_increments_sequentially(self):
        """increment_message_count returns new count each call."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            ops.get_or_create_user_memory("agent1", "user@example.com")
            c1 = ops.increment_message_count("agent1", "user@example.com")
            c2 = ops.increment_message_count("agent1", "user@example.com")
            c3 = ops.increment_message_count("agent1", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert c1 == 1
        assert c2 == 2
        assert c3 == 3

    def test_email_is_normalized_to_lowercase(self):
        """Memory records normalize email to lowercase."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            r1 = ops.get_or_create_user_memory("agent1", "User@Example.COM")
            r2 = ops.get_or_create_user_memory("agent1", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert r1["id"] == r2["id"]
        assert r1["user_email"] == "user@example.com"

    def test_memory_is_scoped_per_agent(self):
        """Different agents get separate memory records for the same user email."""
        import db.public_links as mod
        original = mod.get_db_connection
        mod.get_db_connection = self.fake_db
        try:
            ops = mod.PublicLinkOperations()
            r1 = ops.get_or_create_user_memory("agent-a", "user@example.com")
            r2 = ops.get_or_create_user_memory("agent-b", "user@example.com")
        finally:
            mod.get_db_connection = original

        assert r1["id"] != r2["id"]


# ============================================================================
# Platform prompt service unit tests
# ============================================================================

@pytest.mark.unit
class TestFormatUserMemoryBlock:
    """Unit tests for platform_prompt_service.format_user_memory_block."""

    @staticmethod
    def _import():
        """Import format_user_memory_block with database stubbed out."""
        mock_db = MagicMock()
        mock_db.get_setting_value.return_value = None
        # Stub the database module so platform_prompt_service can be imported
        import sys
        fake_database = MagicMock()
        fake_database.db = mock_db
        # Remove cached version so reimport with stub works
        sys.modules.pop("services.platform_prompt_service", None)
        with patch.dict("sys.modules", {"database": fake_database}):
            import services.platform_prompt_service as svc
            return svc.format_user_memory_block

    def test_block_contains_header(self):
        fn = self._import()
        block = fn("- Name: Alice")
        assert "## What you know about this user" in block

    def test_block_contains_memory_text(self):
        fn = self._import()
        block = fn("- Name: Alice\n- Prefers Python")
        assert "- Name: Alice" in block
        assert "- Prefers Python" in block

    def test_block_trims_whitespace(self):
        fn = self._import()
        block = fn("   - Likes coffee   ")
        content = block.split("## What you know about this user")[1].split("---")[0]
        assert content.strip() == "- Likes coffee"

    def test_block_ends_with_separator(self):
        fn = self._import()
        block = fn("- Fact")
        assert block.strip().endswith("---")
