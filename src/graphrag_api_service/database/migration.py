# src/graphrag_api_service/database/migration.py
# Data migration utilities for GraphRAG API service
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Data migration utilities for migrating from JSON files to database."""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .models import IndexingJob, Role, User, Workspace

logger = logging.getLogger(__name__)


class DataMigrator:
    """Handles migration of data from JSON files to database."""

    def __init__(self, session: Session):
        """Initialize data migrator.

        Args:
            session: Database session
        """
        self.session = session

    async def migrate_workspaces(self, workspaces_file: Path) -> int:
        """Migrate workspaces from JSON file to database.

        Args:
            workspaces_file: Path to workspaces.json file

        Returns:
            Number of workspaces migrated
        """
        if not workspaces_file.exists():
            logger.info(f"Workspaces file not found: {workspaces_file}")
            return 0

        try:
            with open(workspaces_file, "r", encoding="utf-8") as f:
                workspaces_data = json.load(f)

            migrated_count = 0

            # Get or create default admin user for workspace ownership
            admin_user = self._get_or_create_admin_user()

            for workspace_id, workspace_data in workspaces_data.items():
                try:
                    # Check if workspace already exists
                    existing = self.session.query(Workspace).filter_by(id=workspace_id).first()
                    if existing:
                        logger.debug(f"Workspace {workspace_id} already exists, skipping")
                        continue

                    # Create workspace from JSON data
                    workspace = Workspace(
                        id=uuid.UUID(workspace_id) if workspace_id else uuid.uuid4(),
                        name=workspace_data.get("name", f"Workspace {workspace_id}"),
                        description=workspace_data.get("description"),
                        owner_id=admin_user.id,  # Assign to admin user
                        config=workspace_data.get("config", {}),
                        data_path=workspace_data.get("data_path", ""),
                        workspace_path=workspace_data.get("workspace_path"),
                        config_file_path=workspace_data.get("config_file_path"),
                        status=workspace_data.get("status", "created"),
                        created_at=self._parse_datetime(workspace_data.get("created_at")),
                        updated_at=self._parse_datetime(workspace_data.get("updated_at")),
                        last_accessed_at=self._parse_datetime(
                            workspace_data.get("last_accessed_at")
                        ),
                    )

                    self.session.add(workspace)
                    migrated_count += 1
                    logger.debug(f"Migrated workspace: {workspace.name}")

                except Exception as e:
                    logger.error(f"Failed to migrate workspace {workspace_id}: {e}")
                    continue

            self.session.commit()
            logger.info(f"Successfully migrated {migrated_count} workspaces")
            return migrated_count

        except Exception as e:
            logger.error(f"Failed to migrate workspaces: {e}")
            self.session.rollback()
            raise

    async def migrate_indexing_jobs(self, jobs_directory: Path) -> int:
        """Migrate indexing jobs from JSON files to database.

        Args:
            jobs_directory: Path to indexing_jobs directory

        Returns:
            Number of jobs migrated
        """
        if not jobs_directory.exists():
            logger.info(f"Jobs directory not found: {jobs_directory}")
            return 0

        try:
            migrated_count = 0

            # Find all job JSON files
            for job_file in jobs_directory.glob("*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        job_data = json.load(f)

                    job_id = job_file.stem

                    # Check if job already exists
                    existing = self.session.query(IndexingJob).filter_by(id=job_id).first()
                    if existing:
                        logger.debug(f"Job {job_id} already exists, skipping")
                        continue

                    # Find corresponding workspace
                    workspace_id = job_data.get("workspace_id")
                    workspace = self.session.query(Workspace).filter_by(id=workspace_id).first()
                    if not workspace:
                        logger.warning(
                            f"Workspace {workspace_id} not found for job {job_id}, skipping"
                        )
                        continue

                    # Create job from JSON data
                    job = IndexingJob(
                        id=uuid.UUID(job_id) if job_id else uuid.uuid4(),
                        workspace_id=workspace.id,
                        config=job_data.get("config", {}),
                        status=job_data.get("status", "pending"),
                        stage=job_data.get("stage"),
                        progress_percentage=job_data.get("progress_percentage", 0),
                        result=job_data.get("result"),
                        error_message=job_data.get("error_message"),
                        files_processed=job_data.get("files_processed", 0),
                        entities_extracted=job_data.get("entities_extracted", 0),
                        relationships_extracted=job_data.get("relationships_extracted", 0),
                        retry_count=job_data.get("retry_count", 0),
                        max_retries=job_data.get("max_retries", 3),
                        created_at=self._parse_datetime(job_data.get("created_at")),
                        started_at=self._parse_datetime(job_data.get("started_at")),
                        completed_at=self._parse_datetime(job_data.get("completed_at")),
                        updated_at=self._parse_datetime(job_data.get("updated_at")),
                    )

                    self.session.add(job)
                    migrated_count += 1
                    logger.debug(f"Migrated job: {job_id}")

                except Exception as e:
                    logger.error(f"Failed to migrate job {job_file}: {e}")
                    continue

            self.session.commit()
            logger.info(f"Successfully migrated {migrated_count} indexing jobs")
            return migrated_count

        except Exception as e:
            logger.error(f"Failed to migrate indexing jobs: {e}")
            self.session.rollback()
            raise

    def _get_or_create_admin_user(self) -> User:
        """Get or create default admin user for data migration.

        Returns:
            Admin user instance
        """
        # Check if admin user exists
        admin_user = self.session.query(User).filter_by(username="admin").first()
        if admin_user:
            return admin_user

        # Create admin role if it doesn't exist
        admin_role = self.session.query(Role).filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrator role with full permissions",
                permissions=["manage:all", "read:all", "write:all", "delete:all"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.session.add(admin_role)

        # Create admin user with secure password hash
        import bcrypt

        # Generate a secure hash for the default password "admin123"
        # This should be changed on first login
        default_password = "admin123"
        password_hash = bcrypt.hashpw(default_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        admin_user = User(
            username="admin",
            email="admin@graphrag.local",
            password_hash=password_hash,
            full_name="System Administrator",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        admin_user.roles.append(admin_role)

        self.session.add(admin_user)
        self.session.commit()

        logger.info("Created default admin user for migration")
        return admin_user

    def _parse_datetime(self, datetime_str: str | None) -> datetime | None:
        """Parse datetime string to datetime object.

        Args:
            datetime_str: ISO format datetime string

        Returns:
            Parsed datetime or None
        """
        if not datetime_str:
            return None

        try:
            # Try parsing ISO format
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            try:
                # Try parsing timestamp
                return datetime.fromtimestamp(float(datetime_str), tz=UTC)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse datetime: {datetime_str}")
                return datetime.now(UTC)


async def run_data_migration(session: Session, data_directory: Path = None) -> dict[str, int]:
    """Run complete data migration from JSON files to database.

    Args:
        session: Database session
        data_directory: Optional data directory path (defaults to current directory)

    Returns:
        Dictionary with migration counts
    """
    if not data_directory:
        data_directory = Path.cwd()

    migrator = DataMigrator(session)

    results = {
        "workspaces": 0,
        "indexing_jobs": 0,
    }

    # Migrate workspaces
    workspaces_file = data_directory / "workspaces.json"
    results["workspaces"] = await migrator.migrate_workspaces(workspaces_file)

    # Migrate indexing jobs
    jobs_directory = data_directory / "indexing_jobs"
    results["indexing_jobs"] = await migrator.migrate_indexing_jobs(jobs_directory)

    logger.info(f"Migration completed: {results}")
    return results
