# src/graphrag_api_service/routes/graphrag_v2.py
# GraphRAG API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""GraphRAG API route handlers with proper dependency injection."""

from typing import Any

from fastapi import APIRouter

from ..deps import GraphRAGIntegrationDep, WorkspaceManagerDep
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for GraphRAG endpoints
router = APIRouter(prefix="/api", tags=["GraphRAG"])


@router.post("/query")
async def query_graphrag(
    query: str,
    query_type: str = "local",
    workspace_id: str = "default",
    graphrag_integration: GraphRAGIntegrationDep = None,
    workspace_manager: WorkspaceManagerDep = None,
) -> dict[str, Any]:
    """Execute a GraphRAG query.

    Args:
        query: The query to execute
        query_type: Type of query (local or global)
        workspace_id: Workspace ID
        graphrag_integration: GraphRAG integration (injected)
        workspace_manager: Workspace manager (injected)

    Returns:
        Query response
    """
    logger.info(f"Executing {query_type} query in workspace {workspace_id}")

    # Check if GraphRAG integration is available
    if not graphrag_integration:
        return {
            "query": query,
            "response": "GraphRAG integration not available",
            "context": None,
            "query_type": query_type.upper(),
            "processing_time": 0.0,
            "entity_count": 0,
            "relationship_count": 0,
            "token_count": 0,
            "error": "GraphRAG integration not configured",
        }

    try:
        # Get workspace to determine data path
        workspace = await workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return {
                "query": query,
                "response": f"Workspace '{workspace_id}' not found",
                "context": None,
                "query_type": query_type.upper(),
                "processing_time": 0.0,
                "entity_count": 0,
                "relationship_count": 0,
                "token_count": 0,
                "error": f"Workspace '{workspace_id}' not found",
            }

        # Determine data path from workspace
        data_path = workspace.get_output_directory_path()
        if not data_path or not data_path.exists():
            return {
                "query": query,
                "response": "Workspace data not indexed yet",
                "context": None,
                "query_type": query_type.upper(),
                "processing_time": 0.0,
                "entity_count": 0,
                "relationship_count": 0,
                "token_count": 0,
                "error": "Workspace data not indexed",
            }

        # Execute query based on type
        if query_type.lower() == "global":
            result = await graphrag_integration.query_global(
                query=query, data_path=str(data_path), workspace_id=workspace_id
            )
        else:
            result = await graphrag_integration.query_local(
                query=query, data_path=str(data_path), workspace_id=workspace_id
            )

        return {
            "query": query,
            "response": result.get("answer", ""),
            "context": result.get("context"),
            "query_type": query_type.upper(),
            "processing_time": result.get("processing_time", 0.0),
            "entity_count": result.get("entity_count", 0),
            "relationship_count": result.get("relationship_count", 0),
            "token_count": result.get("tokens_used", 0),
        }

    except Exception as e:
        logger.error(f"GraphRAG query failed: {e}")
        return {
            "query": query,
            "response": f"Query failed: {str(e)}",
            "context": None,
            "query_type": query_type.upper(),
            "processing_time": 0.0,
            "entity_count": 0,
            "relationship_count": 0,
            "token_count": 0,
            "error": str(e),
        }


@router.post("/index")
async def index_data(
    workspace_id: str = "default",
    force_reindex: bool = False,
    graphrag_integration: GraphRAGIntegrationDep = None,
    workspace_manager: WorkspaceManagerDep = None,
) -> dict[str, Any]:
    """Start indexing for a workspace.

    Args:
        workspace_id: Workspace ID
        force_reindex: Whether to force reindexing
        graphrag_integration: GraphRAG integration (injected)
        workspace_manager: Workspace manager (injected)

    Returns:
        Indexing job information
    """
    logger.info(f"Starting indexing for workspace {workspace_id}")

    # Check if GraphRAG integration is available
    if not graphrag_integration:
        return {
            "success": False,
            "message": "GraphRAG integration not available",
            "job_id": None,
            "workspace_id": workspace_id,
            "error": "GraphRAG integration not configured",
        }

    try:
        # Get workspace
        workspace = await workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return {
                "success": False,
                "message": f"Workspace '{workspace_id}' not found",
                "job_id": None,
                "workspace_id": workspace_id,
                "error": f"Workspace '{workspace_id}' not found",
            }

        # Get data and config paths from workspace
        data_path = workspace.config.data_path
        config_path = workspace.config_file_path

        # Start indexing
        result = await graphrag_integration.index_data(
            data_path=data_path,
            config_path=config_path,
            force_reindex=force_reindex,
            workspace_id=workspace_id,
        )

        return {
            "success": True,
            "message": result.get("message", "Indexing started successfully"),
            "job_id": result.get("job_id", f"job_{workspace_id}"),
            "workspace_id": workspace_id,
            "files_processed": result.get("files_processed", 0),
            "entities_extracted": result.get("entities_extracted", 0),
            "relationships_extracted": result.get("relationships_extracted", 0),
            "status": result.get("status", "completed"),
        }

    except Exception as e:
        logger.error(f"Indexing failed for workspace {workspace_id}: {e}")
        return {
            "success": False,
            "message": f"Indexing failed: {str(e)}",
            "job_id": None,
            "workspace_id": workspace_id,
            "error": str(e),
        }


@router.get("/status")
async def get_status(
    workspace_id: str = "default",
    workspace_manager: WorkspaceManagerDep = None,
) -> dict[str, Any]:
    """Get GraphRAG indexing status.

    Args:
        workspace_id: Workspace ID to check status for
        workspace_manager: Workspace manager (injected)

    Returns:
        Status information
    """
    try:
        if workspace_manager:
            # Get workspace-specific status
            workspace = await workspace_manager.get_workspace(workspace_id)
            if workspace:
                return {
                    "workspace_id": workspace_id,
                    "status": (
                        workspace.status.value
                        if hasattr(workspace.status, "value")
                        else str(workspace.status)
                    ),
                    "indexing_jobs": [],  # Job tracking will be implemented in Phase 3
                    "last_indexed": (
                        workspace.updated_at.isoformat() if workspace.updated_at else None
                    ),
                    "files_processed": workspace.files_processed,
                    "entities_extracted": workspace.entities_extracted,
                    "relationships_extracted": workspace.relationships_extracted,
                    "data_path": workspace.config.data_path,
                    "output_path": workspace.get_output_directory_path(),
                }
            else:
                return {
                    "workspace_id": workspace_id,
                    "status": "not_found",
                    "indexing_jobs": [],
                    "error": f"Workspace '{workspace_id}' not found",
                }
        else:
            # Fallback status
            return {
                "workspace_id": workspace_id,
                "status": "ready",
                "indexing_jobs": [],
                "message": "Workspace manager not available",
            }

    except Exception as e:
        logger.error(f"Failed to get status for workspace {workspace_id}: {e}")
        return {
            "workspace_id": workspace_id,
            "status": "error",
            "indexing_jobs": [],
            "error": str(e),
        }
