"""
Agent ownership and sharing database operations.

Handles agent ownership registration, access control, and sharing.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

from .connection import get_db_connection
from db_models import AgentShare


class AgentOperations:
    """Agent ownership and sharing database operations."""

    def __init__(self, user_ops):
        """Initialize with reference to user operations for lookups."""
        self._user_ops = user_ops

    @staticmethod
    def _row_to_agent_share(row) -> AgentShare:
        """Convert an agent_sharing row to an AgentShare model."""
        return AgentShare(
            id=row["id"],
            agent_name=row["agent_name"],
            shared_with_email=row["shared_with_email"],
            shared_by_id=row["shared_by_id"],
            shared_by_email=row["shared_by_email"] or "unknown",
            created_at=datetime.fromisoformat(row["created_at"])
        )

    # =========================================================================
    # Agent Ownership Management
    # =========================================================================

    def register_agent_owner(self, agent_name: str, owner_username: str) -> bool:
        """Register the owner of an agent."""
        user = self._user_ops.get_user_by_username(owner_username)
        if not user:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_ownership (agent_name, owner_id, created_at)
                    VALUES (?, ?, ?)
                """, (agent_name, user["id"], datetime.utcnow().isoformat()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Agent already registered
                return False

    def get_agent_owner(self, agent_name: str) -> Optional[Dict]:
        """Get the owner of an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ao.id, ao.agent_name, ao.owner_id, u.username as owner_username, ao.created_at
                FROM agent_ownership ao
                JOIN users u ON ao.owner_id = u.id
                WHERE ao.agent_name = ?
            """, (agent_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_agents_by_owner(self, owner_username: str) -> List[str]:
        """Get all agent names owned by a user."""
        user = self._user_ops.get_user_by_username(owner_username)
        if not user:
            return []

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM agent_ownership WHERE owner_id = ?
            """, (user["id"],))
            return [row["agent_name"] for row in cursor.fetchall()]

    def delete_agent_ownership(self, agent_name: str) -> bool:
        """Remove agent ownership record and all sharing records (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete sharing records first (cascade)
            cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
            # Delete ownership record
            cursor.execute("DELETE FROM agent_ownership WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return cursor.rowcount > 0

    def can_user_access_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can access an agent (owner, shared, or admin)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        # Admins can access all agents
        if user["role"] == "admin":
            return True

        # Check if user is the owner
        owner = self.get_agent_owner(agent_name)
        if owner and owner["owner_username"] == username:
            return True

        # Check if agent is shared with user
        if self.is_agent_shared_with_user(agent_name, username):
            return True

        return False

    def can_user_delete_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can delete an agent (owner or admin)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        # Admins can delete any agent
        if user["role"] == "admin":
            return True

        # Owners can delete their own agents
        owner = self.get_agent_owner(agent_name)
        if owner and owner["owner_username"] == username:
            return True

        return False

    # =========================================================================
    # Agent Sharing Management
    # =========================================================================

    def share_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> Optional[AgentShare]:
        """
        Share an agent with another user by email.
        - Validates owner has permission to share
        - Creates sharing record with email (user doesn't need to exist yet)
        - Returns share details or None if failed
        """
        # Get owner and validate permission
        owner = self._user_ops.get_user_by_username(owner_username)
        if not owner:
            return None

        # Check if user can share (owner or admin)
        if not self.can_user_share_agent(owner_username, agent_name):
            return None

        # Prevent self-sharing (check if owner's email matches target email)
        owner_email = owner.get("email") or ""
        if owner_email and owner_email.lower() == share_with_email.lower():
            return None

        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (agent_name, share_with_email.lower(), owner["id"], now))
                conn.commit()
                share_id = cursor.lastrowid

                return AgentShare(
                    id=share_id,
                    agent_name=agent_name,
                    shared_with_email=share_with_email.lower(),
                    shared_by_id=owner["id"],
                    shared_by_email=owner.get("email") or owner.get("username") or "unknown",
                    created_at=datetime.fromisoformat(now)
                )
            except sqlite3.IntegrityError:
                # Already shared with this email
                return None

    def unshare_agent(self, agent_name: str, owner_username: str, share_with_email: str) -> bool:
        """Remove sharing access for an email."""
        # Validate permission
        if not self.can_user_share_agent(owner_username, agent_name):
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_sharing
                WHERE agent_name = ? AND shared_with_email = ?
            """, (agent_name, share_with_email.lower()))
            conn.commit()
            return cursor.rowcount > 0

    def get_agent_shares(self, agent_name: str) -> List[AgentShare]:
        """Get all emails an agent is shared with."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.agent_name, s.shared_with_email, s.shared_by_id, s.created_at,
                       COALESCE(sb.email, sb.username) as shared_by_email
                FROM agent_sharing s
                JOIN users sb ON s.shared_by_id = sb.id
                WHERE s.agent_name = ?
                ORDER BY s.created_at DESC
            """, (agent_name,))
            return [self._row_to_agent_share(row) for row in cursor.fetchall()]

    def get_shared_agents(self, username: str) -> List[str]:
        """Get all agent names shared with a user (by their email)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return []

        user_email = user.get("email")
        if not user_email:
            return []

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name FROM agent_sharing WHERE shared_with_email = ?
            """, (user_email.lower(),))
            return [row["agent_name"] for row in cursor.fetchall()]

    def is_agent_shared_with_user(self, agent_name: str, username: str) -> bool:
        """Check if an agent is shared with a specific user (by their email)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        user_email = user.get("email")
        if not user_email:
            return False

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM agent_sharing
                WHERE agent_name = ? AND shared_with_email = ?
            """, (agent_name, user_email.lower()))
            return cursor.fetchone() is not None

    def can_user_share_agent(self, username: str, agent_name: str) -> bool:
        """Check if a user can share an agent (only owner or admin)."""
        user = self._user_ops.get_user_by_username(username)
        if not user:
            return False

        if user["role"] == "admin":
            return True

        owner = self.get_agent_owner(agent_name)
        return owner and owner["owner_username"] == username

    def delete_agent_shares(self, agent_name: str) -> int:
        """Delete all sharing records for an agent (when agent is deleted)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_sharing WHERE agent_name = ?", (agent_name,))
            conn.commit()
            return cursor.rowcount
