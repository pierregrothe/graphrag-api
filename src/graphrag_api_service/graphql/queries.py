# src/graphrag_api_service/graphql/queries.py
# GraphQL query definitions
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL query resolvers for GraphRAG operations."""


import strawberry
from strawberry.types import Info

from ..config import settings
from ..graph.operations import GraphOperations
from ..system.operations import SystemOperations
from ..workspace.manager import WorkspaceManager
from ..workspace.models import WorkspaceStatus as WorkspaceModelStatus
from .types import (
    ApplicationInfo,
    ApplicationInterfaces,
    Entity,
    EntityConnection,
    EntityEdge,
    GraphEdge,
    GraphNode,
    GraphStatistics,
    GraphVisualization,
    PageInfo,
    QueryResponse,
    QueryType,
    Relationship,
    RelationshipConnection,
    RelationshipEdge,
    SystemHealth,
    SystemStatus,
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
class Query:
    """GraphQL query root type."""

    # Entity Queries
    @strawberry.field
    async def entities(
        self,
        info: Info,
        name: str | None = None,
        type: str | None = None,
        first: int = 50,
        after: str | None = None,
    ) -> EntityConnection:
        """Query entities from the knowledge graph.

        Args:
            info: GraphQL context information
            name: Optional entity name filter
            type: Optional entity type filter
            first: Number of entities to return
            after: Cursor for pagination

        Returns:
            EntityConnection with entities and pagination info
        """
        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return EntityConnection(
                edges=[],
                page_info=PageInfo(
                    has_next_page=False,
                    has_previous_page=False,
                    start_cursor=None,
                    end_cursor=None,
                ),
                total_count=0,
            )

        # Convert cursor to offset
        offset = int(after) if after else 0

        result = await graph_ops.query_entities(
            data_path=settings.graphrag_data_path,
            entity_name=name,
            entity_type=type,
            limit=first,
            offset=offset,
        )

        # Convert to GraphQL types
        edges = [
            EntityEdge(
                node=Entity(
                    id=e["id"],
                    title=e["title"],
                    type=e["type"],
                    description=e["description"],
                    degree=e["degree"],
                    community_ids=e.get("community_ids", []),
                    text_unit_ids=e.get("text_unit_ids", []),
                ),
                cursor=str(offset + i),
            )
            for i, e in enumerate(result["entities"])
        ]

        has_next = offset + first < result["total_count"]
        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if edges else None,
            end_cursor=str(offset + len(edges) - 1) if edges else None,
        )

        return EntityConnection(edges=edges, page_info=page_info, total_count=result["total_count"])

    @strawberry.field
    async def entity(self, info: Info, id: str) -> Entity | None:
        """Get a specific entity by ID.

        Args:
            info: GraphQL context information
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return None

        result = await graph_ops.query_entities(
            data_path=settings.graphrag_data_path,
            entity_name=id,
            limit=1,
        )

        if result["entities"]:
            e = result["entities"][0]
            return Entity(
                id=e["id"],
                title=e["title"],
                type=e["type"],
                description=e["description"],
                degree=e["degree"],
                community_ids=e.get("community_ids", []),
                text_unit_ids=e.get("text_unit_ids", []),
            )
        return None

    # Relationship Queries
    @strawberry.field
    async def relationships(
        self,
        info: Info,
        source: str | None = None,
        target: str | None = None,
        type: str | None = None,
        first: int = 50,
        after: str | None = None,
    ) -> RelationshipConnection:
        """Query relationships from the knowledge graph.

        Args:
            info: GraphQL context information
            source: Optional source entity filter
            target: Optional target entity filter
            type: Optional relationship type filter
            first: Number of relationships to return
            after: Cursor for pagination

        Returns:
            RelationshipConnection with relationships and pagination info
        """
        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return RelationshipConnection(
                edges=[],
                page_info=PageInfo(
                    has_next_page=False,
                    has_previous_page=False,
                    start_cursor=None,
                    end_cursor=None,
                ),
                total_count=0,
            )

        offset = int(after) if after else 0

        result = await graph_ops.query_relationships(
            data_path=settings.graphrag_data_path,
            source_entity=source,
            target_entity=target,
            relationship_type=type,
            limit=first,
            offset=offset,
        )

        edges = [
            RelationshipEdge(
                node=Relationship(
                    id=r["id"],
                    source=r["source"],
                    target=r["target"],
                    type=r["type"],
                    description=r["description"],
                    weight=r.get("weight", 0.0),
                    text_unit_ids=r.get("text_unit_ids", []),
                ),
                cursor=str(offset + i),
            )
            for i, r in enumerate(result["relationships"])
        ]

        has_next = offset + first < result["total_count"]
        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=offset > 0,
            start_cursor=str(offset) if edges else None,
            end_cursor=str(offset + len(edges) - 1) if edges else None,
        )

        return RelationshipConnection(
            edges=edges, page_info=page_info, total_count=result["total_count"]
        )

    # Graph Statistics
    @strawberry.field
    async def graph_statistics(self, info: Info) -> GraphStatistics | None:
        """Get comprehensive statistics about the knowledge graph.

        Args:
            info: GraphQL context information

        Returns:
            GraphStatistics if available, None otherwise
        """
        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return None

        try:
            stats = await graph_ops.get_graph_statistics(settings.graphrag_data_path)
            return GraphStatistics(
                total_entities=stats["total_entities"],
                total_relationships=stats["total_relationships"],
                total_communities=stats["total_communities"],
                entity_types=stats["entity_types"],
                relationship_types=stats["relationship_types"],
                community_levels=stats["community_levels"],
                graph_density=stats["graph_density"],
                connected_components=stats["connected_components"],
            )
        except Exception:
            return None

    # Workspace Queries
    @strawberry.field
    async def workspaces(self, info: Info) -> list[Workspace]:
        """List all workspaces.

        Args:
            info: GraphQL context information

        Returns:
            List of workspaces
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        workspaces = workspace_manager.list_workspaces()

        return [
            Workspace(
                id=w.id,
                name=w.name,
                description=w.description,
                data_path="",  # WorkspaceSummary doesn't have data_path
                status=convert_workspace_status(w.status),
                created_at=w.created_at,
                updated_at=w.updated_at,
                config={},  # WorkspaceSummary doesn't have config
            )
            for w in workspaces
        ]

    @strawberry.field
    async def workspace(self, info: Info, id: str) -> Workspace | None:
        """Get a specific workspace by ID.

        Args:
            info: GraphQL context information
            id: Workspace ID

        Returns:
            Workspace if found, None otherwise
        """
        workspace_manager: WorkspaceManager = info.context["workspace_manager"]
        w = workspace_manager.get_workspace(id)

        if w:
            return Workspace(
                id=w.id,
                name=w.config.name,
                description=w.config.description,
                data_path=w.config.data_path,
                status=convert_workspace_status(w.status),
                created_at=w.created_at,
                updated_at=w.updated_at,
                config=w.config.model_dump() if w.config else {},
            )
        return None

    # System Queries
    @strawberry.field
    async def system_health(self, info: Info) -> SystemHealth:
        """Get comprehensive system health status.

        Args:
            info: GraphQL context information

        Returns:
            SystemHealth with detailed health information
        """
        system_ops: SystemOperations = info.context["system_operations"]
        health = await system_ops.get_advanced_health()

        return SystemHealth(
            status=health["status"],
            timestamp=health["timestamp"],
            components=health.get("components", {}),
            provider=health.get("provider", {}),
            graphrag=health.get("graphrag", {}),
            workspaces=health.get("workspaces", {}),
            graph_data=health.get("graph_data", {}),
            system_resources=health.get("system_resources", {}),
        )

    @strawberry.field
    async def system_status(self, info: Info) -> SystemStatus:
        """Get enhanced system status with metrics.

        Args:
            info: GraphQL context information

        Returns:
            SystemStatus with comprehensive status information
        """
        system_ops: SystemOperations = info.context["system_operations"]
        status = await system_ops.get_enhanced_status()

        return SystemStatus(
            version=status["version"],
            environment=status["environment"],
            uptime_seconds=status["uptime_seconds"],
            provider_info=status.get("provider_info", {}),
            graph_metrics=status.get("graph_metrics", {}),
            indexing_metrics=status.get("indexing_metrics", {}),
            query_metrics=status.get("query_metrics", {}),
            workspace_metrics=status.get("workspace_metrics", {}),
            recent_operations=status.get("recent_operations", []),
        )

    # Application Info Query
    @strawberry.field
    async def application_info(self, info: Info) -> ApplicationInfo:
        """Get application information and configuration.

        Args:
            info: GraphQL context information

        Returns:
            ApplicationInfo containing application information
        """
        return ApplicationInfo(
            name=settings.app_name,
            version=settings.app_version,
            status="healthy",
            interfaces=ApplicationInterfaces(
                rest_api="/api",
                graphql="/graphql/playground",
                documentation={
                    "swagger_ui": "/docs",
                    "redoc": "/redoc",
                    "openapi_json": "/openapi.json",
                },
            ),
            endpoints={
                "health": "/api/health",
                "info": "/api/info",
                "status": "/api/status",
                "query": "/api/query",
                "index": "/api/index",
                "workspaces": "/api/workspaces",
                "indexing_jobs": "/api/indexing/jobs",
                "indexing_stats": "/api/indexing/stats",
            },
        )

    # GraphRAG Query
    @strawberry.field
    async def graphrag_query(
        self, info: Info, query: str, query_type: QueryType = QueryType.LOCAL
    ) -> QueryResponse | None:
        """Execute a GraphRAG query.

        Args:
            info: GraphQL context information
            query: The query text
            query_type: Type of query (LOCAL or GLOBAL)

        Returns:
            QueryResponse if successful, None otherwise
        """
        graphrag_integration = info.context.get("graphrag_integration")

        if not graphrag_integration or not settings.graphrag_data_path:
            return None

        try:
            result = await graphrag_integration.query(
                query_text=query,
                query_type=query_type.value,
                data_path=settings.graphrag_data_path,
            )

            return QueryResponse(
                query=query,
                response=result.get("response", ""),
                context=result.get("context"),
                query_type=query_type,
                processing_time=result.get("processing_time", 0.0),
                entity_count=result.get("entity_count"),
                relationship_count=result.get("relationship_count"),
                token_count=result.get("token_count"),
            )
        except Exception:
            return None

    # Visualization
    @strawberry.field
    async def graph_visualization(
        self,
        info: Info,
        entity_limit: int = 100,
        relationship_limit: int = 200,
        layout: str = "force_directed",
    ) -> GraphVisualization | None:
        """Generate graph visualization data.

        Args:
            info: GraphQL context information
            entity_limit: Maximum number of entities
            relationship_limit: Maximum number of relationships
            layout: Layout algorithm

        Returns:
            GraphVisualization if available, None otherwise
        """
        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return None

        try:
            viz = await graph_ops.generate_visualization(
                data_path=settings.graphrag_data_path,
                entity_limit=entity_limit,
                relationship_limit=relationship_limit,
                layout_algorithm=layout,
            )

            nodes = [
                GraphNode(
                    id=n["id"],
                    label=n["label"],
                    type=n["type"],
                    size=n["size"],
                    community=n.get("community"),
                    description=n.get("description", ""),
                )
                for n in viz["nodes"]
            ]

            edges = [
                GraphEdge(
                    source=e["source"],
                    target=e["target"],
                    type=e["type"],
                    weight=e.get("weight", 1.0),
                    label=e.get("label"),
                )
                for e in viz["edges"]
            ]

            return GraphVisualization(
                nodes=nodes,
                edges=edges,
                layout=viz["layout"],
                metadata=viz.get("metadata", {}),
            )
        except Exception:
            return None
