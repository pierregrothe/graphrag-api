# src/graphrag_api_service/database/sqlite_models.py
# SQLite database models for lightweight deployment
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""SQLite database models for the GraphRAG API Service."""

import json
import sqlite3
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Suppress passlib bcrypt warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from passlib.context import CryptContext


class SQLiteManager:
    """Lightweight SQLite database manager for GraphRAG."""

    def __init__(self, db_path: str = "data/graphrag.db"):
        """Initialize SQLite database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize password context for secure hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        self._init_database()

    def _init_database(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            conn.execute("PRAGMA foreign_keys=ON")

            # Create workspaces table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    config TEXT DEFAULT '{}',
                    data_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create queries table (for tracking API usage)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queries (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT,
                    query_text TEXT NOT NULL,
                    response TEXT,
                    processing_time_ms INTEGER,
                    tokens_used INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
                )
            """
            )

            # Create users table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    roles TEXT DEFAULT '["user"]',
                    permissions TEXT DEFAULT '["read:workspaces"]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """
            )

            # Create user sessions table for token management
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT UNIQUE NOT NULL,
                    device_info TEXT,
                    ip_address TEXT,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT,
                    is_revoked BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """
            )

            # Create simple API keys table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    permissions TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT
                )
            """
            )

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workspace_name ON workspaces(name)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_queries_workspace ON queries(workspace_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")

            # User table indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)")

            # User sessions indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(refresh_token_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_revoked ON user_sessions(is_revoked)"
            )

            conn.commit()

    def create_workspace(
        self, name: str, description: str | None = None, config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new workspace."""
        workspace_id = str(uuid4())
        config_json = json.dumps(config or {})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO workspaces (id, name, description, config)
                   VALUES (?, ?, ?, ?)""",
                (workspace_id, name, description, config_json),
            )
            conn.commit()

        return {
            "id": workspace_id,
            "name": name,
            "description": description,
            "config": config or {},
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        """Get workspace by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "status": row["status"],
                    "config": json.loads(row["config"]),
                    "data_path": row["data_path"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    def list_workspaces(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List all workspaces."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM workspaces
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            )

            workspaces = []
            for row in cursor:
                workspaces.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "description": row["description"],
                        "status": row["status"],
                        "created_at": row["created_at"],
                    }
                )

            return workspaces

    def update_workspace(self, workspace_id: str, updates: dict[str, Any]) -> bool:
        """Update workspace."""
        # Define allowed fields with explicit mapping for security
        allowed_fields = {
            "name": "name",
            "description": "description",
            "status": "status",
            "config": "config",
            "data_path": "data_path",
        }
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                if field == "config":
                    value = json.dumps(value)
                # Use explicit field mapping to prevent injection
                set_clauses.append(f"{allowed_fields[field]} = ?")
                values.append(value)

        if not set_clauses:
            return False

        values.append(datetime.now().isoformat())
        values.append(workspace_id)

        # Use parameterized query with explicit field validation
        # Note: set_clauses are built from whitelisted allowed_fields, preventing SQL injection
        query = f"UPDATE workspaces SET {', '.join(set_clauses)}, updated_at = ? WHERE id = ?"  # nosec B608 - Fields are whitelisted

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(query, values)
            conn.commit()
            return result.rowcount > 0

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete workspace."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete related queries first
            conn.execute("DELETE FROM queries WHERE workspace_id = ?", (workspace_id,))
            # Delete workspace
            result = conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
            conn.commit()
            return result.rowcount > 0

    def get_workspace_by_name(self, name: str) -> dict | None:
        """Get workspace by name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM workspaces WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "status": row["status"],
                    "config": json.loads(row["config"]),
                    "data_path": row["data_path"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    def log_query(
        self,
        workspace_id: str,
        query_text: str,
        response: str | None = None,
        processing_time_ms: int | None = None,
        tokens_used: int | None = None,
    ) -> str:
        """Log a query for analytics."""
        query_id = str(uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO queries
                   (id, workspace_id, query_text, response, processing_time_ms, tokens_used)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (query_id, workspace_id, query_text, response, processing_time_ms, tokens_used),
            )
            conn.commit()

        return query_id

    def get_workspace_stats(self, workspace_id: str) -> dict:
        """Get workspace statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT
                    COUNT(*) as query_count,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(tokens_used) as total_tokens
                   FROM queries
                   WHERE workspace_id = ?""",
                (workspace_id,),
            )
            row = cursor.fetchone()

            return {
                "query_count": row[0] or 0,
                "avg_processing_time": row[1] or 0,
                "total_tokens": row[2] or 0,
            }

    def create_api_key(self, name: str, key_hash: str, permissions: list | None = None) -> str:
        """Create an API key."""
        key_id = str(uuid4())
        permissions_json = json.dumps(permissions or [])

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO api_keys (id, key_hash, name, permissions)
                   VALUES (?, ?, ?, ?)""",
                (key_id, key_hash, name, permissions_json),
            )
            conn.commit()

        return key_id

    def validate_api_key(self, key_hash: str) -> dict | None:
        """Validate an API key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Update last used
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
                (datetime.now().isoformat(), key_hash),
            )

            # Get key info
            cursor = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,))
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "permissions": json.loads(row["permissions"]),
                }
            return None

    # User Management Methods

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(password, password_hash)

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str | None = None,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """Create a new user."""
        user_id = str(uuid4())
        password_hash = self.hash_password(password)
        roles_json = json.dumps(roles or ["user"])
        permissions_json = json.dumps(permissions or ["read:workspaces"])
        metadata_json = json.dumps({})
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO users
                   (user_id, username, email, password_hash, full_name, is_active, is_admin,
                    roles, permissions, created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    username,
                    email,
                    password_hash,
                    full_name,
                    True,
                    is_admin,
                    roles_json,
                    permissions_json,
                    now,
                    now,
                    metadata_json,
                ),
            )
            conn.commit()

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "is_active": True,
            "is_admin": is_admin,
            "roles": roles or ["user"],
            "permissions": permissions or ["read:workspaces"],
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "metadata": {},
        }

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "full_name": row["full_name"],
                    "is_active": bool(row["is_active"]),
                    "is_admin": bool(row["is_admin"]),
                    "roles": json.loads(row["roles"]),
                    "permissions": json.loads(row["permissions"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "last_login_at": row["last_login_at"],
                    "metadata": json.loads(row["metadata"]),
                }
            return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()

            if row:
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "full_name": row["full_name"],
                    "is_active": bool(row["is_active"]),
                    "is_admin": bool(row["is_admin"]),
                    "roles": json.loads(row["roles"]),
                    "permissions": json.loads(row["permissions"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "last_login_at": row["last_login_at"],
                    "metadata": json.loads(row["metadata"]),
                }
            return None

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

            if row:
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "full_name": row["full_name"],
                    "is_active": bool(row["is_active"]),
                    "is_admin": bool(row["is_admin"]),
                    "roles": json.loads(row["roles"]),
                    "permissions": json.loads(row["permissions"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "last_login_at": row["last_login_at"],
                    "metadata": json.loads(row["metadata"]),
                }
            return None

    def user_exists(self, email: str, username: str | None = None) -> bool:
        """Check if user exists by email or username."""
        with sqlite3.connect(self.db_path) as conn:
            if username:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE email = ? OR username = ?", (email, username)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
            count = cursor.fetchone()[0]
            return count > 0

    def update_user(self, user_id: str, updates: dict[str, Any]) -> bool:
        """Update user information."""
        allowed_fields = {
            "username": "username",
            "email": "email",
            "full_name": "full_name",
            "is_active": "is_active",
            "is_admin": "is_admin",
            "roles": "roles",
            "permissions": "permissions",
            "metadata": "metadata",
        }

        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                if field in ["roles", "permissions", "metadata"]:
                    value = json.dumps(value)
                set_clauses.append(f"{allowed_fields[field]} = ?")
                values.append(value)

        if not set_clauses:
            return False

        values.append(datetime.now(UTC).isoformat())
        values.append(user_id)

        query = f"UPDATE users SET {', '.join(set_clauses)}, updated_at = ? WHERE user_id = ?"  # nosec B608 - Fields are whitelisted

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(query, values)
            conn.commit()
            return result.rowcount > 0

    def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password."""
        password_hash = self.hash_password(new_password)
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
                (password_hash, now, user_id),
            )
            conn.commit()
            return result.rowcount > 0

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
                (now, now, user_id),
            )
            conn.commit()
            return result.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by deactivating)."""
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE users SET is_active = 0, updated_at = ? WHERE user_id = ?", (now, user_id)
            )
            conn.commit()
            return result.rowcount > 0

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)

        if user and user["is_active"] and self.verify_password(password, user["password_hash"]):
            # Update last login
            self.update_last_login(user["user_id"])
            # Return user data (password_hash is excluded by User model)
            return user

        return None

    # Session Management Methods

    def create_user_session(
        self,
        user_id: str,
        refresh_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        """Create a new user session."""
        session_id = str(uuid4())
        refresh_token_hash = self.hash_password(refresh_token)

        if expires_at is None:
            # Default to 30 days from now
            from datetime import timedelta

            expires_at = datetime.now(UTC) + timedelta(days=30)

        expires_at_str = expires_at.isoformat()
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO user_sessions
                   (session_id, user_id, refresh_token_hash, device_info, ip_address,
                    expires_at, created_at, last_used_at, is_revoked)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    user_id,
                    refresh_token_hash,
                    device_info,
                    ip_address,
                    expires_at_str,
                    now,
                    now,
                    False,
                ),
            )
            conn.commit()

        return session_id

    def get_user_session(self, session_id: str) -> dict[str, Any] | None:
        """Get user session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "session_id": row["session_id"],
                    "user_id": row["user_id"],
                    "refresh_token_hash": row["refresh_token_hash"],
                    "device_info": row["device_info"],
                    "ip_address": row["ip_address"],
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                    "last_used_at": row["last_used_at"],
                    "is_revoked": bool(row["is_revoked"]),
                }
            return None

    def validate_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        """Validate refresh token and return session info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM user_sessions
                   WHERE is_revoked = 0 AND datetime(expires_at) > datetime('now')"""
            )

            for row in cursor:
                if self.verify_password(refresh_token, row["refresh_token_hash"]):
                    # Update last used timestamp
                    now = datetime.now(UTC).isoformat()
                    conn.execute(
                        "UPDATE user_sessions SET last_used_at = ? WHERE session_id = ?",
                        (now, row["session_id"]),
                    )
                    conn.commit()

                    return {
                        "session_id": row["session_id"],
                        "user_id": row["user_id"],
                        "device_info": row["device_info"],
                        "ip_address": row["ip_address"],
                        "expires_at": row["expires_at"],
                        "created_at": row["created_at"],
                        "last_used_at": now,
                    }
            return None

    def revoke_user_session(self, session_id: str) -> bool:
        """Revoke a user session."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE user_sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,)
            )
            conn.commit()
            return result.rowcount > 0

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE user_sessions SET is_revoked = 1 WHERE user_id = ?", (user_id,)
            )
            conn.commit()
            return result.rowcount

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM user_sessions WHERE datetime(expires_at) <= datetime('now')"
            )
            conn.commit()
            return result.rowcount

    def close(self) -> None:
        """Close database connection (for cleanup)."""
        # SQLite connections are closed automatically
        pass


# Global instance for easy access
_db_manager: SQLiteManager | None = None


def get_db_manager(db_path: str = "data/graphrag.db") -> SQLiteManager:
    """Get or create the database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = SQLiteManager(db_path)
    return _db_manager
