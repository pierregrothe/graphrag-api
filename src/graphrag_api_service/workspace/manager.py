# src/graphrag_api_service/workspace/manager.py
# GraphRAG workspace management implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""GraphRAG workspace manager for multi-project support and data directory management."""

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..config import Settings
from .models import (
    Workspace,
    WorkspaceConfig,
    WorkspaceCreateRequest,
    WorkspaceStatus,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)


class WorkspaceManager:
    """Manager for GraphRAG workspaces providing multi-project support."""

    def __init__(self, settings: Settings):
        """Initialize workspace manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.base_workspaces_path = Path("workspaces")
        self.workspaces_index_file = self.base_workspaces_path / "workspaces.json"

        # Ensure workspaces directory exists
        self.base_workspaces_path.mkdir(exist_ok=True)

        # Load existing workspaces
        self._workspaces: dict[str, Workspace] = {}
        self._load_workspaces_index()

    def _load_workspaces_index(self) -> None:
        """Load workspaces index from disk."""
        if not self.workspaces_index_file.exists():
            self._save_workspaces_index()
            return

        try:
            with open(self.workspaces_index_file, encoding="utf-8") as f:
                data = json.load(f)

            for workspace_data in data.get("workspaces", []):
                workspace = Workspace(**workspace_data)
                self._workspaces[workspace.id] = workspace

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If index is corrupted, start fresh but log the issue
            print(f"Warning: Corrupted workspaces index, starting fresh: {e}")
            self._workspaces = {}
            self._save_workspaces_index()

    def _save_workspaces_index(self) -> None:
        """Save workspaces index to disk."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "workspaces": [workspace.model_dump() for workspace in self._workspaces.values()],
        }

        with open(self.workspaces_index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def create_workspace(self, request: WorkspaceCreateRequest) -> Workspace:
        """Create a new GraphRAG workspace.

        Args:
            request: Workspace creation request

        Returns:
            Created workspace

        Raises:
            ValueError: If workspace name already exists or data path is invalid
            OSError: If workspace directories cannot be created
        """
        # Check if workspace name already exists
        if any(ws.config.name == request.name for ws in self._workspaces.values()):
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

        # Create workspace
        workspace = Workspace(
            id=workspace_id,
            config=config,
            last_error=None,
            workspace_path=None,
            config_file_path=None,
        )

        # Create workspace directory structure
        workspace_dir = workspace.get_workspace_directory(self.base_workspaces_path)
        output_dir = workspace.get_output_directory(self.base_workspaces_path)

        try:
            workspace_dir.mkdir(parents=True, exist_ok=False)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate GraphRAG configuration file
            self._generate_graphrag_config(workspace)

            # Update workspace paths
            workspace.workspace_path = str(workspace_dir)
            workspace.config_file_path = str(
                workspace.get_config_file_path(self.base_workspaces_path)
            )

            # Add to index and save
            self._workspaces[workspace_id] = workspace
            self._save_workspaces_index()

            return workspace

        except OSError as e:
            # Clean up on failure
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
            raise OSError(f"Failed to create workspace directories: {e}") from e

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace if found, None otherwise
        """
        return self._workspaces.get(workspace_id)

    def get_workspace_by_name(self, name: str) -> Workspace | None:
        """Get workspace by name.

        Args:
            name: Workspace name

        Returns:
            Workspace if found, None otherwise
        """
        for workspace in self._workspaces.values():
            if workspace.config.name == name:
                return workspace
        return None

    def list_workspaces(self) -> list[WorkspaceSummary]:
        """List all workspaces with summary information.

        Returns:
            List of workspace summaries
        """
        summaries = []
        for workspace in self._workspaces.values():
            summary = WorkspaceSummary(
                id=workspace.id,
                name=workspace.config.name,
                description=workspace.config.description,
                status=workspace.status,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                files_processed=workspace.files_processed,
                entities_extracted=workspace.entities_extracted,
                relationships_extracted=workspace.relationships_extracted,
            )
            summaries.append(summary)

        # Sort by creation date (newest first)
        summaries.sort(key=lambda x: x.created_at, reverse=True)
        return summaries

    def update_workspace(self, workspace_id: str, request: WorkspaceUpdateRequest) -> Workspace:
        """Update workspace configuration.

        Args:
            workspace_id: Workspace ID
            request: Update request

        Returns:
            Updated workspace

        Raises:
            ValueError: If workspace not found or update invalid
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Update configuration fields
        if request.description is not None:
            workspace.config.description = request.description

        if request.data_path is not None:
            data_path = Path(request.data_path)
            if not data_path.exists() or not data_path.is_dir():
                raise ValueError(f"Invalid data path: {request.data_path}")
            workspace.config.data_path = str(data_path.resolve())

        if request.chunk_size is not None:
            workspace.config.chunk_size = request.chunk_size

        if request.chunk_overlap is not None:
            workspace.config.chunk_overlap = request.chunk_overlap

        if request.llm_model_override is not None:
            workspace.config.llm_model_override = request.llm_model_override

        if request.embedding_model_override is not None:
            workspace.config.embedding_model_override = request.embedding_model_override

        if request.max_entities is not None:
            workspace.config.max_entities = request.max_entities

        if request.max_relationships is not None:
            workspace.config.max_relationships = request.max_relationships

        if request.community_levels is not None:
            workspace.config.community_levels = request.community_levels

        # Update timestamp
        workspace.updated_at = datetime.now(UTC)

        # Regenerate configuration file if workspace exists
        if workspace.workspace_path and Path(workspace.workspace_path).exists():
            self._generate_graphrag_config(workspace)

        # Save changes
        self._save_workspaces_index()

        return workspace

    def delete_workspace(self, workspace_id: str, remove_files: bool = False) -> bool:
        """Delete workspace.

        Args:
            workspace_id: Workspace ID
            remove_files: Whether to remove workspace files from disk

        Returns:
            True if workspace was deleted, False if not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False

        # Remove files if requested
        if remove_files and workspace.workspace_path:
            workspace_dir = Path(workspace.workspace_path)
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)

        # Remove from index
        del self._workspaces[workspace_id]
        self._save_workspaces_index()

        return True

    def _generate_graphrag_config(self, workspace: Workspace) -> None:
        """Generate GraphRAG configuration file for workspace.

        Args:
            workspace: Workspace to generate config for
        """
        config_path = workspace.get_config_file_path(self.base_workspaces_path)

        # Get LLM models (use overrides if specified, otherwise global settings)
        llm_model = workspace.config.llm_model_override or self._get_current_llm_model()
        embedding_model = (
            workspace.config.embedding_model_override or self._get_current_embedding_model()
        )

        # GraphRAG configuration structure
        graphrag_config = {
            "llm": {
                "api_type": self._get_api_type(),
                "model": llm_model,
                "api_base": self._get_api_base(),
                "api_version": self._get_api_version(),
                "max_tokens": 4000,
                "temperature": 0.1,
                "top_p": 1.0,
                "request_timeout": 180.0,
                "max_retries": 3,
            },
            "embeddings": {
                "api_type": self._get_api_type(),
                "model": embedding_model,
                "api_base": self._get_api_base(),
            },
            "chunks": {
                "size": workspace.config.chunk_size,
                "overlap": workspace.config.chunk_overlap,
                "group_by_columns": ["id"],
                "strategy": {"type": "sentence"},
            },
            "input": {
                "type": "file",
                "file_type": "text",
                "base_dir": workspace.config.data_path,
                "file_encoding": "utf-8",
                "file_pattern": ".*\\.txt$",
            },
            "cache": {
                "type": "file",
                "base_dir": str(
                    workspace.get_output_directory(self.base_workspaces_path) / "cache"
                ),
            },
            "storage": {
                "type": "file",
                "base_dir": str(workspace.get_output_directory(self.base_workspaces_path)),
            },
            "entity_extraction": {
                "strategy": {
                    "type": "graph_intelligence",
                    "extraction_prompt": None,
                    "max_gleanings": 1,
                    "entity_types": ["person", "organization", "location", "event", "concept"],
                    "tuple_delimiter": "<|>",
                    "record_delimiter": "##",
                    "completion_delimiter": "<|COMPLETE|>",
                    "encoding_model": "cl100k_base",
                }
            },
            "summarize_descriptions": {
                "strategy": {
                    "type": "graph_intelligence",
                    "prompt": None,
                    "max_length": 500,
                }
            },
            "community_reports": {
                "strategy": {
                    "type": "graph_intelligence",
                    "prompt": None,
                    "max_length": 2000,
                    "max_input_length": 8000,
                }
            },
            "claim_extraction": {
                "strategy": {
                    "type": "graph_intelligence",
                    "extraction_prompt": None,
                    "max_gleanings": 1,
                    "tuple_delimiter": "<|>",
                    "record_delimiter": "##",
                    "completion_delimiter": "<|COMPLETE|>",
                    "encoding_model": "cl100k_base",
                }
            },
            "cluster_graph": {
                "strategy": {
                    "type": "leiden",
                    "max_cluster_size": 10,
                    "use_lcc": True,
                    "seed": 0xDEADBEEF,
                    "levels": list(range(workspace.config.community_levels)),
                }
            },
            "umap": {
                "enabled": True,
                "n_neighbors": 15,
                "n_components": 2,
                "metric": "cosine",
                "min_dist": 0.1,
                "spread": 1.0,
                "random_state": 42,
            },
            "snapshots": {"graphml": True, "raw_entities": True, "top_level_nodes": True},
            "reporting": {
                "type": "file",
                "base_dir": str(
                    workspace.get_output_directory(self.base_workspaces_path) / "reports"
                ),
            },
        }

        # Write configuration file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(graphrag_config, f, default_flow_style=False, sort_keys=False, indent=2)

    def _get_current_llm_model(self) -> str:
        """Get current LLM model from settings."""
        if self.settings.llm_provider.value == "ollama":
            return self.settings.ollama_llm_model
        else:
            return self.settings.gemini_model

    def _get_current_embedding_model(self) -> str:
        """Get current embedding model from settings."""
        if self.settings.llm_provider.value == "ollama":
            return self.settings.ollama_embedding_model
        else:
            return self.settings.gemini_embedding_model

    def _get_api_type(self) -> str:
        """Get API type for GraphRAG configuration."""
        if self.settings.llm_provider.value == "ollama":
            return "ollama"
        else:
            return "openai_chat"  # GraphRAG uses OpenAI-compatible format for Gemini

    def _get_api_base(self) -> str:
        """Get API base URL for GraphRAG configuration."""
        if self.settings.llm_provider.value == "ollama":
            return self.settings.ollama_base_url
        else:
            return "https://generativelanguage.googleapis.com/v1beta"

    def _get_api_version(self) -> str | None:
        """Get API version for GraphRAG configuration."""
        if self.settings.llm_provider.value == "ollama":
            return None
        else:
            return "v1beta"

    def get_workspace_stats(self) -> dict[str, Any]:
        """Get statistics about all workspaces.

        Returns:
            Dictionary containing workspace statistics
        """
        total_workspaces = len(self._workspaces)
        status_counts = {}

        for status in WorkspaceStatus:
            status_counts[status.value] = 0

        total_files = 0
        total_entities = 0
        total_relationships = 0

        for workspace in self._workspaces.values():
            status_counts[workspace.status.value] += 1
            total_files += workspace.files_processed
            total_entities += workspace.entities_extracted
            total_relationships += workspace.relationships_extracted

        return {
            "total_workspaces": total_workspaces,
            "status_distribution": status_counts,
            "total_files_processed": total_files,
            "total_entities_extracted": total_entities,
            "total_relationships_extracted": total_relationships,
            "base_path": str(self.base_workspaces_path.resolve()),
        }
