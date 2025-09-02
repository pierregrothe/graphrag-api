# src/graphrag_api_service/database/__init__.py
# Database module initialization
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Database module for GraphRAG API service - simplified SQLite implementation."""

from .models import ApiKey, AuditLog, Base, IndexingJob, Role, User, UserRole, Workspace
from .simple_connection import SimpleDatabaseManager, get_simple_database_manager
from .sqlite_models import SQLiteManager, get_db_manager

__all__ = [
    "SimpleDatabaseManager",
    "get_simple_database_manager",
    "SQLiteManager",
    "get_db_manager",
    "Base",
    "User",
    "Role",
    "UserRole",
    "ApiKey",
    "AuditLog",
    "Workspace",
    "IndexingJob",
]
