# src/graphrag_api_service/database/simple_connection.py
# Simplified database connection for small-scale deployment
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Simplified database connection management supporting SQLite and PostgreSQL."""

import logging

from ..config import Settings
from .sqlite_models import SQLiteManager

logger = logging.getLogger(__name__)


class SimpleDatabaseManager:
    """Simple database manager supporting SQLite (primary) and PostgreSQL (optional)."""

    def __init__(self, settings: Settings):
        """Initialize database manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.db_type = settings.database_type.lower()
        self.db: SQLiteManager | None = None
        self._initialized = False

    def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return

        try:
            if self.db_type == "sqlite":
                # Use SQLite for simplicity
                self.db = SQLiteManager(self.settings.database_path)
                logger.info(f"SQLite database initialized at: {self.settings.database_path}")
            else:
                # PostgreSQL support can be added later if needed
                raise NotImplementedError(
                    "PostgreSQL support not implemented in simple mode. Use SQLite instead."
                )

            self._initialized = True
            logger.info(f"Database ({self.db_type}) initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_workspace_manager(self):
        """Get workspace manager for the current database type.

        Returns:
            Workspace manager instance
        """
        if not self._initialized:
            self.initialize()

        if self.db_type == "sqlite":
            from ..workspace.sqlite_manager import SQLiteWorkspaceManager

            return SQLiteWorkspaceManager(self.settings)
        else:
            raise NotImplementedError("Only SQLite is supported in simple mode")

    def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is accessible
        """
        try:
            if not self._initialized:
                self.initialize()

            if self.db_type == "sqlite" and self.db is not None:
                # Simple SQLite health check
                self.db.list_workspaces(limit=1)
                return True

            return False

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
            logger.info("Database connection closed")
            self._initialized = False


# Global database manager
_simple_db_manager: SimpleDatabaseManager | None = None


def get_simple_database_manager(settings: Settings | None = None) -> SimpleDatabaseManager:
    """Get the global simple database manager.

    Args:
        settings: Optional application settings

    Returns:
        SimpleDatabaseManager instance
    """
    global _simple_db_manager

    if _simple_db_manager is None:
        if not settings:
            from ..config import Settings

            settings = Settings()
        _simple_db_manager = SimpleDatabaseManager(settings)

    return _simple_db_manager
