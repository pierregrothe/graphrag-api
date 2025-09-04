# src/graphrag_api_service/workspace/models.py
# GraphRAG workspace data models
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Data models for GraphRAG workspace management."""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class WorkspaceStatus(str, Enum):
    """Status of a GraphRAG workspace."""

    CREATED = "created"
    INDEXING = "indexing"
    INDEXED = "indexed"
    ERROR = "error"
    ARCHIVED = "archived"


class WorkspaceConfig(BaseModel):
    """Configuration for a GraphRAG workspace."""

    # Required fields
    name: str = Field(..., description="Workspace name (unique identifier)")
    description: str = Field(..., description="Description of the workspace")

    # Paths
    data_path: str = Field(..., description="Path to source data directory")
    output_path: str | None = Field(
        None, description="Path to output directory (auto-generated if not provided)"
    )

    # GraphRAG configuration
    chunk_size: int = Field(
        default=1200, ge=300, le=4000, description="Text chunk size for processing"
    )
    chunk_overlap: int = Field(default=100, ge=0, le=500, description="Overlap between chunks")

    # LLM settings (inherit from global if not specified)
    llm_model_override: str | None = Field(
        None, description="Override global LLM model for this workspace"
    )
    embedding_model_override: str | None = Field(
        None, description="Override global embedding model for this workspace"
    )

    # Processing options
    max_entities: int = Field(
        default=1000, ge=10, le=10000, description="Maximum entities to extract"
    )
    max_relationships: int = Field(
        default=2000, ge=20, le=20000, description="Maximum relationships to extract"
    )
    community_levels: int = Field(
        default=4, ge=1, le=6, description="Number of community hierarchy levels"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workspace name format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Workspace name cannot be empty")

        # Remove leading/trailing whitespace
        v = v.strip()

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(
                "Workspace name can only contain letters, numbers, hyphens, and underscores"
            )

        if len(v) > 50:
            raise ValueError("Workspace name cannot exceed 50 characters")

        return v


class Workspace(BaseModel):
    """GraphRAG workspace representation."""

    # Core identification
    id: str = Field(..., description="Unique workspace ID (UUID)")
    config: WorkspaceConfig = Field(..., description="Workspace configuration")

    # Status and metadata
    status: WorkspaceStatus = Field(
        default=WorkspaceStatus.CREATED, description="Current workspace status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )

    # Usage tracking
    last_accessed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last access timestamp"
    )
    access_count: int = Field(default=0, description="Total number of accesses")
    query_count: int = Field(default=0, description="Number of queries executed")
    indexing_count: int = Field(default=0, description="Number of indexing operations")
    size_bytes: int = Field(default=0, description="Workspace size in bytes")
    expires_at: datetime | None = Field(None, description="Expiration timestamp (TTL)")

    # Processing statistics
    files_processed: int = Field(default=0, description="Number of files processed")
    entities_extracted: int = Field(default=0, description="Number of entities extracted")
    relationships_extracted: int = Field(default=0, description="Number of relationships extracted")
    communities_created: int = Field(default=0, description="Number of communities created")

    # Error tracking
    last_error: str | None = Field(None, description="Last error message if status is ERROR")

    # File paths (computed)
    workspace_path: str | None = Field(None, description="Full path to workspace directory")
    config_file_path: str | None = Field(None, description="Path to GraphRAG config file")

    def get_workspace_directory(self, base_workspaces_path: Path) -> Path:
        """Get the full workspace directory path.

        Args:
            base_workspaces_path: Base path where workspaces are stored

        Returns:
            Path to the workspace directory
        """
        return base_workspaces_path / self.config.name

    def get_output_directory(self, base_workspaces_path: Path) -> Path:
        """Get the output directory path for GraphRAG results.

        Args:
            base_workspaces_path: Base path where workspaces are stored

        Returns:
            Path to the output directory
        """
        workspace_dir = self.get_workspace_directory(base_workspaces_path)
        return workspace_dir / "output"

    def get_config_file_path(self, base_workspaces_path: Path) -> Path:
        """Get the GraphRAG configuration file path.

        Args:
            base_workspaces_path: Base path where workspaces are stored

        Returns:
            Path to the GraphRAG configuration file
        """
        workspace_dir = self.get_workspace_directory(base_workspaces_path)
        return workspace_dir / "settings.yaml"

    def is_ready_for_indexing(self) -> bool:
        """Check if workspace is ready for indexing.

        Returns:
            True if workspace can be indexed
        """
        return self.status in [
            WorkspaceStatus.CREATED,
            WorkspaceStatus.INDEXED,
            WorkspaceStatus.ERROR,
        ]

    def is_ready_for_querying(self) -> bool:
        """Check if workspace is ready for querying.

        Returns:
            True if workspace can be queried
        """
        return self.status == WorkspaceStatus.INDEXED

    def update_status(self, new_status: WorkspaceStatus, error_message: str | None = None) -> None:
        """Update workspace status and timestamp.

        Args:
            new_status: New status to set
            error_message: Optional error message if status is ERROR
        """
        self.status = new_status
        self.updated_at = datetime.now(UTC)

        if new_status == WorkspaceStatus.ERROR and error_message:
            self.last_error = error_message
        elif new_status != WorkspaceStatus.ERROR:
            self.last_error = None

    def update_access(self) -> None:
        """Update access tracking when workspace is accessed."""
        self.last_accessed_at = datetime.now(UTC)
        self.access_count += 1

    def update_query_count(self) -> None:
        """Update query count when a query is executed."""
        self.query_count += 1
        self.update_access()

    def update_indexing_count(self) -> None:
        """Update indexing count when indexing operation is performed."""
        self.indexing_count += 1
        self.update_access()

    def update_size(self, size_bytes: int) -> None:
        """Update workspace size in bytes."""
        self.size_bytes = size_bytes

    def set_expiration(self, ttl_hours: int) -> None:
        """Set workspace expiration based on TTL in hours."""
        if ttl_hours > 0:
            from datetime import timedelta

            self.expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        else:
            self.expires_at = None

    def is_expired(self) -> bool:
        """Check if workspace has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_idle(self, max_idle_hours: int) -> bool:
        """Check if workspace has been idle for too long."""
        if max_idle_hours <= 0:
            return False
        from datetime import timedelta

        idle_threshold = datetime.now(UTC) - timedelta(hours=max_idle_hours)
        return self.last_accessed_at < idle_threshold


class WorkspaceSummary(BaseModel):
    """Summary information for a workspace (for listing operations)."""

    id: str = Field(..., description="Unique workspace ID")
    name: str = Field(..., description="Workspace name")
    description: str = Field(..., description="Workspace description")
    status: WorkspaceStatus = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    files_processed: int = Field(..., description="Number of files processed")
    entities_extracted: int = Field(..., description="Number of entities extracted")
    relationships_extracted: int = Field(..., description="Number of relationships extracted")


class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a new workspace."""

    name: str = Field(..., description="Workspace name (must be unique)")
    description: str = Field(..., description="Description of the workspace")
    data_path: str = Field(..., description="Path to source data directory")

    # Optional configuration overrides
    chunk_size: int | None = Field(
        None, ge=300, le=4000, description="Text chunk size for processing"
    )
    chunk_overlap: int | None = Field(None, ge=0, le=500, description="Overlap between chunks")
    llm_model_override: str | None = Field(None, description="Override global LLM model")
    embedding_model_override: str | None = Field(
        None, description="Override global embedding model"
    )
    max_entities: int | None = Field(
        None, ge=10, le=10000, description="Maximum entities to extract"
    )
    max_relationships: int | None = Field(
        None, ge=20, le=20000, description="Maximum relationships to extract"
    )
    community_levels: int | None = Field(
        None, ge=1, le=6, description="Number of community hierarchy levels"
    )


class WorkspaceUpdateRequest(BaseModel):
    """Request model for updating workspace configuration."""

    description: str | None = Field(None, description="Update workspace description")
    data_path: str | None = Field(None, description="Update source data directory path")

    # Configuration updates
    chunk_size: int | None = Field(None, ge=300, le=4000, description="Update chunk size")
    chunk_overlap: int | None = Field(None, ge=0, le=500, description="Update chunk overlap")
    llm_model_override: str | None = Field(None, description="Update LLM model override")
    embedding_model_override: str | None = Field(
        None, description="Update embedding model override"
    )
    max_entities: int | None = Field(None, ge=10, le=10000, description="Update max entities")
    max_relationships: int | None = Field(
        None, ge=20, le=20000, description="Update max relationships"
    )
    community_levels: int | None = Field(None, ge=1, le=6, description="Update community levels")
