# src/graphrag_api_service/workspace/sqlite_manager.py
# SQLite-based workspace manager for simplified deployment
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""SQLite-based workspace manager for GraphRAG API."""

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from ..config import Settings
from ..database.sqlite_models import SQLiteManager
from .models import Workspace, WorkspaceConfig, WorkspaceCreateRequest

logger = logging.getLogger(__name__)


class SQLiteWorkspaceManager:
    """SQLite-based workspace manager for GraphRAG workspaces."""

    def __init__(self, settings: Settings):
        """Initialize SQLite workspace manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.db = SQLiteManager(settings.database_path or "data/graphrag.db")
        self.base_workspaces_path = Path("workspaces")

        # Ensure workspaces directory exists
        self.base_workspaces_path.mkdir(exist_ok=True)

    def create_workspace(
        self, request: WorkspaceCreateRequest, owner_id: str | None = None
    ) -> Workspace:
        """Create a new GraphRAG workspace.

        Args:
            request: Workspace creation request
            owner_id: Owner user ID (optional)

        Returns:
            Created workspace

        Raises:
            ValueError: If workspace name already exists or data path is invalid
            OSError: If workspace directories cannot be created
        """
        # Check if workspace name already exists
        existing = self.db.get_workspace_by_name(request.name)
        if existing:
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
            workspace_data = {
                "config": config.dict(),
                "data_path": str(data_path.resolve()),
                "workspace_path": str(workspace_dir),
                "config_file_path": str(config_file_path),
                "status": "created",
            }

            db_workspace = self.db.create_workspace(
                name=request.name, description=request.description, config=workspace_data
            )

            # Convert to API model
            workspace = Workspace(
                id=db_workspace["id"],
                config=config,
                last_error=None,
                workspace_path=str(workspace_dir),
                config_file_path=str(config_file_path),
            )

            logger.info(f"Created workspace: {workspace.config.name} (ID: {workspace.id})")
            return workspace

        except Exception as e:
            # Cleanup directories on failure
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir, ignore_errors=True)
            raise OSError(f"Failed to create workspace directories: {e}") from e

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace or None if not found
        """
        db_workspace = self.db.get_workspace(workspace_id)
        if not db_workspace:
            return None

        return self._db_to_api_model(db_workspace)

    def get_workspace_by_name(self, name: str) -> Workspace | None:
        """Get workspace by name.

        Args:
            name: Workspace name

        Returns:
            Workspace or None if not found
        """
        db_workspace = self.db.get_workspace_by_name(name)
        if not db_workspace:
            return None

        return self._db_to_api_model(db_workspace)

    def list_workspaces(self, limit: int = 10, offset: int = 0) -> list[Workspace]:
        """List all workspaces.

        Args:
            limit: Maximum number of workspaces to return
            offset: Number of workspaces to skip

        Returns:
            List of workspaces
        """
        db_workspaces = self.db.list_workspaces(limit=limit, offset=offset)
        return [self._db_to_api_model(ws) for ws in db_workspaces]

    def update_workspace(self, workspace_id: str, **updates) -> Workspace | None:
        """Update workspace.

        Args:
            workspace_id: Workspace ID
            **updates: Fields to update

        Returns:
            Updated workspace or None if not found
        """
        success = self.db.update_workspace(workspace_id, updates)
        if not success:
            return None

        return self.get_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str, remove_files: bool = False) -> bool:
        """Delete workspace.

        Args:
            workspace_id: Workspace ID
            remove_files: Whether to remove workspace files

        Returns:
            True if deleted successfully
        """
        # Get workspace for cleanup
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False

        # Delete workspace directory if requested
        if remove_files and workspace.workspace_path:
            workspace_dir = Path(workspace.workspace_path)
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir, ignore_errors=True)

        # Delete database record
        success = self.db.delete_workspace(workspace_id)

        if success:
            logger.info(f"Deleted workspace: {workspace_id}")

        return success

    def get_workspace_stats(self) -> dict[str, Any]:
        """Get workspace statistics.

        Returns:
            Dictionary with workspace statistics
        """
        workspaces = self.db.list_workspaces(limit=1000, offset=0)

        stats = {
            "total_workspaces": len(workspaces),
            "active_workspaces": len([ws for ws in workspaces if ws.get("status") == "active"]),
            "created_workspaces": len([ws for ws in workspaces if ws.get("status") == "created"]),
            "error_workspaces": len([ws for ws in workspaces if ws.get("status") == "error"]),
        }

        return stats

    def _db_to_api_model(self, db_workspace: dict) -> Workspace:
        """Convert database dictionary to API model.

        Args:
            db_workspace: Database workspace dictionary

        Returns:
            API workspace model
        """
        config_data = db_workspace.get("config", {})
        if isinstance(config_data, str):
            config_data = json.loads(config_data)

        # Extract nested config if it exists
        if "config" in config_data:
            workspace_config = config_data["config"]
        else:
            workspace_config = config_data

        config = WorkspaceConfig(**workspace_config)

        return Workspace(
            id=db_workspace["id"],
            config=config,
            last_error=config_data.get("last_error"),
            workspace_path=config_data.get("workspace_path"),
            config_file_path=config_data.get("config_file_path"),
        )

    def _generate_graphrag_config(self, config: WorkspaceConfig, config_file_path: Path) -> None:
        """Generate GraphRAG configuration file.

        Args:
            config: Workspace configuration
            config_file_path: Path to save configuration file
        """
        # Determine provider settings
        if self.settings.is_ollama_provider():
            llm_type = "ollama"
            llm_model = config.llm_model_override or self.settings.ollama_llm_model
            embedding_model = (
                config.embedding_model_override or self.settings.ollama_embedding_model
            )
            api_base = self.settings.ollama_base_url
        else:  # Google Gemini
            llm_type = "google_gemini"
            llm_model = config.llm_model_override or self.settings.gemini_model
            embedding_model = config.embedding_model_override or "models/text-embedding-004"
            api_base = None

        # Generate YAML configuration for GraphRAG
        graphrag_config: dict[str, Any] = {
            "encoding_model": embedding_model,
            "llm": {
                "type": llm_type,
                "model": llm_model,
                "max_tokens": 4000,
                "temperature": 0,
            },
            "parallelization": {
                "stagger": 0.3,
                "num_threads": 4,  # Reduced for small scale
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
                "base_dir": str(Path(config_file_path.parent) / "cache"),
            },
            "storage": {
                "type": "file",
                "base_dir": config.output_path,
            },
            "reporting": {
                "type": "file",
                "base_dir": str(Path(config_file_path.parent) / "reports"),
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
                "enabled": False,  # Disabled for simplicity
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
                "enabled": False,  # Disabled for simplicity
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
                "max_tokens": 8000,  # Reduced for small models
            },
            "global_search": {
                "max_tokens": 8000,  # Reduced for small models
                "data_max_tokens": 8000,
                "map_max_tokens": 1000,
                "reduce_max_tokens": 2000,
                "concurrency": 4,  # Reduced for small scale
            },
        }

        # Add provider-specific settings
        if api_base:
            graphrag_config["llm"]["api_base"] = api_base

        # Write YAML configuration
        import yaml

        with open(config_file_path, "w", encoding="utf-8") as f:
            yaml.dump(graphrag_config, f, default_flow_style=False, indent=2)
