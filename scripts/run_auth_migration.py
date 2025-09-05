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

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graphrag_api_service.database.migrations.auth_migration import (
    run_auth_migration,
    verify_migration,
)


def main():
    """Main function to run the migration."""
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

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    try:
        if args.verify_only:
            # Only verify the migration
            logger.info("Verifying authentication migration...")
            results = verify_migration(args.db_path)

            print("\n📋 Migration Verification Results:")
            all_passed = True
            for check, passed in results.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check.replace('_', ' ').title()}")
                if not passed:
                    all_passed = False

            if all_passed:
                print("\n🎉 All verification checks passed!")
                return 0
            else:
                print("\n⚠️  Some verification checks failed")
                return 1

        else:
            # Run the migration
            logger.info("Starting authentication system migration...")

            create_admin = not args.no_admin
            success = run_auth_migration(args.db_path, create_admin)

            if success:
                print("✅ Authentication migration completed successfully")

                # Verify migration
                logger.info("Verifying migration...")
                results = verify_migration(args.db_path)

                print("\n📋 Migration Verification:")
                all_passed = True
                for check, passed in results.items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check.replace('_', ' ').title()}")
                    if not passed:
                        all_passed = False

                if all_passed:
                    print("\n🎉 Migration completed and verified successfully!")

                    if create_admin:
                        print("\n🔐 Default Admin User Created:")
                        print("  Username: admin")
                        print("  Email: admin@graphrag.local")
                        print("  Password: GraphRAG_Admin_2025!")
                        print(
                            "\n⚠️  SECURITY WARNING: Please change the admin password immediately!"
                        )

                    return 0
                else:
                    print("\n⚠️  Migration completed but verification failed")
                    return 1
            else:
                print("❌ Authentication migration failed")
                return 1

    except KeyboardInterrupt:
        print("\n⏹️  Migration cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
