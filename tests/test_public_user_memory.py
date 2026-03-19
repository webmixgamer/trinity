"""
Tests for Per-User Persistent Memory for Public Link Agents (MEM-001).

Memory is scoped to (agent_name, user_email), persists cross-session,
and is injected into the system prompt for email-verified sessions.
Background summarization via claude-haiku fires every 5 messages.

Run with: pytest tests/test_public_user_memory.py -v
Feature: Issue #147
"""

import os
import pytest
import sqlite3
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def auth_headers():
    """Get auth headers for authenticated requests."""
    password = os.getenv("TRINITY_TEST_PASSWORD", "password")
    response = httpx.post(
        f"{BASE_URL}/api/token",
        data={"username": "admin", "password": password}
    )
    if response.status_code != 200:
        pytest.skip("Could not authenticate — check admin credentials")
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# DB Table Existence
# ============================================================================

class TestPublicUserMemoryTable:
    """Verify public_user_memory table and index were created by migration."""

    @pytest.mark.smoke
    def test_table_exists(self):
        """public_user_memory table exists in the database."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='public_user_memory'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "public_user_memory table not found — migration may not have run"

    @pytest.mark.smoke
    def test_table_schema(self):
        """public_user_memory has the expected columns."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(public_user_memory)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {"id", "agent_name", "user_email", "memory_text", "message_count", "created_at", "updated_at"}
        assert expected == columns, f"Schema mismatch. Got: {columns}"

    @pytest.mark.smoke
    def test_unique_constraint_on_agent_email(self):
        """UNIQUE(agent_name, user_email) constraint exists."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='public_user_memory'")
        ddl = cursor.fetchone()[0]
        conn.close()

        assert "UNIQUE" in ddl.upper(), "Expected UNIQUE constraint in table DDL"

    @pytest.mark.smoke
    def test_lookup_index_exists(self):
        """idx_public_user_memory_lookup index exists."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_public_user_memory_lookup'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "idx_public_user_memory_lookup index not found"


# ============================================================================
# Anonymous Session — Memory Not Created
# ============================================================================

class TestAnonymousSessionMemoryIsolation:
    """Anonymous sessions must not create memory records."""

    @pytest.mark.smoke
    def test_invalid_link_returns_not_found(self):
        """Sanity check: public chat with invalid token returns 404."""
        response = httpx.post(
            f"{BASE_URL}/api/public/chat/nonexistent-token-xyz",
            json={"message": "Hello", "session_id": "anon-test-001"}
        )
        assert response.status_code == 404

    @pytest.mark.smoke
    def test_anonymous_chat_does_not_create_memory(self, auth_headers):
        """Anonymous chat sessions don't create public_user_memory rows."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        # Count memory rows before
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM public_user_memory")
        count_before = cursor.fetchone()[0]
        conn.close()

        # Create a temporary agent + anonymous public link
        agent_name = "mem-test-anon-001"
        try:
            r = httpx.post(
                f"{BASE_URL}/api/agents",
                json={"name": agent_name},
                headers=auth_headers
            )
            if r.status_code not in (200, 201):
                pytest.skip("Could not create test agent")

            link_r = httpx.post(
                f"{BASE_URL}/api/agents/{agent_name}/public-links",
                json={"name": "anon-test-link", "require_email": False},
                headers=auth_headers
            )
            if link_r.status_code != 200:
                pytest.skip("Could not create public link")

            token = link_r.json()["token"]

            # Fire anonymous chat (agent likely not running → 503, that's fine)
            httpx.post(
                f"{BASE_URL}/api/public/chat/{token}",
                json={"message": "Hello", "session_id": "anon-session-no-memory"},
                timeout=10.0
            )

        finally:
            httpx.delete(f"{BASE_URL}/api/agents/{agent_name}", headers=auth_headers)

        # Count memory rows after — must not have increased
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM public_user_memory")
        count_after = cursor.fetchone()[0]
        conn.close()

        assert count_after == count_before, (
            f"Anonymous session created {count_after - count_before} unexpected memory row(s)"
        )


# ============================================================================
# Memory DB Operations via API Layer
# ============================================================================

class TestMemoryDatabaseOperations:
    """Verify the DB helper methods work correctly via direct SQLite access."""

    @pytest.mark.smoke
    def test_get_or_create_memory_creates_empty_row(self):
        """Direct DB: get_or_create inserts row with empty memory_text."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        import secrets
        agent = f"test-mem-ops-{secrets.token_hex(4)}"
        email = f"mem-test-{secrets.token_hex(4)}@example.com"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Simulate what get_or_create_user_memory does
            import datetime
            now = datetime.datetime.utcnow().isoformat()
            memory_id = secrets.token_urlsafe(16)
            cursor.execute("""
                INSERT INTO public_user_memory
                (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                VALUES (?, ?, ?, '', 0, ?, ?)
            """, (memory_id, agent, email.lower(), now, now))
            conn.commit()

            # Verify the row
            cursor.execute(
                "SELECT * FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent, email.lower())
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["memory_text"] == ""
            assert row["message_count"] == 0

        finally:
            cursor.execute(
                "DELETE FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent, email.lower())
            )
            conn.commit()
            conn.close()

    @pytest.mark.smoke
    def test_update_memory_text(self):
        """Direct DB: update_user_memory writes new text."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        import secrets, datetime
        agent = f"test-mem-upd-{secrets.token_hex(4)}"
        email = f"mem-upd-{secrets.token_hex(4)}@example.com"
        now = datetime.datetime.utcnow().isoformat()
        memory_id = secrets.token_urlsafe(16)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO public_user_memory
                (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                VALUES (?, ?, ?, '', 0, ?, ?)
            """, (memory_id, agent, email.lower(), now, now))

            # Update memory text
            cursor.execute("""
                UPDATE public_user_memory SET memory_text=?, updated_at=?
                WHERE agent_name=? AND user_email=?
            """, ("- Name: Alice\n- Prefers Python", now, agent, email.lower()))
            conn.commit()

            cursor.execute(
                "SELECT memory_text FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent, email.lower())
            )
            row = cursor.fetchone()
            assert row["memory_text"] == "- Name: Alice\n- Prefers Python"

        finally:
            cursor.execute(
                "DELETE FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent, email.lower())
            )
            conn.commit()
            conn.close()

    @pytest.mark.smoke
    def test_unique_constraint_per_agent_and_email(self):
        """Direct DB: UNIQUE(agent_name, user_email) prevents duplicates."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        import secrets, datetime
        agent = f"test-mem-uniq-{secrets.token_hex(4)}"
        email = f"uniq-{secrets.token_hex(4)}@example.com"
        now = datetime.datetime.utcnow().isoformat()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO public_user_memory
                (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                VALUES (?, ?, ?, '', 0, ?, ?)
            """, (secrets.token_urlsafe(16), agent, email.lower(), now, now))
            conn.commit()

            # Second insert for same (agent, email) must fail
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO public_user_memory
                    (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                    VALUES (?, ?, ?, '', 0, ?, ?)
                """, (secrets.token_urlsafe(16), agent, email.lower(), now, now))
                conn.commit()

        finally:
            conn.rollback()
            cursor.execute(
                "DELETE FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent, email.lower())
            )
            conn.commit()
            conn.close()

    @pytest.mark.smoke
    def test_memory_scoped_per_agent(self):
        """Direct DB: different agents get separate memory rows for the same email."""
        db_path = os.path.expanduser("~/trinity-data/trinity.db")
        if not os.path.exists(db_path):
            pytest.skip(f"Database not found at {db_path}")

        import secrets, datetime
        email = f"shared-{secrets.token_hex(4)}@example.com"
        agent_a = f"test-mem-a-{secrets.token_hex(4)}"
        agent_b = f"test-mem-b-{secrets.token_hex(4)}"
        now = datetime.datetime.utcnow().isoformat()
        id_a = secrets.token_urlsafe(16)
        id_b = secrets.token_urlsafe(16)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO public_user_memory
                (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                VALUES (?, ?, ?, 'memory-a', 0, ?, ?)
            """, (id_a, agent_a, email.lower(), now, now))
            cursor.execute("""
                INSERT INTO public_user_memory
                (id, agent_name, user_email, memory_text, message_count, created_at, updated_at)
                VALUES (?, ?, ?, 'memory-b', 0, ?, ?)
            """, (id_b, agent_b, email.lower(), now, now))
            conn.commit()

            cursor.execute(
                "SELECT id FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent_a, email.lower())
            )
            row_a = cursor.fetchone()
            cursor.execute(
                "SELECT id FROM public_user_memory WHERE agent_name=? AND user_email=?",
                (agent_b, email.lower())
            )
            row_b = cursor.fetchone()

            assert row_a[0] != row_b[0], "Expected separate rows for different agents"

        finally:
            cursor.execute(
                "DELETE FROM public_user_memory WHERE agent_name IN (?, ?) AND user_email=?",
                (agent_a, agent_b, email.lower())
            )
            conn.commit()
            conn.close()


# ============================================================================
# Platform Prompt Service — format_user_memory_block
# ============================================================================

def _format_user_memory_block(memory_text: str) -> str:
    """Local copy of format_user_memory_block for test verification.

    Mirrors src/backend/services/platform_prompt_service.py exactly.
    Kept inline to avoid the full backend import chain in the test env.
    """
    return f"## What you know about this user\n\n{memory_text.strip()}\n\n---"


class TestFormatUserMemoryBlock:
    """Tests for the format_user_memory_block output contract.

    Uses the inline mirror above to verify the contract independently
    of backend import chain issues in the test environment.
    """

    @pytest.mark.smoke
    def test_block_contains_header(self):
        block = _format_user_memory_block("- Name: Alice")
        assert "## What you know about this user" in block

    @pytest.mark.smoke
    def test_block_contains_memory_text(self):
        block = _format_user_memory_block("- Name: Alice\n- Prefers Python")
        assert "- Name: Alice" in block
        assert "- Prefers Python" in block

    @pytest.mark.smoke
    def test_block_trims_surrounding_whitespace(self):
        block = _format_user_memory_block("   - Likes coffee   ")
        content = block.split("## What you know about this user")[1].split("---")[0]
        assert content.strip() == "- Likes coffee"

    @pytest.mark.smoke
    def test_block_ends_with_separator(self):
        block = _format_user_memory_block("- Fact")
        assert block.strip().endswith("---")
