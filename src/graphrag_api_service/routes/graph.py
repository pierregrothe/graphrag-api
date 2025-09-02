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
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Generate graph visualization.

    Args:
        entity_limit: Maximum entities to include
        relationship_limit: Maximum relationships to include
        layout_algorithm: Layout algorithm to use
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Visualization data in D3.js compatible format
    """
    logger.debug(
        f"Creating visualization: entities={entity_limit}, relationships={relationship_limit}"
    )

    if not graph_operations:
        return {
            "nodes": [],
            "edges": [],
            "layout": layout_algorithm,
            "metadata": {"total_nodes": 0, "total_edges": 0},
            "error": "Graph operations not available",
        }

    try:
        settings = get_settings()
        data_path = workspace_id or settings.graphrag_data_path

        # Get entities and relationships
        entities_result = await graph_operations.query_entities(
            data_path=data_path,
            limit=entity_limit,
            offset=0,
        )

        relationships_result = await graph_operations.query_relationships(
            data_path=data_path,
            limit=relationship_limit,
            offset=0,
        )

        # Convert to visualization format
        nodes = []
        for i, entity in enumerate(entities_result.get("entities", [])):
            nodes.append(
                {
                    "id": entity.get("id", f"entity_{i}"),
                    "label": entity.get("title", entity.get("name", f"Entity {i}")),
                    "type": entity.get("type", "default"),
                    "size": entity.get("degree", 1) * 10,  # Size based on degree
                    "x": None,  # Will be calculated by layout
                    "y": None,
                    "community": entity.get("community_id"),
                    "description": entity.get("description", ""),
                }
            )

        edges = []
        for _, rel in enumerate(relationships_result.get("relationships", [])):
            edges.append(
                {
                    "source": rel.get("source"),
                    "target": rel.get("target"),
                    "type": rel.get("type", "related"),
                    "weight": rel.get("weight", 1.0),
                    "label": rel.get("description", ""),
                }
            )

        # Apply layout algorithm (simplified - in production use networkx or similar)
        if layout_algorithm == "force_directed":
            # Simple circular layout as placeholder
            import math

            num_nodes = len(nodes)
            if num_nodes > 0:
                angle_step = 2 * math.pi / num_nodes
                radius = min(500, num_nodes * 10)
                for i, node in enumerate(nodes):
                    angle = i * angle_step
                    node["x"] = radius * math.cos(angle)
                    node["y"] = radius * math.sin(angle)

        return {
            "nodes": nodes,
            "edges": edges,
            "layout": layout_algorithm,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "workspace_id": workspace_id,
                "timestamp": "2025-09-02T00:00:00Z",
            },
        }

    except Exception as e:
        logger.error(f"Failed to create visualization: {e}")
        return {
            "nodes": [],
            "edges": [],
            "layout": layout_algorithm,
            "metadata": {"total_nodes": 0, "total_edges": 0},
            "error": str(e),
        }


@router.post("/export")
async def export_graph(
    format: str = Query("json", pattern="^(json|csv|graphml)$"),
    include_entities: bool = True,
    include_relationships: bool = True,
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Export graph data.

    Args:
        format: Export format (json, csv, graphml)
        include_entities: Include entities in export
        include_relationships: Include relationships in export
        workspace_id: Workspace ID
        graph_operations: Graph operations (injected)

    Returns:
        Export response with download information
    """
    logger.debug(f"Exporting graph: format={format}")

    if not graph_operations:
        return {
            "success": False,
            "error": "Graph operations not available",
        }

    try:
        import csv
        import json
        import tempfile
        import uuid
        from datetime import datetime, timedelta
        from pathlib import Path

        settings = get_settings()
        data_path = workspace_id or settings.graphrag_data_path

        # Collect data to export
        export_data = {
            "metadata": {
                "workspace_id": workspace_id,
                "export_date": datetime.utcnow().isoformat(),
                "format": format,
            },
            "entities": [],
            "relationships": [],
        }

        entity_count = 0
        relationship_count = 0

        if include_entities:
            entities_result = await graph_operations.query_entities(
                data_path=data_path,
                limit=10000,  # Export all entities
                offset=0,
            )
            export_data["entities"] = entities_result.get("entities", [])
            entity_count = len(export_data["entities"])

        if include_relationships:
            relationships_result = await graph_operations.query_relationships(
                data_path=data_path,
                limit=10000,  # Export all relationships
                offset=0,
            )
            export_data["relationships"] = relationships_result.get("relationships", [])
            relationship_count = len(export_data["relationships"])

        # Create temporary file
        export_id = str(uuid.uuid4())
        temp_dir = Path(tempfile.gettempdir()) / "graphrag_exports"
        temp_dir.mkdir(exist_ok=True)

        if format == "json":
            file_path = temp_dir / f"graph_export_{export_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)

        elif format == "csv":
            # Export entities to CSV
            if include_entities and export_data["entities"]:
                entities_file = temp_dir / f"entities_{export_id}.csv"
                with open(entities_file, "w", newline="", encoding="utf-8") as f:
                    if export_data["entities"]:
                        writer = csv.DictWriter(f, fieldnames=export_data["entities"][0].keys())
                        writer.writeheader()
                        writer.writerows(export_data["entities"])

            # Export relationships to CSV
            if include_relationships and export_data["relationships"]:
                relationships_file = temp_dir / f"relationships_{export_id}.csv"
                with open(relationships_file, "w", newline="", encoding="utf-8") as f:
                    if export_data["relationships"]:
                        writer = csv.DictWriter(
                            f, fieldnames=export_data["relationships"][0].keys()
                        )
                        writer.writeheader()
                        writer.writerows(export_data["relationships"])

            file_path = temp_dir / f"graph_export_{export_id}.csv"

        elif format == "graphml":
            # Simple GraphML format
            file_path = temp_dir / f"graph_export_{export_id}.graphml"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
                f.write('  <graph id="G" edgedefault="directed">\n')

                # Write nodes
                for entity in export_data.get("entities", []):
                    f.write(f'    <node id="{entity.get("id", "")}"/>\n')

                # Write edges
                for rel in export_data.get("relationships", []):
                    f.write(
                        f'    <edge source="{rel.get("source", "")}" target="{rel.get("target", "")}"/>\n'
                    )

                f.write("  </graph>\n")
                f.write("</graphml>\n")

        # Get file size
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Generate expiry time (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        return {
            "success": True,
            "export_id": export_id,
            "download_url": f"/api/graph/download/{export_id}",
            "format": format,
            "file_size": file_size,
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "workspace_id": workspace_id,
            "expires_at": expires_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to export graph: {e}")
        return {
            "success": False,
            "error": str(e),
        }
