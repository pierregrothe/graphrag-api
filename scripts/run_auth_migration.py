#!/usr/bin/env python3
# scripts/run_auth_migration.py
# Script to run authentication system migration
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Script to run the authentication system database migration."""

import argparse
import logging
import sys
from pathlib import Path

from graphrag_api_service.database.migrations.auth_migration import (
    run_auth_migration,
    verify_migration,
)

# Add the src directory to the Python path (after imports to avoid E402)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run GraphRAG API Service authentication system migration"
    )
    parser.add_argument(
        "--db-path",
        default="data/graphrag.db",
        help="Path to SQLite database file (default: data/graphrag.db)",
    )
    parser.add_argument("--no-admin", action="store_true", help="Skip creating default admin user")
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify migration, don't run it"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser


def setup_logging(verbose: bool) -> logging.Logger:
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def print_verification_results(results: dict[str, bool]) -> bool:
    """Print verification results and return whether all passed."""
    print("\n📋 Migration Verification Results:")
    all_passed = True
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    return all_passed


def handle_verify_only(db_path: str, logger: logging.Logger) -> int:
    """Handle verify-only mode."""
    logger.info("Verifying authentication migration...")
    results = verify_migration(db_path)

    all_passed = print_verification_results(results)

    if all_passed:
        print("\n🎉 All verification checks passed!")
        return 0
    else:
        print("\n⚠️  Some verification checks failed")
        return 1


def print_admin_info() -> None:
    """Print admin user creation information."""
    print("\n🔐 Default Admin User Created:")
    print("  Username: admin")
    print("  Email: admin@graphrag.local")
    print("  Password: GraphRAG_Admin_2025!")
    print("\n⚠️  SECURITY WARNING: Please change the admin password immediately!")


def handle_migration_run(db_path: str, create_admin: bool, logger: logging.Logger) -> int:
    """Handle migration run mode."""
    logger.info("Starting authentication system migration...")

    success = run_auth_migration(db_path, create_admin)

    if not success:
        print("❌ Authentication migration failed")
        return 1

    print("✅ Authentication migration completed successfully")

    # Verify migration
    logger.info("Verifying migration...")
    results = verify_migration(db_path)

    print("\n📋 Migration Verification:")
    all_passed = print_verification_results(results)

    if all_passed:
        print("\n🎉 Migration completed and verified successfully!")
        if create_admin:
            print_admin_info()
        return 0
    else:
        print("\n⚠️  Migration completed but verification failed")
        return 1


def _run_migration_logic(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Encapsulates the core migration logic."""
    if args.verify_only:
        return handle_verify_only(args.db_path, logger)
    else:
        create_admin = not args.no_admin
        return handle_migration_run(args.db_path, create_admin, logger)


def main() -> int:
    """Main function to run the migration."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    try:
        return _run_migration_logic(args, logger)
    except KeyboardInterrupt:
        print("\n⏹️  Migration cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
