# src/graphrag_api_service/workspace/database_manager.py
# Database-backed workspace manager
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Database-backed workspace manager for GraphRAG API."""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..database.models import Workspace as DBWorkspace
from .models import Workspace, WorkspaceConfig, WorkspaceCreateRequest

logger = logging.getLogger(__name__)


class DatabaseWorkspaceManager:
    """Database-backed workspace manager for GraphRAG workspaces."""

    def __init__(self, settings: Settings, session_factory):
        """Initialize database workspace manager.

        Args:
            settings: Application settings
            session_factory: Async session factory for database access
        """
        self.settings = settings
        self.session_factory = session_factory
        self.base_workspaces_path = Path("workspaces")

        # Ensure workspaces directory exists
        self.base_workspaces_path.mkdir(exist_ok=True)

    async def create_workspace(
        self, request: WorkspaceCreateRequest, owner_id: str = None
    ) -> Workspace:
        """Create a new GraphRAG workspace.

        Args:
            request: Workspace creation request
            owner_id: Owner user ID (optional, defaults to system user)

        Returns:
            Created workspace

        Raises:
            ValueError: If workspace name already exists or data path is invalid
            OSError: If workspace directories cannot be created
        """
        async with self.session_factory() as session:
            # Check if workspace name already exists
            existing = await session.execute(
                select(DBWorkspace).where(DBWorkspace.name == request.name)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Workspace with name '{request.name}' already exists")

            # Validate data path exists
            data_path = Path(request.data_path)
            if not data_path.exists():
                raise ValueError(f"Data path does not exist: {request.data_path}")

            if not data_path.is_dir():
                raise ValueError(f"Data path is not a directory: {request.data_path}")

            # Create workspace configuration
            config = WorkspaceConfig(
                name=request.name,
                description=request.description,
                data_path=str(data_path.resolve()),
                output_path=None,  # Will be set after directory creation
                chunk_size=request.chunk_size or 1200,
                chunk_overlap=request.chunk_overlap or 100,
                llm_model_override=request.llm_model_override,
                embedding_model_override=request.embedding_model_override,
                max_entities=request.max_entities or 1000,
                max_relationships=request.max_relationships or 2000,
                community_levels=request.community_levels or 4,
            )

            # Generate unique ID
            workspace_id = str(uuid.uuid4())

            # Create workspace directory structure
            workspace_dir = self.base_workspaces_path / workspace_id
            output_dir = workspace_dir / "output"

            try:
                workspace_dir.mkdir(parents=True, exist_ok=False)
                output_dir.mkdir(parents=True, exist_ok=True)

                # Generate GraphRAG configuration file
                config_file_path = workspace_dir / "settings.yaml"
                self._generate_graphrag_config(config, config_file_path)

                # Update workspace paths
                config.output_path = str(output_dir)

                # Create database record
                db_workspace = DBWorkspace(
                    id=uuid.UUID(workspace_id),
                    name=request.name,
                    description=request.description,
                    owner_id=uuid.UUID(owner_id) if owner_id else None,
                    config=config.dict(),
                    data_path=str(data_path.resolve()),
                    workspace_path=str(workspace_dir),
                    config_file_path=str(config_file_path),
                    status="created",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )

                session.add(db_workspace)
                await session.commit()
                await session.refresh(db_workspace)

                # Convert to API model
                workspace = self._db_to_api_model(db_workspace)

                logger.info(f"Created workspace: {workspace.config.name} (ID: {workspace.id})")
                return workspace

            except Exception as e:
                # Cleanup directories on failure
                if workspace_dir.exists():
                    import shutil

                    shutil.rmtree(workspace_dir, ignore_errors=True)
                raise OSError(f"Failed to create workspace directories: {e}") from e

    async def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace or None if not found
        """
        async with self.session_factory() as session:
            db_workspace = await session.get(DBWorkspace, uuid.UUID(workspace_id))
            if not db_workspace:
                return None

            return self._db_to_api_model(db_workspace)

    async def list_workspaces(self, owner_id: str = None) -> list[Workspace]:
        """List all workspaces.

        Args:
            owner_id: Optional owner ID to filter by

        Returns:
            List of workspaces
        """
        async with self.session_factory() as session:
            stmt = select(DBWorkspace)
            if owner_id:
                stmt = stmt.where(DBWorkspace.owner_id == uuid.UUID(owner_id))

            result = await session.execute(stmt)
            db_workspaces = result.scalars().all()

            return [self._db_to_api_model(ws) for ws in db_workspaces]

    async def update_workspace(self, workspace_id: str, **updates) -> Workspace | None:
        """Update workspace.

        Args:
            workspace_id: Workspace ID
            **updates: Fields to update

        Returns:
            Updated workspace or None if not found
        """
        async with self.session_factory() as session:
            db_workspace = await session.get(DBWorkspace, uuid.UUID(workspace_id))
            if not db_workspace:
                return None

            # Update allowed fields
            if "description" in updates:
                db_workspace.description = updates["description"]
            if "status" in updates:
                db_workspace.status = updates["status"]
            if "last_error" in updates:
                db_workspace.last_error = updates["last_error"]
            if "config" in updates:
                db_workspace.config = updates["config"]

            db_workspace.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(db_workspace)

            return self._db_to_api_model(db_workspace)

    async def delete_workspace(self, workspace_id: str) -> bool:
        """Delete workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted successfully
        """
        async with self.session_factory() as session:
            db_workspace = await session.get(DBWorkspace, uuid.UUID(workspace_id))
            if not db_workspace:
                return False

            # Delete workspace directory
            if db_workspace.workspace_path:
                workspace_dir = Path(db_workspace.workspace_path)
                if workspace_dir.exists():
                    import shutil

                    shutil.rmtree(workspace_dir, ignore_errors=True)

            # Delete database record
            await session.delete(db_workspace)
            await session.commit()

            logger.info(f"Deleted workspace: {workspace_id}")
            return True

    async def get_workspace_stats(self) -> dict[str, Any]:
        """Get workspace statistics.

        Returns:
            Dictionary with workspace statistics
        """
        async with self.session_factory() as session:
            result = await session.execute(select(DBWorkspace))
            workspaces = result.scalars().all()

            stats = {
                "total_workspaces": len(workspaces),
                "active_workspaces": len([ws for ws in workspaces if ws.status == "active"]),
                "created_workspaces": len([ws for ws in workspaces if ws.status == "created"]),
                "error_workspaces": len([ws for ws in workspaces if ws.status == "error"]),
            }

            return stats

    def _db_to_api_model(self, db_workspace: DBWorkspace) -> Workspace:
        """Convert database model to API model.

        Args:
            db_workspace: Database workspace model

        Returns:
            API workspace model
        """
        config = WorkspaceConfig(**db_workspace.config)

        return Workspace(
            id=str(db_workspace.id),
            config=config,
            last_error=db_workspace.last_error,
            workspace_path=db_workspace.workspace_path,
            config_file_path=db_workspace.config_file_path,
        )

    def _generate_graphrag_config(self, config: WorkspaceConfig, config_file_path: Path) -> None:
        """Generate GraphRAG configuration file.

        Args:
            config: Workspace configuration
            config_file_path: Path to save configuration file
        """
        # Generate YAML configuration for GraphRAG
        graphrag_config = {
            "encoding_model": config.embedding_model_override or self.settings.embedding_model,
            "llm": {
                "api_key": "${GRAPHRAG_API_KEY}",
                "type": "openai_chat",
                "model": config.llm_model_override or self.settings.llm_model,
                "max_tokens": 4000,
                "temperature": 0,
            },
            "parallelization": {
                "stagger": 0.3,
                "num_threads": 50,
            },
            "async_mode": "threaded",
            "chunks": {
                "size": config.chunk_size,
                "overlap": config.chunk_overlap,
                "group_by_columns": ["id"],
            },
            "input": {
                "type": "file",
                "file_type": "text",
                "base_dir": config.data_path,
                "file_encoding": "utf-8",
                "file_pattern": ".*\\.txt$",
            },
            "cache": {
                "type": "file",
                "base_dir": "${GRAPHRAG_CACHE_DIR}",
            },
            "storage": {
                "type": "file",
                "base_dir": config.output_path,
            },
            "reporting": {
                "type": "file",
                "base_dir": "${GRAPHRAG_REPORTING_DIR}",
            },
            "entity_extraction": {
                "entity_types": ["person", "organization", "location"],
                "max_gleanings": 1,
            },
            "summarize_descriptions": {
                "max_length": 500,
            },
            "community_reports": {
                "max_length": 2000,
                "max_input_length": 8000,
            },
            "claim_extraction": {
                "enabled": True,
                "max_gleanings": 1,
            },
            "embed_graph": {
                "enabled": True,
                "num_walks": 10,
                "walk_length": 40,
                "window_size": 2,
                "iterations": 3,
                "random_seed": 597832,
            },
            "umap": {
                "enabled": True,
            },
            "snapshots": {
                "graphml": False,
                "raw_entities": False,
                "top_level_nodes": False,
            },
            "local_search": {
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "conversation_history_max_turns": 5,
                "top_k_mapped_entities": 10,
                "top_k_relationships": 10,
                "max_tokens": 12000,
            },
            "global_search": {
                "max_tokens": 12000,
                "data_max_tokens": 12000,
                "map_max_tokens": 1000,
                "reduce_max_tokens": 2000,
                "concurrency": 32,
            },
        }

        # Write YAML configuration
        import yaml

        with open(config_file_path, "w", encoding="utf-8") as f:
            yaml.dump(graphrag_config, f, default_flow_style=False, indent=2)
