"""
SQLite persistence layer for Trinity platform.

This module provides the main DatabaseManager class and database initialization.
The actual database operations are organized in submodules under db/:
- db/users.py: User management
- db/agents.py: Agent ownership and sharing
- db/mcp_keys.py: MCP API key management
- db/schedules.py: Schedule and execution management
- db/chat.py: Chat session and message persistence
- db/activities.py: Activity stream logging

For backward compatibility, all models and the global `db` instance are
re-exported from this module.

Handles persistent storage for:
- Users (Auth0 and local users)
- Agent ownership (who created which agent)
- MCP API keys (with usage tracking)

Redis is still used for:
- Credential secrets (fast access)
- OAuth state (ephemeral, TTL-based)
- Sessions/cache
"""

import os
from datetime import datetime
from pathlib import Path

# Re-export models for backward compatibility
from db_models import (
    UserCreate,
    User,
    AgentOwnership,
    AgentShare,
    AgentShareRequest,
    McpApiKeyCreate,
    McpApiKey,
    McpApiKeyWithSecret,
    McpAgentKeyCreate,
    ScheduleCreate,
    Schedule,
    ScheduleExecution,
    AgentGitConfig,
    GitSyncResult,
    ChatSession,
    ChatMessage,
    AgentPermission,
    AgentPermissionInfo,
    SharedFolderConfig,
    SharedFolderConfigUpdate,
    SharedFolderMount,
    SharedFolderInfo,
    SystemSetting,
    SystemSettingUpdate,
    # Public Agent Links (Phase 12.2)
    PublicLinkCreate,
    PublicLink,
    PublicLinkUpdate,
    PublicLinkWithUrl,
    PublicLinkInfo,
    VerificationRequest,
    VerificationConfirm,
    VerificationResponse,
    PublicChatRequest,
    PublicChatResponse,
    # Public Chat Persistence (Phase 12.2.5)
    PublicChatSession,
    PublicChatMessage,
    # Email Authentication (Phase 12.4)
    EmailWhitelistEntry,
    EmailWhitelistAdd,
    EmailLoginRequest,
    EmailLoginVerify,
    EmailLoginResponse,
    # Agent Notifications (NOTIF-001)
    NotificationCreate,
    Notification,
    NotificationList,
    NotificationAcknowledge,
)

# Re-export connection utilities
from db.connection import get_db_connection, DB_PATH

# Import operation classes
from db.users import UserOperations
from db.agents import AgentOperations
from db.mcp_keys import McpKeyOperations
from db.schedules import ScheduleOperations
from db.chat import ChatOperations
from db.activities import ActivityOperations
from db.permissions import PermissionOperations
from db.shared_folders import SharedFolderOperations
from db.settings import SettingsOperations
from db.public_links import PublicLinkOperations
from db.email_auth import EmailAuthOperations
from db.skills import SkillsOperations
from db.public_chat import PublicChatOperations
from db.tags import TagOperations
from db.system_views import SystemViewOperations
from db.notifications import NotificationOperations


def _migrate_agent_sharing_table(cursor, conn):
    """Migrate agent_sharing table from user_id based to email based."""
    # Check if old schema exists (with shared_with_id column)
    cursor.execute("PRAGMA table_info(agent_sharing)")
    columns = {row[1] for row in cursor.fetchall()}

    if "shared_with_id" in columns and "shared_with_email" not in columns:
        print("Migrating agent_sharing table to email-based schema...")

        # Migrate existing data: join with users to get emails
        cursor.execute("""
            SELECT s.id, s.agent_name, u.email, s.shared_by_id, s.created_at
            FROM agent_sharing s
            JOIN users u ON s.shared_with_id = u.id
        """)
        existing_shares = cursor.fetchall()

        # Drop old table
        cursor.execute("DROP TABLE agent_sharing")

        # Create new table with email
        cursor.execute("""
            CREATE TABLE agent_sharing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                shared_with_email TEXT NOT NULL,
                shared_by_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (shared_by_id) REFERENCES users(id),
                UNIQUE(agent_name, shared_with_email)
            )
        """)

        # Re-insert migrated data
        for share in existing_shares:
            if share[2]:  # email exists
                cursor.execute("""
                    INSERT INTO agent_sharing (agent_name, shared_with_email, shared_by_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (share[1], share[2].lower(), share[3], share[4]))

        conn.commit()
        print(f"Migrated {len(existing_shares)} sharing records to email-based schema")


def _migrate_schedule_executions_observability(cursor, conn):
    """Add observability columns to schedule_executions table."""
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = [
        ("context_used", "INTEGER"),
        ("context_max", "INTEGER"),
        ("cost", "REAL"),
        ("tool_calls", "TEXT"),
        ("execution_log", "TEXT")  # Full Claude Code execution transcript (JSON)
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to schedule_executions...")
            cursor.execute(f"ALTER TABLE schedule_executions ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_mcp_api_keys_agent_scope(cursor, conn):
    """Add agent_name and scope columns to mcp_api_keys table for agent-to-agent collaboration."""
    cursor.execute("PRAGMA table_info(mcp_api_keys)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = [
        ("agent_name", "TEXT"),  # Which agent owns this key (NULL for user keys)
        ("scope", "TEXT DEFAULT 'user'")  # "user" or "agent"
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to mcp_api_keys for agent collaboration...")
            cursor.execute(f"ALTER TABLE mcp_api_keys ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_system_flag(cursor, conn):
    """Add is_system column to agent_ownership table for system agent protection."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "is_system" not in columns:
        print("Adding is_system column to agent_ownership for system agent protection...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN is_system INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_platform_key(cursor, conn):
    """Add use_platform_api_key column to agent_ownership table for per-agent API key control."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "use_platform_api_key" not in columns:
        print("Adding use_platform_api_key column to agent_ownership for per-agent API key control...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN use_platform_api_key INTEGER DEFAULT 1")
        conn.commit()


def _migrate_agent_git_config_source_branch(cursor, conn):
    """Add source_branch and source_mode columns to agent_git_config for GitHub source tracking."""
    cursor.execute("PRAGMA table_info(agent_git_config)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("source_branch", "TEXT DEFAULT 'main'"),  # Branch to pull from
        ("source_mode", "INTEGER DEFAULT 0")  # 1 = track source branch directly, 0 = legacy working branch
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_git_config for GitHub source tracking...")
            cursor.execute(f"ALTER TABLE agent_git_config ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_autonomy(cursor, conn):
    """Add autonomy_enabled column to agent_ownership table for autonomous scheduling control."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "autonomy_enabled" not in columns:
        print("Adding autonomy_enabled column to agent_ownership for autonomous scheduling...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN autonomy_enabled INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_resource_limits(cursor, conn):
    """Add memory_limit and cpu_limit columns to agent_ownership table for per-agent resource configuration."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("memory_limit", "TEXT"),  # e.g., "4g", "8g", "16g"
        ("cpu_limit", "TEXT")  # e.g., "2", "4", "8"
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_ownership for resource configuration...")
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_ownership_full_capabilities(cursor, conn):
    """Add full_capabilities column to agent_ownership table for container security settings."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    if "full_capabilities" not in columns:
        print("Adding full_capabilities column to agent_ownership for container security settings...")
        cursor.execute("ALTER TABLE agent_ownership ADD COLUMN full_capabilities INTEGER DEFAULT 0")
        conn.commit()


def _migrate_agent_ownership_read_only_mode(cursor, conn):
    """Add read_only_mode and read_only_config columns to agent_ownership table for code protection."""
    cursor.execute("PRAGMA table_info(agent_ownership)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("read_only_mode", "INTEGER DEFAULT 0"),  # 0 = disabled, 1 = enabled
        ("read_only_config", "TEXT")  # JSON config for blocked/allowed patterns
    ]

    for col_name, col_def in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_ownership for read-only mode...")
            cursor.execute(f"ALTER TABLE agent_ownership ADD COLUMN {col_name} {col_def}")

    conn.commit()


def _migrate_agent_schedules_execution_config(cursor, conn):
    """Add timeout_seconds and allowed_tools columns to agent_schedules table for per-schedule execution config."""
    cursor.execute("PRAGMA table_info(agent_schedules)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("timeout_seconds", "INTEGER DEFAULT 900"),  # Default 15 minutes
        ("allowed_tools", "TEXT")  # JSON array of allowed tools, NULL = all tools
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to agent_schedules for execution configuration...")
            cursor.execute(f"ALTER TABLE agent_schedules ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_notifications_table(cursor, conn):
    """Create agent_notifications table if it doesn't exist (NOTIF-001)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_notifications (
            id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            priority TEXT DEFAULT 'normal',
            category TEXT,
            metadata TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            acknowledged_by TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_agent ON agent_notifications(agent_name, created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON agent_notifications(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_priority ON agent_notifications(priority)")
    conn.commit()


def _migrate_execution_origin_tracking(cursor, conn):
    """Add execution origin tracking columns to schedule_executions table (AUDIT-001).

    Tracks WHO triggered each execution:
    - source_user_id: User who triggered (for manual and MCP user triggers)
    - source_user_email: User email (denormalized for queries)
    - source_agent_name: Calling agent (for agent-to-agent collaboration)
    - source_mcp_key_id: MCP API key ID used (for MCP calls)
    - source_mcp_key_name: MCP API key name (denormalized)
    """
    cursor.execute("PRAGMA table_info(schedule_executions)")
    columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("source_user_id", "INTEGER"),
        ("source_user_email", "TEXT"),
        ("source_agent_name", "TEXT"),
        ("source_mcp_key_id", "TEXT"),
        ("source_mcp_key_name", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to schedule_executions for origin tracking...")
            cursor.execute(f"ALTER TABLE schedule_executions ADD COLUMN {col_name} {col_type}")

    conn.commit()


def _migrate_agent_skills_table(cursor, conn):
    """Migrate agent_skills table if it has wrong schema (skill_id instead of skill_name)."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_skills'")
    if not cursor.fetchone():
        return  # Table doesn't exist yet, will be created fresh

    cursor.execute("PRAGMA table_info(agent_skills)")
    columns = {row[1] for row in cursor.fetchall()}

    # Check if table has old schema (skill_id instead of skill_name)
    if "skill_id" in columns and "skill_name" not in columns:
        print("Migrating agent_skills table: renaming skill_id to skill_name...")

        # Get existing data
        cursor.execute("SELECT id, agent_name, skill_id, assigned_by, assigned_at FROM agent_skills")
        existing_data = cursor.fetchall()

        # Drop old table
        cursor.execute("DROP TABLE agent_skills")

        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE agent_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                UNIQUE(agent_name, skill_name)
            )
        """)

        # Reinsert data
        for row in existing_data:
            cursor.execute("""
                INSERT INTO agent_skills (agent_name, skill_name, assigned_by, assigned_at)
                VALUES (?, ?, ?, ?)
            """, (row[1], row[2], row[3], row[4]))

        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_agent ON agent_skills(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_skill ON agent_skills(skill_name)")

        conn.commit()
        print(f"Migrated {len(existing_data)} agent_skills records")


def init_database():
    """Initialize the SQLite database with all required tables."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Run migrations first (if tables exist)
        try:
            _migrate_agent_sharing_table(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_sharing): {e}")

        try:
            _migrate_schedule_executions_observability(cursor, conn)
        except Exception as e:
            print(f"Migration check (schedule_executions): {e}")

        try:
            _migrate_mcp_api_keys_agent_scope(cursor, conn)
        except Exception as e:
            print(f"Migration check (mcp_api_keys agent scope): {e}")

        try:
            _migrate_agent_ownership_system_flag(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_ownership is_system): {e}")

        try:
            _migrate_agent_ownership_platform_key(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_ownership use_platform_api_key): {e}")

        try:
            _migrate_agent_git_config_source_branch(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_git_config source_branch): {e}")

        try:
            _migrate_agent_ownership_autonomy(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_ownership autonomy_enabled): {e}")

        try:
            _migrate_agent_ownership_resource_limits(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_ownership resource_limits): {e}")

        try:
            _migrate_agent_skills_table(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_skills): {e}")

        try:
            _migrate_agent_ownership_read_only_mode(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_ownership read_only_mode): {e}")

        try:
            _migrate_agent_schedules_execution_config(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_schedules execution_config): {e}")

        try:
            _migrate_agent_notifications_table(cursor, conn)
        except Exception as e:
            print(f"Migration check (agent_notifications): {e}")

        try:
            _migrate_execution_origin_tracking(cursor, conn)
        except Exception as e:
            print(f"Migration check (execution_origin_tracking): {e}")

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                auth0_sub TEXT UNIQUE,
                name TEXT,
                picture TEXT,
                email TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        # Agent ownership table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_ownership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                is_system INTEGER DEFAULT 0,
                use_platform_api_key INTEGER DEFAULT 1,
                autonomy_enabled INTEGER DEFAULT 0,
                memory_limit TEXT,
                cpu_limit TEXT,
                read_only_mode INTEGER DEFAULT 0,
                read_only_config TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)

        # Agent sharing table - stores email directly (user may not exist yet)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_sharing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                shared_with_email TEXT NOT NULL,
                shared_by_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (shared_by_id) REFERENCES users(id),
                UNIQUE(agent_name, shared_with_email)
            )
        """)

        # MCP API keys table (with agent collaboration support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcp_api_keys (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                key_prefix TEXT NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                usage_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                user_id INTEGER NOT NULL,
                agent_name TEXT,
                scope TEXT DEFAULT 'user',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Agent schedules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_schedules (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                name TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                message TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                timezone TEXT DEFAULT 'UTC',
                description TEXT,
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                timeout_seconds INTEGER DEFAULT 900,
                allowed_tools TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)

        # Schedule executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule_executions (
                id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                message TEXT NOT NULL,
                response TEXT,
                error TEXT,
                triggered_by TEXT NOT NULL,
                context_used INTEGER,
                context_max INTEGER,
                cost REAL,
                tool_calls TEXT,
                execution_log TEXT,
                FOREIGN KEY (schedule_id) REFERENCES agent_schedules(id)
            )
        """)

        # Agent git configuration table (Phase 7: GitHub Bidirectional Sync)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_git_config (
                id TEXT PRIMARY KEY,
                agent_name TEXT UNIQUE NOT NULL,
                github_repo TEXT NOT NULL,
                working_branch TEXT NOT NULL,
                instance_id TEXT NOT NULL,
                source_branch TEXT DEFAULT 'main',
                source_mode INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_sync_at TEXT,
                last_commit_sha TEXT,
                sync_enabled INTEGER DEFAULT 1,
                sync_paths TEXT,
                FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name)
            )
        """)

        # Chat sessions table (persistent chat tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_message_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                total_context_used INTEGER DEFAULT 0,
                total_context_max INTEGER DEFAULT 200000,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Chat messages table (all user and assistant messages)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cost REAL,
                context_used INTEGER,
                context_max INTEGER,
                tool_calls TEXT,
                execution_time_ms INTEGER,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Agent activities table (unified activity stream - Phase 9.7)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_activities (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                activity_state TEXT NOT NULL,
                parent_activity_id TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                user_id INTEGER,
                triggered_by TEXT NOT NULL,
                related_chat_message_id TEXT,
                related_execution_id TEXT,
                details TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (parent_activity_id) REFERENCES agent_activities(id),
                FOREIGN KEY (related_chat_message_id) REFERENCES chat_messages(id),
                FOREIGN KEY (related_execution_id) REFERENCES schedule_executions(id)
            )
        """)

        # Agent permissions table (Phase 9.10: Agent-to-Agent Permissions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_agent TEXT NOT NULL,
                target_agent TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                UNIQUE(source_agent, target_agent)
            )
        """)

        # Agent shared folder configuration table (Phase 9.11: Agent Shared Folders)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_shared_folder_config (
                agent_name TEXT PRIMARY KEY,
                expose_enabled INTEGER DEFAULT 0,
                consume_enabled INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # System settings table (system-wide configuration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Public agent links table (Phase 12.2: Public Agent Links)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_public_links (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                enabled INTEGER DEFAULT 1,
                name TEXT,
                require_email INTEGER DEFAULT 0,
                FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # Public link email verifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_link_verifications (
                id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                session_token TEXT,
                session_expires_at TEXT,
                FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE
            )
        """)

        # Public link usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_link_usage (
                id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                email TEXT,
                ip_address TEXT,
                message_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE
            )
        """)

        # Public chat sessions table (Phase 12.2.5: Public Chat Persistence)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_chat_sessions (
                id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                session_identifier TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_message_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                FOREIGN KEY (link_id) REFERENCES agent_public_links(id) ON DELETE CASCADE,
                UNIQUE(link_id, session_identifier)
            )
        """)

        # Public chat messages table (Phase 12.2.5: Public Chat Persistence)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cost REAL,
                FOREIGN KEY (session_id) REFERENCES public_chat_sessions(id) ON DELETE CASCADE
            )
        """)

        # Email whitelist table (Phase 12.4: Email-Based Authentication)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                added_by TEXT NOT NULL,
                added_at TEXT NOT NULL,
                source TEXT NOT NULL,
                FOREIGN KEY (added_by) REFERENCES users(id)
            )
        """)

        # Email login codes table (Phase 12.4: Email-Based Authentication)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_login_codes (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                used_at TEXT
            )
        """)

        # Agent skills table (Skills Management System)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                UNIQUE(agent_name, skill_name)
            )
        """)

        # Agent tags table (ORG-001: Agent Systems & Tags)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_tags (
                agent_name TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_name, tag),
                FOREIGN KEY (agent_name) REFERENCES agent_ownership(agent_name) ON DELETE CASCADE
            )
        """)

        # System views table (ORG-001 Phase 2: Agent Systems & Tags)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_views (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                color TEXT,
                filter_tags TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                is_shared INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_auth0_sub ON users(auth0_sub)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_ownership_owner ON agent_ownership(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_ownership_name ON agent_ownership(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sharing_agent ON agent_sharing(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sharing_email ON agent_sharing(shared_with_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_keys_user ON mcp_api_keys(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_keys_hash ON mcp_api_keys(key_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_keys_agent ON mcp_api_keys(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_agent ON agent_schedules(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_owner ON agent_schedules(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON agent_schedules(enabled)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_schedule ON schedule_executions(schedule_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_agent ON schedule_executions(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_status ON schedule_executions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_git_config_agent ON agent_git_config(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_git_config_repo ON agent_git_config(github_repo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent ON chat_sessions(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_agent ON chat_messages(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_agent ON agent_activities(agent_name, created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_type ON agent_activities(activity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_state ON agent_activities(activity_state)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_user ON agent_activities(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_parent ON agent_activities(parent_activity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_chat_msg ON agent_activities(related_chat_message_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_execution ON agent_activities(related_execution_id)")
        # Agent permissions indexes (Phase 9.10)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_permissions_source ON agent_permissions(source_agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_permissions_target ON agent_permissions(target_agent)")
        # Shared folder indexes (Phase 9.11)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_folders_expose ON agent_shared_folder_config(expose_enabled)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shared_folders_consume ON agent_shared_folder_config(consume_enabled)")
        # Public links indexes (Phase 12.2)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_links_token ON agent_public_links(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_links_agent ON agent_public_links(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_link ON public_link_verifications(link_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_email ON public_link_verifications(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_code ON public_link_verifications(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_link ON public_link_usage(link_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_ip ON public_link_usage(ip_address)")
        # Email auth indexes (Phase 12.4)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_whitelist_email ON email_whitelist(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_login_codes_email ON email_login_codes(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_login_codes_code ON email_login_codes(code)")
        # Agent skills indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_agent ON agent_skills(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_skills_skill ON agent_skills(skill_name)")
        # Agent tags indexes (ORG-001)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_tags_tag ON agent_tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_tags_agent ON agent_tags(agent_name)")
        # Public chat session indexes (Phase 12.2.5)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_link ON public_chat_sessions(link_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_identifier ON public_chat_sessions(session_identifier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_chat_messages_session ON public_chat_messages(session_id)")
        # System views indexes (ORG-001 Phase 2)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_views_owner ON system_views(owner_id)")

        conn.commit()

        # Create default admin user if not exists
        _ensure_admin_user(cursor, conn)


def _ensure_admin_user(cursor, conn):
    """Ensure the admin user exists with properly hashed password."""
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    admin_username = os.getenv("ADMIN_USERNAME", "admin")

    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (admin_username,))
    existing = cursor.fetchone()

    if existing is None:
        # Create admin user
        if not admin_password:
            print("WARNING: ADMIN_PASSWORD not set - skipping admin user creation")
            print("         Set ADMIN_PASSWORD environment variable to create admin user")
            return

        now = datetime.utcnow().isoformat()
        # Hash password using bcrypt
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash(admin_password)

        cursor.execute("""
            INSERT INTO users (username, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (admin_username, hashed, "admin", now, now))
        conn.commit()
        print(f"Created admin user '{admin_username}' with hashed password")
    else:
        # Check if existing password needs update (migration or change)
        existing_hash = existing[1]
        should_update = False
        
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        if existing_hash and not existing_hash.startswith("$2"):
            # Password is likely plaintext (bcrypt hashes start with $2)
            if admin_password and existing_hash == admin_password:
                should_update = True
                print(f"Migrating admin user '{admin_username}' password from plaintext to bcrypt")
        elif admin_password:
             # Check if environment password matches DB hash
            try:
                if not pwd_context.verify(admin_password, existing_hash):
                    should_update = True
                    print(f"Environment password changed - updating admin user '{admin_username}'")
            except Exception as e:
                print(f"Error verifying password hash: {e}")
                should_update = True

        if should_update and admin_password:
            hashed = pwd_context.hash(admin_password)
            cursor.execute("""
                UPDATE users SET password_hash = ?, updated_at = ?
                WHERE username = ?
            """, (hashed, datetime.utcnow().isoformat(), admin_username))
            conn.commit()


class DatabaseManager:
    """
    Manages SQLite database operations for Trinity platform.

    This class composes operations from specialized submodules:
    - User management: db/users.py
    - Agent ownership/sharing: db/agents.py
    - MCP API keys: db/mcp_keys.py
    - Schedules/executions: db/schedules.py
    - Chat sessions/messages: db/chat.py
    - Activity stream: db/activities.py

    All methods are delegated to the appropriate submodule while
    maintaining the same interface for backward compatibility.
    """

    def __init__(self):
        init_database()

        # Initialize operation handlers
        self._user_ops = UserOperations()
        self._agent_ops = AgentOperations(self._user_ops)
        self._mcp_key_ops = McpKeyOperations(self._user_ops)
        self._schedule_ops = ScheduleOperations(self._user_ops, self._agent_ops)
        self._chat_ops = ChatOperations()
        self._activity_ops = ActivityOperations()
        self._permission_ops = PermissionOperations(self._user_ops, self._agent_ops)
        self._shared_folder_ops = SharedFolderOperations(self._permission_ops)
        self._settings_ops = SettingsOperations()
        self._public_link_ops = PublicLinkOperations(self._user_ops, self._agent_ops)
        self._email_auth_ops = EmailAuthOperations(self._user_ops)
        self._skills_ops = SkillsOperations()
        self._public_chat_ops = PublicChatOperations()
        self._tag_ops = TagOperations()
        self._system_view_ops = SystemViewOperations()
        self._notification_ops = NotificationOperations()

    # =========================================================================
    # User Management (delegated to db/users.py)
    # =========================================================================

    def get_user_by_username(self, username: str):
        return self._user_ops.get_user_by_username(username)

    def get_user_by_auth0_sub(self, auth0_sub: str):
        return self._user_ops.get_user_by_auth0_sub(auth0_sub)

    def get_user_by_id(self, user_id: int):
        return self._user_ops.get_user_by_id(user_id)

    def get_user_by_email(self, email: str):
        return self._user_ops.get_user_by_email(email)

    def create_user(self, user_data: UserCreate):
        return self._user_ops.create_user(user_data)

    def update_user(self, username: str, updates: dict):
        return self._user_ops.update_user(username, updates)

    def update_last_login(self, username: str):
        return self._user_ops.update_last_login(username)

    def update_user_password(self, username: str, hashed_password: str):
        return self._user_ops.update_user_password(username, hashed_password)

    def get_or_create_auth0_user(self, auth0_sub: str, email: str, name: str = None, picture: str = None):
        return self._user_ops.get_or_create_auth0_user(auth0_sub, email, name, picture)

    def list_users(self):
        return self._user_ops.list_users()

    # =========================================================================
    # Agent Ownership Management (delegated to db/agents.py)
    # =========================================================================

    def register_agent_owner(self, agent_name: str, owner_username: str, is_system: bool = False):
        return self._agent_ops.register_agent_owner(agent_name, owner_username, is_system)

    def get_agent_owner(self, agent_name: str):
        return self._agent_ops.get_agent_owner(agent_name)

    def get_agents_by_owner(self, owner_username: str):
        return self._agent_ops.get_agents_by_owner(owner_username)

    def delete_agent_ownership(self, agent_name: str):
        return self._agent_ops.delete_agent_ownership(agent_name)

    def can_user_access_agent(self, username: str, agent_name: str):
        return self._agent_ops.can_user_access_agent(username, agent_name)

    def can_user_delete_agent(self, username: str, agent_name: str):
        return self._agent_ops.can_user_delete_agent(username, agent_name)

    def is_system_agent(self, agent_name: str):
        return self._agent_ops.is_system_agent(agent_name)

    # =========================================================================
    # Agent Sharing Management (delegated to db/agents.py)
    # =========================================================================

    def share_agent(self, agent_name: str, owner_username: str, share_with_email: str):
        return self._agent_ops.share_agent(agent_name, owner_username, share_with_email)

    def unshare_agent(self, agent_name: str, owner_username: str, share_with_email: str):
        return self._agent_ops.unshare_agent(agent_name, owner_username, share_with_email)

    def get_agent_shares(self, agent_name: str):
        return self._agent_ops.get_agent_shares(agent_name)

    def get_shared_agents(self, username: str):
        return self._agent_ops.get_shared_agents(username)

    def is_agent_shared_with_user(self, agent_name: str, username: str):
        return self._agent_ops.is_agent_shared_with_user(agent_name, username)

    def can_user_share_agent(self, username: str, agent_name: str):
        return self._agent_ops.can_user_share_agent(username, agent_name)

    def delete_agent_shares(self, agent_name: str):
        return self._agent_ops.delete_agent_shares(agent_name)

    # =========================================================================
    # Agent API Key Settings (delegated to db/agents.py)
    # =========================================================================

    def get_use_platform_api_key(self, agent_name: str):
        return self._agent_ops.get_use_platform_api_key(agent_name)

    def set_use_platform_api_key(self, agent_name: str, use_platform_key: bool):
        return self._agent_ops.set_use_platform_api_key(agent_name, use_platform_key)

    # =========================================================================
    # Agent Autonomy Mode (delegated to db/agents.py)
    # =========================================================================

    def get_autonomy_enabled(self, agent_name: str):
        return self._agent_ops.get_autonomy_enabled(agent_name)

    def set_autonomy_enabled(self, agent_name: str, enabled: bool):
        return self._agent_ops.set_autonomy_enabled(agent_name, enabled)

    def get_all_agents_autonomy_status(self):
        return self._agent_ops.get_all_agents_autonomy_status()

    # =========================================================================
    # Batch Metadata Query (N+1 Fix) - delegated to db/agents.py
    # =========================================================================

    def get_all_agent_metadata(self, user_email: str = None):
        return self._agent_ops.get_all_agent_metadata(user_email)

    def get_accessible_agent_names(self, user_email: str, is_admin: bool = False):
        """Get list of agent names the user can access (owned + shared, or all if admin)."""
        return self._agent_ops.get_accessible_agent_names(user_email, is_admin)

    # =========================================================================
    # Agent Resource Limits (delegated to db/agents.py)
    # =========================================================================

    def get_resource_limits(self, agent_name: str):
        return self._agent_ops.get_resource_limits(agent_name)

    def set_resource_limits(self, agent_name: str, memory: str = None, cpu: str = None):
        return self._agent_ops.set_resource_limits(agent_name, memory, cpu)

    # =========================================================================
    # Agent Read-Only Mode (delegated to db/agents.py)
    # =========================================================================

    def get_read_only_mode(self, agent_name: str):
        return self._agent_ops.get_read_only_mode(agent_name)

    def set_read_only_mode(self, agent_name: str, enabled: bool, config: dict = None):
        return self._agent_ops.set_read_only_mode(agent_name, enabled, config)

    # =========================================================================
    # MCP API Key Management (delegated to db/mcp_keys.py)
    # =========================================================================

    def create_mcp_api_key(self, username: str, key_data: McpApiKeyCreate):
        return self._mcp_key_ops.create_mcp_api_key(username, key_data)

    def create_agent_mcp_api_key(self, agent_name: str, owner_username: str, description: str = None):
        return self._mcp_key_ops.create_agent_mcp_api_key(agent_name, owner_username, description)

    def get_agent_mcp_api_key(self, agent_name: str):
        return self._mcp_key_ops.get_agent_mcp_api_key(agent_name)

    def delete_agent_mcp_api_key(self, agent_name: str):
        return self._mcp_key_ops.delete_agent_mcp_api_key(agent_name)

    def validate_mcp_api_key(self, api_key: str):
        return self._mcp_key_ops.validate_mcp_api_key(api_key)

    def get_mcp_api_key(self, key_id: str, username: str):
        return self._mcp_key_ops.get_mcp_api_key(key_id, username)

    def list_mcp_api_keys(self, username: str):
        return self._mcp_key_ops.list_mcp_api_keys(username)

    def list_all_mcp_api_keys(self):
        return self._mcp_key_ops.list_all_mcp_api_keys()

    def revoke_mcp_api_key(self, key_id: str, username: str):
        return self._mcp_key_ops.revoke_mcp_api_key(key_id, username)

    def delete_mcp_api_key(self, key_id: str, username: str):
        return self._mcp_key_ops.delete_mcp_api_key(key_id, username)

    # =========================================================================
    # Schedule Management (delegated to db/schedules.py)
    # =========================================================================

    def create_schedule(self, agent_name: str, username: str, schedule_data: ScheduleCreate):
        return self._schedule_ops.create_schedule(agent_name, username, schedule_data)

    def get_schedule(self, schedule_id: str):
        return self._schedule_ops.get_schedule(schedule_id)

    def list_agent_schedules(self, agent_name: str):
        return self._schedule_ops.list_agent_schedules(agent_name)

    def list_all_enabled_schedules(self):
        return self._schedule_ops.list_all_enabled_schedules()

    def list_all_disabled_schedules(self):
        return self._schedule_ops.list_all_disabled_schedules()

    def list_all_schedules(self):
        """List all schedules across all agents."""
        return self._schedule_ops.list_all_schedules()

    def update_schedule(self, schedule_id: str, username: str, updates: dict):
        return self._schedule_ops.update_schedule(schedule_id, username, updates)

    def delete_schedule(self, schedule_id: str, username: str):
        return self._schedule_ops.delete_schedule(schedule_id, username)

    def set_schedule_enabled(self, schedule_id: str, enabled: bool):
        return self._schedule_ops.set_schedule_enabled(schedule_id, enabled)

    def update_schedule_run_times(self, schedule_id: str, last_run_at=None, next_run_at=None):
        return self._schedule_ops.update_schedule_run_times(schedule_id, last_run_at, next_run_at)

    def delete_agent_schedules(self, agent_name: str):
        return self._schedule_ops.delete_agent_schedules(agent_name)

    # =========================================================================
    # Schedule Execution Management (delegated to db/schedules.py)
    # =========================================================================

    def create_task_execution(
        self,
        agent_name: str,
        message: str,
        triggered_by: str = "manual",
        source_user_id: int = None,
        source_user_email: str = None,
        source_agent_name: str = None,
        source_mcp_key_id: str = None,
        source_mcp_key_name: str = None,
    ):
        """Create an execution record for a manual/API-triggered task (no schedule)."""
        return self._schedule_ops.create_task_execution(
            agent_name, message, triggered_by,
            source_user_id=source_user_id,
            source_user_email=source_user_email,
            source_agent_name=source_agent_name,
            source_mcp_key_id=source_mcp_key_id,
            source_mcp_key_name=source_mcp_key_name,
        )

    def create_schedule_execution(
        self,
        schedule_id: str,
        agent_name: str,
        message: str,
        triggered_by: str = "schedule",
        source_user_id: int = None,
        source_user_email: str = None,
        source_agent_name: str = None,
        source_mcp_key_id: str = None,
        source_mcp_key_name: str = None,
    ):
        return self._schedule_ops.create_schedule_execution(
            schedule_id, agent_name, message, triggered_by,
            source_user_id=source_user_id,
            source_user_email=source_user_email,
            source_agent_name=source_agent_name,
            source_mcp_key_id=source_mcp_key_id,
            source_mcp_key_name=source_mcp_key_name,
        )

    def update_execution_status(self, execution_id: str, status: str, response: str = None, error: str = None,
                                context_used: int = None, context_max: int = None, cost: float = None, tool_calls: str = None, execution_log: str = None):
        return self._schedule_ops.update_execution_status(execution_id, status, response, error,
                                                          context_used, context_max, cost, tool_calls, execution_log)

    def get_schedule_executions(self, schedule_id: str, limit: int = 50):
        return self._schedule_ops.get_schedule_executions(schedule_id, limit)

    def get_agent_executions(self, agent_name: str, limit: int = 50):
        return self._schedule_ops.get_agent_executions(agent_name, limit)

    def get_execution(self, execution_id: str):
        return self._schedule_ops.get_execution(execution_id)

    def get_all_agents_execution_stats(self, hours: int = 24):
        """Get execution statistics for all agents."""
        return self._schedule_ops.get_all_agents_execution_stats(hours)

    # =========================================================================
    # Git Configuration Management (delegated to db/schedules.py)
    # =========================================================================

    def create_git_config(
        self,
        agent_name: str,
        github_repo: str,
        working_branch: str,
        instance_id: str,
        sync_paths=None,
        source_branch: str = "main",
        source_mode: bool = False
    ):
        return self._schedule_ops.create_git_config(
            agent_name, github_repo, working_branch, instance_id, sync_paths,
            source_branch=source_branch, source_mode=source_mode
        )

    def get_git_config(self, agent_name: str):
        return self._schedule_ops.get_git_config(agent_name)

    def update_git_sync(self, agent_name: str, commit_sha: str):
        return self._schedule_ops.update_git_sync(agent_name, commit_sha)

    def set_git_sync_enabled(self, agent_name: str, enabled: bool):
        return self._schedule_ops.set_git_sync_enabled(agent_name, enabled)

    def delete_git_config(self, agent_name: str):
        return self._schedule_ops.delete_git_config(agent_name)

    def list_git_enabled_agents(self):
        return self._schedule_ops.list_git_enabled_agents()

    # =========================================================================
    # Chat Session and Message Operations (delegated to db/chat.py)
    # =========================================================================

    def get_or_create_chat_session(self, agent_name: str, user_id: int, user_email: str):
        return self._chat_ops.get_or_create_chat_session(agent_name, user_id, user_email)

    def add_chat_message(self, session_id: str, agent_name: str, user_id: int, user_email: str,
                         role: str, content: str, cost: float = None, context_used: int = None,
                         context_max: int = None, tool_calls: str = None, execution_time_ms: int = None):
        return self._chat_ops.add_chat_message(session_id, agent_name, user_id, user_email,
                                               role, content, cost, context_used, context_max,
                                               tool_calls, execution_time_ms)

    def get_chat_session(self, session_id: str):
        return self._chat_ops.get_chat_session(session_id)

    def get_chat_messages(self, session_id: str, limit: int = 100):
        return self._chat_ops.get_chat_messages(session_id, limit)

    def get_agent_chat_history(self, agent_name: str, user_id: int = None, limit: int = 100):
        return self._chat_ops.get_agent_chat_history(agent_name, user_id, limit)

    def get_agent_chat_sessions(self, agent_name: str, user_id: int = None, status: str = None):
        return self._chat_ops.get_agent_chat_sessions(agent_name, user_id, status)

    def close_chat_session(self, session_id: str):
        return self._chat_ops.close_chat_session(session_id)

    def create_new_chat_session(self, agent_name: str, user_id: int, user_email: str):
        return self._chat_ops.create_new_chat_session(agent_name, user_id, user_email)

    def delete_chat_session(self, session_id: str):
        return self._chat_ops.delete_chat_session(session_id)

    # =========================================================================
    # Activity Stream Methods (delegated to db/activities.py)
    # =========================================================================

    def create_activity(self, activity):
        return self._activity_ops.create_activity(activity)

    def complete_activity(self, activity_id: str, status: str = "completed", details: dict = None, error: str = None):
        return self._activity_ops.complete_activity(activity_id, status, details, error)

    def get_activity(self, activity_id: str):
        return self._activity_ops.get_activity(activity_id)

    def get_agent_activities(self, agent_name: str, activity_type: str = None, activity_state: str = None, limit: int = 100):
        return self._activity_ops.get_agent_activities(agent_name, activity_type, activity_state, limit)

    def get_activities_in_range(self, start_time: str = None, end_time: str = None, activity_types: list = None, limit: int = 100):
        return self._activity_ops.get_activities_in_range(start_time, end_time, activity_types, limit)

    def get_current_activities(self, agent_name: str):
        return self._activity_ops.get_current_activities(agent_name)

    # =========================================================================
    # Agent Permissions (delegated to db/permissions.py) - Phase 9.10
    # =========================================================================

    def get_permitted_agents(self, source_agent: str):
        return self._permission_ops.get_permitted_agents(source_agent)

    def get_permission_details(self, source_agent: str):
        return self._permission_ops.get_permission_details(source_agent)

    def is_agent_permitted(self, source_agent: str, target_agent: str):
        return self._permission_ops.is_permitted(source_agent, target_agent)

    def add_agent_permission(self, source_agent: str, target_agent: str, created_by: str):
        return self._permission_ops.add_permission(source_agent, target_agent, created_by)

    def remove_agent_permission(self, source_agent: str, target_agent: str):
        return self._permission_ops.remove_permission(source_agent, target_agent)

    def set_agent_permissions(self, source_agent: str, target_agents: list, created_by: str):
        return self._permission_ops.set_permissions(source_agent, target_agents, created_by)

    def delete_agent_permissions(self, agent_name: str):
        return self._permission_ops.delete_agent_permissions(agent_name)

    def grant_default_permissions(self, agent_name: str, owner_username: str):
        return self._permission_ops.grant_default_permissions(agent_name, owner_username)

    # =========================================================================
    # Shared Folder Configuration (delegated to db/shared_folders.py) - Phase 9.11
    # =========================================================================

    def get_shared_folder_config(self, agent_name: str):
        return self._shared_folder_ops.get_shared_folder_config(agent_name)

    def upsert_shared_folder_config(self, agent_name: str, expose_enabled=None, consume_enabled=None):
        return self._shared_folder_ops.upsert_shared_folder_config(agent_name, expose_enabled, consume_enabled)

    def delete_shared_folder_config(self, agent_name: str):
        return self._shared_folder_ops.delete_shared_folder_config(agent_name)

    def get_agents_exposing_folders(self):
        return self._shared_folder_ops.get_agents_exposing_folders()

    def get_available_shared_folders(self, requesting_agent: str):
        return self._shared_folder_ops.get_available_shared_folders(requesting_agent)

    def get_consuming_agents(self, source_agent: str):
        return self._shared_folder_ops.get_consuming_agents(source_agent)

    @staticmethod
    def get_shared_volume_name(agent_name: str):
        return SharedFolderOperations.get_shared_volume_name(agent_name)

    @staticmethod
    def get_shared_mount_path(source_agent: str):
        return SharedFolderOperations.get_shared_mount_path(source_agent)

    # =========================================================================
    # System Settings (delegated to db/settings.py)
    # =========================================================================

    def get_setting(self, key: str):
        return self._settings_ops.get_setting(key)

    def get_setting_value(self, key: str, default: str = None):
        return self._settings_ops.get_setting_value(key, default)

    def set_setting(self, key: str, value: str):
        return self._settings_ops.set_setting(key, value)

    def delete_setting(self, key: str):
        return self._settings_ops.delete_setting(key)

    def get_all_settings(self):
        return self._settings_ops.get_all_settings()

    def get_settings_dict(self):
        return self._settings_ops.get_settings_dict()

    # =========================================================================
    # Public Agent Links (delegated to db/public_links.py) - Phase 12.2
    # =========================================================================

    def create_public_link(self, agent_name: str, created_by: str, name: str = None,
                           require_email: bool = False, expires_at: str = None):
        return self._public_link_ops.create_public_link(agent_name, created_by, name, require_email, expires_at)

    def get_public_link(self, link_id: str):
        return self._public_link_ops.get_public_link(link_id)

    def get_public_link_by_token(self, token: str):
        return self._public_link_ops.get_public_link_by_token(token)

    def list_agent_public_links(self, agent_name: str):
        return self._public_link_ops.list_agent_public_links(agent_name)

    def update_public_link(self, link_id: str, name: str = None, enabled: bool = None,
                           require_email: bool = None, expires_at: str = None):
        return self._public_link_ops.update_public_link(link_id, name, enabled, require_email, expires_at)

    def delete_public_link(self, link_id: str):
        return self._public_link_ops.delete_public_link(link_id)

    def delete_agent_public_links(self, agent_name: str):
        return self._public_link_ops.delete_agent_public_links(agent_name)

    def is_public_link_valid(self, token: str):
        return self._public_link_ops.is_link_valid(token)

    # Email verification methods
    def create_verification(self, link_id: str, email: str, expiry_minutes: int = 10):
        return self._public_link_ops.create_verification(link_id, email, expiry_minutes)

    def verify_code(self, link_id: str, email: str, code: str, session_hours: int = 24):
        return self._public_link_ops.verify_code(link_id, email, code, session_hours)

    def validate_session(self, link_id: str, session_token: str):
        return self._public_link_ops.validate_session(link_id, session_token)

    def count_recent_verification_requests(self, email: str, minutes: int = 10):
        return self._public_link_ops.count_recent_verification_requests(email, minutes)

    # Usage tracking methods
    def record_public_link_usage(self, link_id: str, email: str = None, ip_address: str = None):
        return self._public_link_ops.record_usage(link_id, email, ip_address)

    def get_public_link_usage_stats(self, link_id: str):
        return self._public_link_ops.get_link_usage_stats(link_id)

    def count_recent_messages_by_ip(self, ip_address: str, minutes: int = 1):
        return self._public_link_ops.count_recent_messages_by_ip(ip_address, minutes)

    # =========================================================================
    # Email Authentication (delegated to db/email_auth.py) - Phase 12.4
    # =========================================================================

    def is_email_whitelisted(self, email: str):
        return self._email_auth_ops.is_email_whitelisted(email)

    def add_to_whitelist(self, email: str, added_by: str, source: str = "manual"):
        return self._email_auth_ops.add_to_whitelist(email, added_by, source)

    def remove_from_whitelist(self, email: str):
        return self._email_auth_ops.remove_from_whitelist(email)

    def list_whitelist(self, limit: int = 100):
        return self._email_auth_ops.list_whitelist(limit)

    def create_login_code(self, email: str, expiry_minutes: int = 10):
        return self._email_auth_ops.create_login_code(email, expiry_minutes)

    def verify_login_code(self, email: str, code: str):
        return self._email_auth_ops.verify_login_code(email, code)

    def count_recent_code_requests(self, email: str, minutes: int = 10):
        return self._email_auth_ops.count_recent_code_requests(email, minutes)

    def cleanup_old_codes(self, days: int = 1):
        return self._email_auth_ops.cleanup_old_codes(days)

    def get_or_create_email_user(self, email: str):
        return self._email_auth_ops.get_or_create_email_user(email)

    # =========================================================================
    # Agent Skills (delegated to db/skills.py) - Skills Management System
    # =========================================================================

    def get_agent_skills(self, agent_name: str):
        return self._skills_ops.get_agent_skills(agent_name)

    def get_agent_skill_names(self, agent_name: str):
        return self._skills_ops.get_agent_skill_names(agent_name)

    def assign_skill(self, agent_name: str, skill_name: str, assigned_by: str):
        return self._skills_ops.assign_skill(agent_name, skill_name, assigned_by)

    def unassign_skill(self, agent_name: str, skill_name: str):
        return self._skills_ops.unassign_skill(agent_name, skill_name)

    def set_agent_skills(self, agent_name: str, skill_names: list, assigned_by: str):
        return self._skills_ops.set_agent_skills(agent_name, skill_names, assigned_by)

    def delete_agent_skills(self, agent_name: str):
        return self._skills_ops.delete_agent_skills(agent_name)

    def is_skill_assigned(self, agent_name: str, skill_name: str):
        return self._skills_ops.is_skill_assigned(agent_name, skill_name)

    def get_agents_with_skill(self, skill_name: str):
        return self._skills_ops.get_agents_with_skill(skill_name)

    # =========================================================================
    # Public Chat Sessions (delegated to db/public_chat.py) - Phase 12.2.5
    # =========================================================================

    def get_or_create_public_chat_session(self, link_id: str, session_identifier: str, identifier_type: str):
        return self._public_chat_ops.get_or_create_session(link_id, session_identifier, identifier_type)

    def get_public_chat_session_by_identifier(self, link_id: str, session_identifier: str):
        return self._public_chat_ops.get_session_by_identifier(link_id, session_identifier)

    def get_public_chat_session(self, session_id: str):
        return self._public_chat_ops.get_session(session_id)

    def add_public_chat_message(self, session_id: str, role: str, content: str, cost: float = None):
        return self._public_chat_ops.add_message(session_id, role, content, cost)

    def get_public_chat_messages(self, session_id: str, limit: int = 20):
        return self._public_chat_ops.get_session_messages(session_id, limit)

    def get_recent_public_chat_messages(self, session_id: str, limit: int = 20):
        return self._public_chat_ops.get_recent_messages(session_id, limit)

    def clear_public_chat_session(self, session_id: str):
        return self._public_chat_ops.clear_session(session_id)

    def build_public_chat_context(self, session_id: str, new_message: str, max_turns: int = 10):
        return self._public_chat_ops.build_context_prompt(session_id, new_message, max_turns)

    def delete_public_link_sessions(self, link_id: str):
        return self._public_chat_ops.delete_link_sessions(link_id)

    # =========================================================================
    # Agent Tags (delegated to db/tags.py) - ORG-001
    # =========================================================================

    def get_agent_tags(self, agent_name: str):
        return self._tag_ops.get_agent_tags(agent_name)

    def set_agent_tags(self, agent_name: str, tags: list):
        return self._tag_ops.set_agent_tags(agent_name, tags)

    def add_agent_tag(self, agent_name: str, tag: str):
        return self._tag_ops.add_tag(agent_name, tag)

    def remove_agent_tag(self, agent_name: str, tag: str):
        return self._tag_ops.remove_tag(agent_name, tag)

    def list_all_tags(self):
        return self._tag_ops.list_all_tags()

    def get_agents_by_tag(self, tag: str):
        return self._tag_ops.get_agents_by_tag(tag)

    def get_agents_by_tags(self, tags: list):
        return self._tag_ops.get_agents_by_tags(tags)

    def delete_agent_tags(self, agent_name: str):
        return self._tag_ops.delete_agent_tags(agent_name)

    def get_tags_for_agents(self, agent_names: list):
        return self._tag_ops.get_tags_for_agents(agent_names)

    # =========================================================================
    # System Views (delegated to db/system_views.py) - ORG-001 Phase 2
    # =========================================================================

    def create_system_view(self, owner_id: str, data):
        return self._system_view_ops.create_view(owner_id, data)

    def get_system_view(self, view_id: str):
        return self._system_view_ops.get_view(view_id)

    def list_user_system_views(self, user_id: str):
        return self._system_view_ops.list_user_views(user_id)

    def list_all_system_views(self):
        return self._system_view_ops.list_all_views()

    def update_system_view(self, view_id: str, data):
        return self._system_view_ops.update_view(view_id, data)

    def delete_system_view(self, view_id: str):
        return self._system_view_ops.delete_view(view_id)

    def can_user_view_system_view(self, user_id: str, view_id: str):
        return self._system_view_ops.can_user_view(user_id, view_id)

    def can_user_edit_system_view(self, user_id: str, view_id: str, is_admin: bool = False):
        return self._system_view_ops.can_user_edit_view(user_id, view_id, is_admin)

    # =========================================================================
    # Agent Notifications (delegated to db/notifications.py) - NOTIF-001
    # =========================================================================

    def create_notification(self, agent_name: str, data):
        return self._notification_ops.create_notification(agent_name, data)

    def get_notification(self, notification_id: str):
        return self._notification_ops.get_notification(notification_id)

    def list_notifications(self, agent_name=None, status=None, priority=None, limit=100):
        return self._notification_ops.list_notifications(agent_name, status, priority, limit)

    def list_agent_notifications(self, agent_name: str, status=None, limit=50):
        return self._notification_ops.list_agent_notifications(agent_name, status, limit)

    def acknowledge_notification(self, notification_id: str, acknowledged_by: str):
        return self._notification_ops.acknowledge_notification(notification_id, acknowledged_by)

    def dismiss_notification(self, notification_id: str, dismissed_by: str):
        return self._notification_ops.dismiss_notification(notification_id, dismissed_by)

    def delete_agent_notifications(self, agent_name: str):
        return self._notification_ops.delete_agent_notifications(agent_name)

    def count_pending_notifications(self, agent_name=None):
        return self._notification_ops.count_pending_notifications(agent_name)


# Global database manager instance
db = DatabaseManager()
