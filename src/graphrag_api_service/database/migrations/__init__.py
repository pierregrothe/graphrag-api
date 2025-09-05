# src/graphrag_api_service/database/migrations/__init__.py
# Database migrations module
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Database migrations for GraphRAG API Service."""

from .auth_migration import run_auth_migration

__all__ = [
    "run_auth_migration",
]
