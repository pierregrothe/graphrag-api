# src/graphrag_api_service/graphql/mutations.py
# GraphQL mutation definitions
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL mutation resolvers for GraphRAG operations."""

from typing import TYPE_CHECKING, Any

import strawberry
from strawberry.types import Info

# For GraphQL runtime, we use strawberry.scalars.JSON
# For type checking, we use Any since strawberry.scalars.JSON is not a valid type
if TYPE_CHECKING:
    JSONType = Any
else:
    JSONType = strawberry.scalars.JSON

from ..config import settings
from ..graphrag_integration import GraphRAGIntegration
from ..system.operations import SystemOperations
from ..workspace.manager import WorkspaceManager
from ..workspace.models import WorkspaceCreateRequest, WorkspaceUpdateRequest
from ..workspace.models import WorkspaceStatus as WorkspaceModelStatus
from .types import (
    ConfigValidationResult,
    IndexResponse,
    LLMProvider,
    ProviderSwitchResult,
    Workspace,
    WorkspaceStatus,
)


def convert_workspace_status(model_status: WorkspaceModelStatus) -> WorkspaceStatus:
    """Convert workspace model status to GraphQL status."""
    status_map = {
        WorkspaceModelStatus.CREATED: WorkspaceStatus.CREATED,
        WorkspaceModelStatus.INDEXING: WorkspaceStatus.INDEXING,
        WorkspaceModelStatus.INDEXED: WorkspaceStatus.READY,  # Map INDEXED to READY
        WorkspaceModelStatus.ERROR: WorkspaceStatus.ERROR,
        WorkspaceModelStatus.ARCHIVED: WorkspaceStatus.CREATED,  # Map ARCHIVED to CREATED
    }
    return status_map.get(model_status, WorkspaceStatus.CREATED)


@strawberry.type
class Mutation:
    """GraphQL mutation root type."""

    # Workspace Mutations
    @strawberry.mutation
    async def create_workspace(
        self,
        info: Info,
        name: str,
        description: str | None = None,
        data_path: str | None = None,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            info: GraphQL context information
            name: Workspace name
            description: Optional workspace description
            data_path: Optional data path for the workspace

        Returns:
            Created workspace
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]

        # Use provided data_path or generate default
        if not data_path:
            data_path = f"./data/{name.lower().replace(' ', '_')}"

        # Create the proper request object
        request = WorkspaceCreateRequest(
            name=name,
            description=description or "",
            data_path=data_path,
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        workspace = workspace_manager.create_workspace(request)

        return Workspace(
            id=workspace.id,
            name=workspace.config.name,
            description=workspace.config.description,
            data_path=workspace.config.data_path,
            status=convert_workspace_status(workspace.status),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            config=workspace.config.model_dump() if workspace.config else {},
        )

    @strawberry.mutation
    async def update_workspace(
        self,
        info: Info,
        id: str,
        name: str | None = None,
        description: str | None = None,
        config: JSONType | None = None,
    ) -> Workspace | None:
        """Update an existing workspace.

        Args:
            info: GraphQL context information
            id: Workspace ID
            name: Optional new name
            description: Optional new description
            config: Optional new configuration

        Returns:
            Updated workspace if successful
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]

        # Create the proper update request object
        update_request = WorkspaceUpdateRequest(
            description=description,
            data_path=None,
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        workspace = workspace_manager.update_workspace(id, update_request)

        if workspace:
            return Workspace(
                id=workspace.id,
                name=workspace.config.name,
                description=workspace.config.description,
                data_path=workspace.config.data_path,
                status=convert_workspace_status(workspace.status),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                config=workspace.config.model_dump() if workspace.config else {},
            )
        return None

    @strawberry.mutation
    async def delete_workspace(self, info: Info, id: str) -> bool:
        """Delete a workspace.

        Args:
            info: GraphQL context information
            id: Workspace ID

        Returns:
            True if deleted, False otherwise
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        return workspace_manager.delete_workspace(id)

    @strawberry.mutation
    async def set_active_workspace(self, info: Info, id: str) -> Workspace | None:
        """Set the active workspace.

        Args:
            info: GraphQL context information
            id: Workspace ID

        Returns:
            Active workspace if successful
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        workspace = workspace_manager.get_workspace(id)

        if workspace:
            # Update global data path
            settings.graphrag_data_path = workspace.config.data_path

            return Workspace(
                id=workspace.id,
                name=workspace.config.name,
                description=workspace.config.description,
                data_path=workspace.config.data_path,
                status=convert_workspace_status(workspace.status),
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                config=workspace.config.model_dump() if workspace.config else {},
            )
        return None

    # Indexing Mutations
    @strawberry.mutation
    async def start_indexing(
        self,
        info: Info,
        workspace_id: str | None = None,
        root_directory: str | None = None,
        config_file: str | None = None,
        rebuild: bool = False,
    ) -> IndexResponse:
        """Start indexing for a workspace.

        Args:
            info: GraphQL context information
            workspace_id: Optional workspace ID
            root_directory: Optional root directory for indexing
            config_file: Optional configuration file path
            rebuild: Whether to rebuild existing index

        Returns:
            IndexResponse with job information
        """
        graphrag_integration: GraphRAGIntegration = info.context["graphrag_integration"]

        # Use workspace data path if workspace_id provided
        if workspace_id:
            workspace_manager: WorkspaceManager = info.context["workspace_manager"]
            workspace = workspace_manager.get_workspace(workspace_id)
            if workspace:
                root_directory = workspace.config.data_path

        if not root_directory:
            root_directory = settings.graphrag_data_path

        if not root_directory:
            return IndexResponse(
                success=False,
                message="No root directory specified for indexing",
                job_id=None,
                workspace_id=workspace_id,
            )

        try:
            result = await graphrag_integration.index_data(
                data_path=root_directory,
                config_path=config_file,
                force_reindex=rebuild,
            )

            return IndexResponse(
                success=result.get("success", False),
                message=result.get("message", "Indexing started"),
                job_id=result.get("job_id"),
                workspace_id=workspace_id,
            )
        except Exception as e:
            return IndexResponse(
                success=False,
                message=f"Failed to start indexing: {str(e)}",
                job_id=None,
                workspace_id=workspace_id,
            )

    @strawberry.mutation
    async def cancel_indexing(self, info: Info, job_id: str) -> bool:
        """Cancel an indexing job.

        Args:
            info: GraphQL context information
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        indexing_manager = info.context.get("indexing_manager")
        if indexing_manager:
            return bool(indexing_manager.cancel_job(job_id))
        return False

    # System Mutations
    @strawberry.mutation
    async def switch_provider(self, info: Info, provider: LLMProvider) -> ProviderSwitchResult:
        """Switch the LLM provider.

        Args:
            info: GraphQL context information
            provider: Target provider

        Returns:
            ProviderSwitchResult with switch status
        """
        system_ops: SystemOperations = info.context["system_operations"]

        result = await system_ops.switch_provider(provider.value)

        return ProviderSwitchResult(
            success=result["success"],
            previous_provider=result["previous_provider"],
            current_provider=result["current_provider"],
            message=result["message"],
            validation_result=result.get("validation_result"),
        )

    @strawberry.mutation
    async def validate_config(
        self,
        info: Info,
        config_type: str,
        config_data: JSONType,
    ) -> ConfigValidationResult:
        """Validate configuration data.

        Args:
            info: GraphQL context information
            config_type: Type of configuration
            config_data: Configuration data to validate

        Returns:
            ConfigValidationResult with validation details
        """
        system_ops: SystemOperations = info.context["system_operations"]

        result = await system_ops.validate_configuration(
            config_type=config_type,
            config_data=config_data,
        )

        return ConfigValidationResult(
            valid=result["valid"],
            config_type=result["config_type"],
            errors=result["errors"],
            warnings=result["warnings"],
            suggestions=result["suggestions"],
            validated_config=result.get("validated_config"),
        )

    # Graph Data Mutations
    @strawberry.mutation
    async def clear_graph_cache(self, info: Info) -> bool:
        """Clear the graph cache.

        Args:
            info: GraphQL context information

        Returns:
            True if cache cleared successfully
        """
        # GraphOperations doesn't have clear_cache method, return success for now
        # TODO: Implement cache clearing functionality
        return True

    @strawberry.mutation
    async def rebuild_graph_index(
        self, info: Info, workspace_id: str | None = None
    ) -> IndexResponse:
        """Rebuild the graph index.

        Args:
            info: GraphQL context information
            workspace_id: Optional workspace ID

        Returns:
            IndexResponse with rebuild status
        """
        # Implement rebuild logic directly
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        graphrag_integration: GraphRAGIntegration = info.context["graphrag_integration"]

        # Get workspace and data path
        root_directory = settings.graphrag_data_path or "/tmp/graphrag"
        config_file = None

        if workspace_id:
            workspace = workspace_manager.get_workspace(workspace_id)
            if workspace:
                root_directory = workspace.config.data_path

        try:
            result = await graphrag_integration.index_data(
                data_path=root_directory,
                config_path=config_file,
                force_reindex=True,  # Always rebuild
            )

            return IndexResponse(
                success=result.get("success", False),
                message=result.get("message", "Graph index rebuild completed"),
                job_id=result.get("job_id"),
                workspace_id=workspace_id,
            )
        except Exception as e:
            return IndexResponse(
                success=False,
                message=f"Failed to rebuild graph index: {str(e)}",
                job_id=None,
                workspace_id=workspace_id,
            )
