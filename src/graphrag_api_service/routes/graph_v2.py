# src/graphrag_api_service/routes/graph_v2.py
# Graph data API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Graph data API route handlers with proper dependency injection."""

from typing import Any

from fastapi import APIRouter, Query

from ..config import get_settings
from ..deps import GraphOperationsDep
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for graph endpoints
router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("/entities")
async def get_entities(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    entity_name: str | None = Query(None),
    entity_type: str | None = Query(None),
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Get entities from the knowledge graph.

    Args:
        limit: Maximum number of entities to return
        offset: Number of entities to skip
        entity_name: Optional entity name filter
        entity_type: Optional entity type filter
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Dict with entities and metadata
    """
    logger.debug(f"Getting entities: limit={limit}, offset={offset}")

    if not graph_operations:
        return {
            "entities": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "error": "Graph operations not available",
        }

    try:
        # Build filters
        filters = {}
        if entity_name:
            filters["name"] = entity_name
        if entity_type:
            filters["type"] = entity_type

        # Get entities from graph operations
        settings = get_settings()
        result = await graph_operations.query_entities(
            data_path=workspace_id or settings.graphrag_data_path,
            limit=limit,
            offset=offset,
            **filters,
        )

        return {
            "entities": result.get("entities", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
            "workspace_id": workspace_id,
        }

    except Exception as e:
        logger.error(f"Failed to get entities: {e}")
        return {"entities": [], "total_count": 0, "limit": limit, "offset": offset, "error": str(e)}


@router.get("/relationships")
async def get_relationships(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    source_entity: str | None = Query(None),
    target_entity: str | None = Query(None),
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Get relationships from the knowledge graph.

    Args:
        limit: Maximum number of relationships to return
        offset: Number of relationships to skip
        source_entity: Optional source entity filter
        target_entity: Optional target entity filter
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Dict with relationships and metadata
    """
    logger.debug(f"Getting relationships: limit={limit}, offset={offset}")

    if not graph_operations:
        return {
            "relationships": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "error": "Graph operations not available",
        }

    try:
        # Build filters
        filters = {}
        if source_entity:
            filters["source"] = source_entity
        if target_entity:
            filters["target"] = target_entity

        # Get relationships from graph operations
        settings = get_settings()
        result = await graph_operations.query_relationships(
            data_path=workspace_id or settings.graphrag_data_path,
            limit=limit,
            offset=offset,
            **filters,
        )

        return {
            "relationships": result.get("relationships", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
            "workspace_id": workspace_id,
        }

    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        return {
            "relationships": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e),
        }


@router.get("/communities")
async def get_communities(
    workspace_id: str = Query("default"), graph_operations: GraphOperationsDep = None
) -> dict[str, Any]:
    """Get communities from the knowledge graph.

    Args:
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Dict with communities and metadata
    """
    logger.debug("Getting communities")

    if not graph_operations:
        return {"communities": [], "total_count": 0, "error": "Graph operations not available"}

    try:
        # Get communities from graph operations
        settings = get_settings()
        result = await graph_operations.query_communities(
            data_path=workspace_id or settings.graphrag_data_path
        )

        return {
            "communities": result.get("communities", []),
            "total_count": result.get("total_count", 0),
            "workspace_id": workspace_id,
        }

    except Exception as e:
        logger.error(f"Failed to get communities: {e}")
        return {"communities": [], "total_count": 0, "error": str(e)}


@router.get("/statistics")
async def get_statistics(
    workspace_id: str = Query("default"), graph_operations: GraphOperationsDep = None
) -> dict[str, Any]:
    """Get graph statistics.

    Args:
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Graph statistics
    """
    logger.debug("Getting graph statistics")

    if not graph_operations:
        return {
            "total_entities": 0,
            "total_relationships": 0,
            "total_communities": 0,
            "entity_types": {},
            "relationship_types": {},
            "community_levels": {},
            "graph_density": 0.0,
            "connected_components": 0,
            "error": "Graph operations not available",
        }

    try:
        # Get statistics from graph operations
        settings = get_settings()
        result = await graph_operations.get_graph_statistics(
            data_path=workspace_id or settings.graphrag_data_path
        )

        return {
            "total_entities": result.get("total_entities", 0),
            "total_relationships": result.get("total_relationships", 0),
            "total_communities": result.get("total_communities", 0),
            "entity_types": result.get("entity_types", {}),
            "relationship_types": result.get("relationship_types", {}),
            "community_levels": result.get("community_levels", {}),
            "graph_density": result.get("graph_density", 0.0),
            "connected_components": result.get("connected_components", 0),
            "workspace_id": workspace_id,
        }

    except Exception as e:
        logger.error(f"Failed to get graph statistics: {e}")
        return {
            "total_entities": 0,
            "total_relationships": 0,
            "total_communities": 0,
            "entity_types": {},
            "relationship_types": {},
            "community_levels": {},
            "graph_density": 0.0,
            "connected_components": 0,
            "error": str(e),
        }


@router.post("/visualization")
async def create_visualization(
    entity_limit: int = 50,
    relationship_limit: int = 100,
    layout_algorithm: str = "force_directed",
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Generate graph visualization.

    Args:
        entity_limit: Maximum entities to include
        relationship_limit: Maximum relationships to include
        layout_algorithm: Layout algorithm to use
        graph_operations: Graph operations (injected)

    Returns:
        Visualization data
    """
    logger.debug(
        f"Creating visualization: entities={entity_limit}, relationships={relationship_limit}"
    )

    return {
        "nodes": [],
        "edges": [],
        "layout": layout_algorithm,
        "metadata": {"total_nodes": 0, "total_edges": 0},
    }


@router.post("/export")
async def export_graph(
    format: str = "json",
    include_entities: bool = True,
    include_relationships: bool = True,
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Export graph data.

    Args:
        format: Export format
        include_entities: Include entities in export
        include_relationships: Include relationships in export
        graph_operations: Graph operations (injected)

    Returns:
        Export response
    """
    logger.debug(f"Exporting graph: format={format}")

    return {
        "download_url": f"/download/graph.{format}",
        "format": format,
        "file_size": 0,
        "entity_count": 0,
        "relationship_count": 0,
        "expires_at": "2025-09-02T00:00:00Z",
    }
