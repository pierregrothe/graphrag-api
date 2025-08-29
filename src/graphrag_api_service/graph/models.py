# src/graphrag_api_service/graph/models.py
# Graph operations data models
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Data models for graph operations and knowledge graph analysis."""

from typing import Any

from pydantic import BaseModel, Field


class EntityQueryRequest(BaseModel):
    """Request model for entity querying."""

    entity_name: str | None = Field(None, description="Specific entity name to search for")
    entity_type: str | None = Field(None, description="Entity type filter")
    limit: int = Field(
        default=50, ge=1, le=1000, description="Maximum number of entities to return"
    )
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class EntityQueryResponse(BaseModel):
    """Response model for entity querying."""

    entities: list[dict[str, Any]] = Field(..., description="List of entities with metadata")
    total_count: int = Field(..., description="Total number of entities matching criteria")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")


class RelationshipQueryRequest(BaseModel):
    """Request model for relationship querying."""

    source_entity: str | None = Field(None, description="Source entity name filter")
    target_entity: str | None = Field(None, description="Target entity name filter")
    relationship_type: str | None = Field(None, description="Relationship type filter")
    limit: int = Field(
        default=50, ge=1, le=1000, description="Maximum number of relationships to return"
    )
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class RelationshipQueryResponse(BaseModel):
    """Response model for relationship querying."""

    relationships: list[dict[str, Any]] = Field(
        ..., description="List of relationships with metadata"
    )
    total_count: int = Field(..., description="Total number of relationships matching criteria")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""

    total_entities: int = Field(..., description="Total number of entities in the graph")
    total_relationships: int = Field(..., description="Total number of relationships in the graph")
    total_communities: int = Field(..., description="Total number of communities in the graph")
    entity_types: dict[str, int] = Field(..., description="Count of entities by type")
    relationship_types: dict[str, int] = Field(..., description="Count of relationships by type")
    community_levels: dict[str, int] = Field(..., description="Count of communities by level")
    graph_density: float = Field(..., description="Graph density metric")
    connected_components: int = Field(..., description="Number of connected components")


class GraphVisualizationRequest(BaseModel):
    """Request model for graph visualization."""

    entity_limit: int = Field(
        default=100, ge=10, le=1000, description="Maximum number of entities to include"
    )
    relationship_limit: int = Field(
        default=200, ge=10, le=2000, description="Maximum number of relationships to include"
    )
    community_level: int | None = Field(
        None, ge=0, le=10, description="Community level to visualize"
    )
    layout_algorithm: str = Field(
        default="force_directed",
        description="Layout algorithm: force_directed, circular, hierarchical",
    )
    include_node_labels: bool = Field(
        default=True, description="Include node labels in visualization"
    )
    include_edge_labels: bool = Field(
        default=False, description="Include edge labels in visualization"
    )


class GraphVisualizationResponse(BaseModel):
    """Response model for graph visualization."""

    nodes: list[dict[str, Any]] = Field(..., description="Node data for visualization")
    edges: list[dict[str, Any]] = Field(..., description="Edge data for visualization")
    layout: str = Field(..., description="Layout algorithm used")
    metadata: dict[str, Any] = Field(..., description="Visualization metadata")


class GraphExportRequest(BaseModel):
    """Request model for graph export."""

    format: str = Field(..., description="Export format: json, gexf, graphml, csv")
    include_entities: bool = Field(default=True, description="Include entities in export")
    include_relationships: bool = Field(default=True, description="Include relationships in export")
    include_communities: bool = Field(default=True, description="Include communities in export")
    entity_limit: int | None = Field(None, ge=1, description="Limit number of entities (optional)")
    relationship_limit: int | None = Field(
        None, ge=1, description="Limit number of relationships (optional)"
    )


class GraphExportResponse(BaseModel):
    """Response model for graph export."""

    download_url: str = Field(..., description="URL to download the exported file")
    format: str = Field(..., description="Export format used")
    file_size: int = Field(..., description="File size in bytes")
    entity_count: int = Field(..., description="Number of entities in export")
    relationship_count: int = Field(..., description="Number of relationships in export")
    expires_at: str = Field(..., description="Expiration timestamp for download URL")
