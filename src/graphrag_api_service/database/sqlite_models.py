# src/graphrag_api_service/database/sqlite_models.py
# SQLite database models for lightweight deployment
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""SQLite database models for the GraphRAG API Service."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class SQLiteManager:
    """Lightweight SQLite database manager for GraphRAG."""

    def __init__(self, db_path: str = "data/graphrag.db"):
        """Initialize SQLite database manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
        query = f"UPDATE workspaces SET {', '.join(set_clauses)}, updated_at = ? WHERE id = ?"

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
