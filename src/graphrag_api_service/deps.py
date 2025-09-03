# src/graphrag_api_service/deps.py
# FastAPI dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""FastAPI dependency injection for accessing services."""

from typing import Annotated

from fastapi import Depends

from .dependencies import get_service_container
from .graph.operations import GraphOperations
from .graphrag_integration import GraphRAGIntegration
from .indexing.manager import IndexingManager
from .performance.cache_manager import get_cache_manager
from .system.operations import SystemOperations
from .workspace.manager import WorkspaceManager


def get_workspace_manager():
    """Get workspace manager from service container."""
    container = get_service_container()
    return container.workspace_manager


def get_indexing_manager():
    """Get indexing manager from service container."""
    container = get_service_container()
    return container.indexing_manager


def get_graph_operations():
    """Get graph operations from service container."""
    container = get_service_container()
    return container.graph_operations


def get_graphrag_integration():
    """Get GraphRAG integration from service container."""
    container = get_service_container()
    return container.graphrag_integration


def get_system_operations():
    """Get system operations from service container."""
    container = get_service_container()
    return container.system_operations


async def get_cache_manager_dep():
    """Get cache manager for dependency injection."""
    try:
        # Get cache manager asynchronously
        cache_manager = await get_cache_manager()
        return cache_manager
    except Exception as e:
        # Log the error but don't fail the request
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Cache manager not available: {e}")
        return None


# Type aliases for dependency injection
WorkspaceManagerDep = Annotated[WorkspaceManager | None, Depends(get_workspace_manager)]
IndexingManagerDep = Annotated[IndexingManager | None, Depends(get_indexing_manager)]
GraphOperationsDep = Annotated[GraphOperations | None, Depends(get_graph_operations)]
GraphRAGIntegrationDep = Annotated[GraphRAGIntegration | None, Depends(get_graphrag_integration)]
SystemOperationsDep = Annotated[SystemOperations | None, Depends(get_system_operations)]
CacheManagerDep = Annotated[object | None, Depends(get_cache_manager_dep)]
