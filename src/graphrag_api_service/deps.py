# src/graphrag_api_service/deps.py
# FastAPI dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""FastAPI dependency injection for accessing services."""

from typing import Annotated

from fastapi import Depends

from .dependencies import get_service_container


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


def get_cache_manager_dep():
    """Get cache manager for dependency injection."""
    from .performance.cache_manager import get_cache_manager
    import asyncio

    # Get the cache manager instance
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we can't await here
            # Return a placeholder that the route can handle
            return "cache_manager_available"
        else:
            return asyncio.run(get_cache_manager())
    except Exception:
        return None


# Type aliases for dependency injection
WorkspaceManagerDep = Annotated[object, Depends(get_workspace_manager)]
IndexingManagerDep = Annotated[object, Depends(get_indexing_manager)]
GraphOperationsDep = Annotated[object, Depends(get_graph_operations)]
GraphRAGIntegrationDep = Annotated[object, Depends(get_graphrag_integration)]
SystemOperationsDep = Annotated[object, Depends(get_system_operations)]
CacheManagerDep = Annotated[object, Depends(get_cache_manager_dep)]
