# src/graphrag_api_service/routes/graph_v2.py
# Graph data API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Graph data API route handlers with proper dependency injection."""

import asyncio
import csv
import json
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..deps import GraphOperationsDep
from ..exceptions import SecurityError, ValidationError, path_traversal_attempt
from ..logging_config import get_logger
from ..security import get_security_logger

logger = get_logger(__name__)
security_logger = get_security_logger()

# Create router for graph endpoints
router = APIRouter(prefix="/api/graph", tags=["Graph"])


def validate_workspace_path(workspace_id: str | None, settings, request: Request = None) -> str:
    """Validate and resolve workspace path to prevent traversal attacks.

    Parameters
    ----------
    workspace_id : str | None
        User-provided workspace identifier
    settings : object
        Application settings containing base paths

    Returns
    -------
    str
        Validated and resolved data path

    Raises
    ------
    HTTPException
        If path validation fails
    """
    # Use default path if no workspace_id provided
    if not workspace_id or workspace_id == "default":
        data_path = settings.graphrag_data_path
        if not data_path:
            raise HTTPException(status_code=400, detail="No default data path configured")
        return data_path

    # Validate workspace_id format (prevent obvious attacks)
    if not workspace_id.replace("-", "").replace("_", "").isalnum():
        # Log security violation
        security_logger.path_traversal_attempt(
            attempted_path=workspace_id,
            request=request
        )
        raise ValidationError(
            message="Invalid workspace ID format",
            field="workspace_id",
            value=workspace_id
        )

    # Construct safe workspace path
    base_workspaces_path = getattr(settings, "base_workspaces_path", "workspaces")

    try:
        # Resolve paths to absolute paths
        base_path = Path(base_workspaces_path).resolve()
        workspace_path = (base_path / workspace_id).resolve()

        # Ensure the resolved path is within the base directory
        if not str(workspace_path).startswith(str(base_path)):
            # Log security violation
            security_logger.path_traversal_attempt(
                attempted_path=workspace_id,
                request=request
            )
            raise SecurityError(
                message="Access to workspace denied - path traversal attempt",
                violation_type="path_traversal",
                details={"attempted_path": workspace_id}
            )

        # Check if workspace directory exists
        if not workspace_path.exists():
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")

        return str(workspace_path)

    except (OSError, ValueError) as e:
        logger.error(f"Path validation error for workspace '{workspace_id}': {e}")
        raise HTTPException(status_code=400, detail="Invalid workspace path") from e


@router.get("/entities")
async def get_entities(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    entity_name: str | None = Query(None),
    entity_type: str | None = Query(None),
    workspace_id: str = Query("default"),
    graph_operations: GraphOperationsDep = None,
) -> dict[str, Any]:
    """Get entities from the knowledge graph.

    Parameters
    ----------
    limit : int, default=50
        Maximum number of entities to return (1-1000)
    offset : int, default=0
        Number of entities to skip
    entity_name : str | None, default=None
        Optional entity name filter
    entity_type : str | None, default=None
        Optional entity type filter
    workspace_id : str, default="default"
        Workspace identifier
    graph_operations : GraphOperationsDep, default=None
        Graph operations service (injected)

    Returns
    -------
    dict[str, Any]
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

        # Get entities from graph operations with security validation
        settings = get_settings()
        data_path = validate_workspace_path(workspace_id, settings, request)

        # Use thread pool for potentially CPU-intensive graph operations
        result = await asyncio.to_thread(
            graph_operations.query_entities,
            data_path=data_path,
            limit=limit,
            offset=offset,
            **filters,
        )

        # Log successful access
        security_logger.workspace_access(
            workspace_id=workspace_id,
            user_id=getattr(request.state, 'user_id', 'anonymous'),
            action="read_entities",
            success=True,
            request=request
        )

        return {
            "entities": result.get("entities", []),
            "total_count": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
            "workspace_id": workspace_id,
        }

    except Exception as e:
        # Log failed access
        security_logger.workspace_access(
            workspace_id=workspace_id,
            user_id=getattr(request.state, 'user_id', 'anonymous'),
            action="read_entities",
            success=False,
            request=request
        )

        logger.error(f"Failed to get entities: {e}")

        # Re-raise service exceptions as-is, convert others to HTTP exceptions
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        else:
            raise HTTPException(status_code=500, detail=str(e))


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
        data_path = validate_workspace_path(workspace_id, settings)

        result = await graph_operations.query_relationships(
            data_path=data_path,
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
        data_path = validate_workspace_path(workspace_id, settings)

        result = await graph_operations.query_communities(data_path=data_path)

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
        data_path = validate_workspace_path(workspace_id, settings)

        result = await graph_operations.get_graph_statistics(data_path=data_path)

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
        data_path = validate_workspace_path(workspace_id, settings)

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


async def _collect_export_data(
    graph_operations: Any,
    data_path: str,
    workspace_id: str,
    format: str,
    include_entities: bool,
    include_relationships: bool,
) -> tuple[dict[str, Any], int, int]:
    """Collect data for export."""
    from datetime import UTC

    export_data: dict[str, Any] = {
        "metadata": {
            "workspace_id": workspace_id,
            "export_date": datetime.now(UTC).isoformat(),
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

    return export_data, entity_count, relationship_count


def _export_to_json(export_data: dict[str, Any], file_path: Path) -> None:
    """Export data to JSON format."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)


def _export_to_csv(export_data: dict[str, Any], export_id: str, temp_dir: Path) -> None:
    """Export data to CSV format."""
    # Export entities to CSV
    if export_data["entities"]:
        entities_file = temp_dir / f"entities_{export_id}.csv"
        with open(entities_file, "w", newline="", encoding="utf-8") as f:
            entities_list = export_data["entities"]
            if entities_list and isinstance(entities_list[0], dict):
                writer = csv.DictWriter(f, fieldnames=entities_list[0].keys())
                writer.writeheader()
                writer.writerows(entities_list)

    # Export relationships to CSV
    if export_data["relationships"]:
        relationships_file = temp_dir / f"relationships_{export_id}.csv"
        with open(relationships_file, "w", newline="", encoding="utf-8") as f:
            relationships_list = export_data["relationships"]
            if relationships_list and isinstance(relationships_list[0], dict):
                writer = csv.DictWriter(f, fieldnames=relationships_list[0].keys())
                writer.writeheader()
                writer.writerows(relationships_list)


def _export_to_graphml(export_data: dict[str, Any], file_path: Path) -> None:
    """Export data to GraphML format."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        f.write('  <graph id="G" edgedefault="directed">\n')

        # Write nodes
        for entity in export_data.get("entities", []):
            if isinstance(entity, dict):
                entity_id = entity.get("id", entity.get("title", ""))
                f.write(f'    <node id="{entity_id}"/>\n')

        # Write edges
        for rel in export_data.get("relationships", []):
            if isinstance(rel, dict):
                f.write(
                    f'    <edge source="{rel.get("source", "")}" target="{rel.get("target", "")}"/>\n'
                )

        f.write("  </graph>\n")
        f.write("</graphml>\n")


def _create_export_response(
    export_id: str,
    format: str,
    file_path: Path,
    entity_count: int,
    relationship_count: int,
    workspace_id: str,
) -> dict[str, Any]:
    """Create export response dictionary."""
    from datetime import UTC

    file_size = file_path.stat().st_size if file_path.exists() else 0
    expires_at = datetime.now(UTC) + timedelta(hours=24)

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
        settings = get_settings()
        data_path = validate_workspace_path(workspace_id, settings)

        # Collect data to export
        export_data, entity_count, relationship_count = await _collect_export_data(
            graph_operations,
            data_path,
            workspace_id,
            format,
            include_entities,
            include_relationships,
        )

        # Create temporary file
        export_id = str(uuid.uuid4())
        temp_dir = Path(tempfile.gettempdir()) / "graphrag_exports"
        temp_dir.mkdir(exist_ok=True)

        # Export based on format
        if format == "json":
            file_path = temp_dir / f"graph_export_{export_id}.json"
            _export_to_json(export_data, file_path)
        elif format == "csv":
            _export_to_csv(export_data, export_id, temp_dir)
            file_path = temp_dir / f"graph_export_{export_id}.csv"
        elif format == "graphml":
            file_path = temp_dir / f"graph_export_{export_id}.graphml"
            _export_to_graphml(export_data, file_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return _create_export_response(
            export_id, format, file_path, entity_count, relationship_count, workspace_id
        )

    except Exception as e:
        logger.error(f"Failed to export graph: {e}")
        return {
            "success": False,
            "error": str(e),
        }
