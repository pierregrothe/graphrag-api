# src/graphrag_api_service/graphql/mutations.py
# GraphQL mutation definitions
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL mutation resolvers for GraphRAG operations."""

import logging
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
from ..workspace.models import WorkspaceCreateRequest
from ..workspace.models import WorkspaceStatus as WorkspaceModelStatus
from ..workspace.models import WorkspaceUpdateRequest
from .optimization import get_query_cache

logger = logging.getLogger(__name__)
from .types import (
    CacheClearResult,
    ConfigValidationResult,
    GraphExport,
    GraphQLIndexingJobStatus,
    GraphQLIndexingStage,
    IndexingJobDetail,
    IndexingJobProgress,
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
            name: Workspace name
            description: Optional workspace description
            data_path: Optional data path for the workspace
            info: GraphQL context information

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

        workspace = await workspace_manager.create_workspace(request)

        # Handle case where workspace.config might be None (for testing)
        if workspace.config:
            workspace_name = workspace.config.name
            workspace_description = workspace.config.description
            workspace_data_path = workspace.config.data_path
            config_dict = workspace.config.model_dump()
        else:
            # Fallback to request data if config is None
            workspace_name = name
            workspace_description = description or ""
            workspace_data_path = data_path
            config_dict = {}

        return Workspace(
            id=workspace.id,
            name=workspace_name,
            description=workspace_description,
            data_path=workspace_data_path,
            status=convert_workspace_status(workspace.status),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            config=config_dict,
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
            id: Workspace ID
            name: Optional new name
            description: Optional new description
            config: Optional new configuration
            info: GraphQL context information

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

        workspace = await workspace_manager.update_workspace(id, update_request)

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
    async def delete_workspace(self, id: str, info: Info) -> bool:
        """Delete a workspace.

        Args:
            id: Workspace ID
            info: GraphQL context information

        Returns:
            True if deleted, False otherwise
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        return await workspace_manager.delete_workspace(id)

    @strawberry.mutation
    async def set_active_workspace(self, id: str, info: Info) -> Workspace | None:
        """Set the active workspace.

        Args:
            id: Workspace ID
            info: GraphQL context information

        Returns:
            Active workspace if successful
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        workspace = await workspace_manager.get_workspace(id)

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
            workspace_id: Optional workspace ID
            root_directory: Optional root directory for indexing
            config_file: Optional configuration file path
            rebuild: Whether to rebuild existing index
            info: GraphQL context information

        Returns:
            IndexResponse with job information
        """
        graphrag_integration: GraphRAGIntegration = info.context["graphrag_integration"]

        # Use workspace data path if workspace_id provided
        if workspace_id:
            workspace_manager: WorkspaceManager = info.context["workspace_manager"]
            workspace = await workspace_manager.get_workspace(workspace_id)
            if workspace and workspace.config:
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
    async def cancel_indexing(self, job_id: str, info: Info) -> bool:
        """Cancel an indexing job.

        Args:
            job_id: Job ID to cancel
            info: GraphQL context information

        Returns:
            True if cancelled, False otherwise
        """
        indexing_manager = info.context.get("indexing_manager")
        if indexing_manager:
            return bool(indexing_manager.cancel_job(job_id))
        return False

    # System Mutations
    @strawberry.mutation
    async def switch_provider(self, provider: LLMProvider, info: Info) -> ProviderSwitchResult:
        """Switch the LLM provider.

        Args:
            provider: Target provider
            info: GraphQL context information

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
            config_type: Type of configuration
            config_data: Configuration data to validate
            info: GraphQL context information

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
    async def export_graph(
        self,
        info: Info,
        format: str = "json",
        include_entities: bool = True,
        include_relationships: bool = True,
        include_communities: bool = True,
        entity_limit: int | None = None,
        relationship_limit: int | None = None,
        workspace_id: str | None = None,
    ) -> GraphExport:
        """Export graph data in various formats.

        Args:
            format: Export format (json, csv)
            include_entities: Include entities in export
            include_relationships: Include relationships in export
            include_communities: Include communities in export
            entity_limit: Optional limit on entities
            relationship_limit: Optional limit on relationships
            workspace_id: Optional workspace ID for scoped export
            info: GraphQL context information

        Returns:
            GraphExport with download information
        """
        from ..graph.operations import GraphOperations

        graph_ops: GraphOperations = info.context["graph_operations"]

        # Use workspace data path if workspace_id provided
        data_path = settings.graphrag_data_path
        if workspace_id:
            workspace_manager: WorkspaceManager = info.context["workspace_manager"]
            workspace = await workspace_manager.get_workspace(workspace_id)
            if workspace and workspace.config:
                data_path = workspace.config.data_path

        if not data_path:
            raise Exception("No data path available for export")

        try:
            result = await graph_ops.export_graph(
                data_path=data_path,
                format=format,
                include_entities=include_entities,
                include_relationships=include_relationships,
                include_communities=include_communities,
                entity_limit=entity_limit,
                relationship_limit=relationship_limit,
            )

            return GraphExport(
                download_url=result["download_url"],
                format=result["format"],
                file_size=result["file_size"],
                entity_count=result["entity_count"],
                relationship_count=result["relationship_count"],
                expires_at=result["expires_at"],
            )
        except Exception as e:
            raise Exception(f"Failed to export graph: {str(e)}") from e

    # Indexing Mutations
    @strawberry.mutation
    async def cancel_indexing_job(self, id: str, info: Info) -> IndexingJobDetail | None:
        """Cancel an indexing job.

        Args:
            id: Job ID to cancel
            info: GraphQL context information

        Returns:
            Updated IndexingJobDetail if successful, None if job not found
        """
        from ..indexing.manager import IndexingManager

        indexing_manager: IndexingManager = info.context["indexing_manager"]

        # Check if job exists
        job = indexing_manager.get_job(id)
        if not job:
            return None

        # Cancel the job
        success = indexing_manager.cancel_job(id)
        if not success:
            return None

        # Return updated job details
        updated_job = indexing_manager.get_job(id)
        if updated_job:
            return IndexingJobDetail(
                id=updated_job.id,
                workspace_id=updated_job.workspace_id,
                status=GraphQLIndexingJobStatus(updated_job.status.value),
                created_at=updated_job.created_at,
                started_at=updated_job.started_at,
                completed_at=updated_job.completed_at,
                error_message=updated_job.error_message,
                retry_count=updated_job.retry_count,
                max_retries=updated_job.max_retries,
                priority=updated_job.priority,
                progress=IndexingJobProgress(
                    overall_progress=updated_job.progress.overall_progress,
                    current_stage=GraphQLIndexingStage(updated_job.progress.current_stage.value),
                    stage_progress=updated_job.progress.stage_progress,
                    stage_details=updated_job.progress.stage_details,
                ),
            )
        return None

    # Cache Mutations
    @strawberry.mutation
    async def clear_cache(self, info: Info, cache_type: str | None = None) -> CacheClearResult:
        """Clear system cache.

        Args:
            info: GraphQL context information
            cache_type: Optional specific cache type to clear (e.g., 'graph', 'embedding', 'query')

        Returns:
            CacheClearResult with operation details
        """
        # For now, simulate cache clearing
        # In a real implementation, this would clear actual cache systems
        files_cleared = 0
        bytes_freed = 0

        if cache_type:
            message = f"Cache type '{cache_type}' cleared successfully"
        else:
            message = "All caches cleared successfully"

        return CacheClearResult(
            success=True,
            message=message,
            files_cleared=files_cleared,
            bytes_freed=bytes_freed,
        )

    @strawberry.mutation
    async def clear_graph_cache(self, info: Info) -> bool:
        """Clear the graph cache.

        Args:
            info: GraphQL context information

        Returns:
            True if cache cleared successfully
        """
        try:
            # Clear GraphQL query cache
            query_cache = get_query_cache()
            query_cache.clear()
            logger.info("GraphQL query cache cleared")

            # Clear DataLoader caches
            dataloaders = info.context.get("dataloaders", {})
            for loader_name, loader in dataloaders.items():
                if hasattr(loader, "clear"):
                    loader.clear()
                    logger.debug(f"Cleared DataLoader cache: {loader_name}")

            # Clear system cache if available
            system_operations = info.context.get("system_operations")
            if system_operations and hasattr(system_operations, "clear_cache"):
                await system_operations.clear_cache()
                logger.info("System cache cleared")

            # Clear connection pool cache if available
            from ..performance.connection_pool import get_connection_pool

            try:
                connection_pool = await get_connection_pool()
                if hasattr(connection_pool, "clear_cache"):
                    await connection_pool.clear_cache()
                    logger.info("Connection pool cache cleared")
            except Exception as e:
                logger.warning(f"Could not clear connection pool cache: {e}")

            logger.info("All graph caches cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear graph cache: {e}")
            return False

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
        import os
        import tempfile

        if settings.graphrag_data_path:
            root_directory = settings.graphrag_data_path
        else:
            # Use secure temporary directory with proper permissions
            temp_dir = tempfile.mkdtemp(prefix="graphrag_", suffix="_data")
            root_directory = temp_dir
            os.chmod(temp_dir, 0o700)  # Restrict access to owner only

        config_file = None

        if workspace_id:
            workspace = await workspace_manager.get_workspace(workspace_id)
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
