# src/graphrag_api_service/database/migrations/auth_migration.py
# Authentication system database migration
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Database migration for authentication system Phase 1."""

import logging
import os
from pathlib import Path

from ..sqlite_models import SQLiteManager

logger = logging.getLogger(__name__)


def run_auth_migration(db_path: str = "data/graphrag.db", create_admin: bool = True) -> bool:
    """Run the authentication system migration.

    This migration:
    1. Creates the users table with proper schema
    2. Creates the user_sessions table for token management
    3. Adds necessary indexes for performance
    4. Optionally creates a default admin user

    Args:
        db_path: Path to the SQLite database file
        create_admin: Whether to create a default admin user

    Returns:
        True if migration completed successfully, False otherwise
    """
    try:
        logger.info("Starting authentication system migration...")

        # Initialize SQLite manager (this will create tables if they don't exist)
        db_manager = SQLiteManager(db_path)

        # Check if migration has already been run
        if _migration_already_run(db_manager):
            logger.info("Authentication migration already completed")
            return True

        # Create default admin user if requested
        if create_admin:
            _create_default_admin_user(db_manager)

        # Mark migration as completed
        _mark_migration_complete(db_manager)

        logger.info("Authentication system migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Authentication migration failed: {e}")
        return False


def _migration_already_run(db_manager: SQLiteManager) -> bool:
    """Check if the authentication migration has already been run."""
    try:
        # Check if we have any users in the database
        import sqlite3

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]

            # If we have users, assume migration has been run
            return user_count > 0

    except sqlite3.OperationalError:
        # Table doesn't exist, migration hasn't been run
        return False
    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return False


def _create_default_admin_user(db_manager: SQLiteManager) -> None:
    """Create a default admin user for initial system access."""
    try:
        # Get admin credentials from environment or use defaults
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@graphrag.local")
        admin_password = os.getenv("ADMIN_PASSWORD", "GraphRAG_Admin_2025!")

        # Check if admin user already exists
        if db_manager.user_exists(admin_email, admin_username):
            logger.info("Default admin user already exists")
            return

        # Create admin user
        admin_user = db_manager.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            full_name="System Administrator",
            roles=["admin", "user"],
            permissions=[
                "read:workspaces",
                "write:workspaces",
                "delete:workspaces",
                "manage:users",
                "manage:api_keys",
                "admin:system",
            ],
            is_admin=True,
        )

        logger.info(f"Created default admin user: {admin_username} ({admin_email})")
        logger.warning(
            "SECURITY WARNING: Default admin user created with standard credentials. "
            "Please change the password immediately after first login!"
        )

    except Exception as e:
        logger.error(f"Failed to create default admin user: {e}")
        raise


def _mark_migration_complete(db_manager: SQLiteManager) -> None:
    """Mark the migration as completed by creating a migration record."""
    try:
        import sqlite3
        from datetime import UTC, datetime

        # Create migrations table if it doesn't exist
        with sqlite3.connect(db_manager.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    version TEXT DEFAULT '1.0.0'
                )
                """
            )

            # Record this migration
            conn.execute(
                "INSERT OR IGNORE INTO migrations (name, applied_at, version) VALUES (?, ?, ?)",
                ("auth_system_phase1", datetime.now(UTC).isoformat(), "1.0.0"),
            )
            conn.commit()

        logger.info("Migration marked as complete")

    except Exception as e:
        logger.error(f"Failed to mark migration as complete: {e}")
        raise


def verify_migration(db_path: str = "data/graphrag.db") -> dict[str, bool]:
    """Verify that the authentication migration was successful.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with verification results
    """
    results = {
        "users_table_exists": False,
        "user_sessions_table_exists": False,
        "indexes_created": False,
        "admin_user_exists": False,
        "migration_recorded": False,
    }

    try:
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            results["users_table_exists"] = cursor.fetchone() is not None

            # Check if user_sessions table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions'"
            )
            results["user_sessions_table_exists"] = cursor.fetchone() is not None

            # Check if indexes exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_email'"
            )
            results["indexes_created"] = cursor.fetchone() is not None

            # Check if admin user exists
            if results["users_table_exists"]:
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
                admin_count = cursor.fetchone()[0]
                results["admin_user_exists"] = admin_count > 0

            # Check if migration is recorded
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
            )
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM migrations WHERE name = 'auth_system_phase1'")
                results["migration_recorded"] = cursor.fetchone()[0] > 0

    except Exception as e:
        logger.error(f"Migration verification failed: {e}")

    return results


if __name__ == "__main__":
    # Allow running migration directly
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/graphrag.db"
    create_admin = "--no-admin" not in sys.argv

    logging.basicConfig(level=logging.INFO)

    success = run_auth_migration(db_path, create_admin)

    if success:
        print("✅ Authentication migration completed successfully")

        # Verify migration
        results = verify_migration(db_path)
        print("\n📋 Migration Verification:")
        for check, passed in results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")

        if all(results.values()):
            print("\n🎉 All verification checks passed!")
        else:
            print("\n⚠️  Some verification checks failed")
            sys.exit(1)
    else:
        print("❌ Authentication migration failed")
        sys.exit(1)
