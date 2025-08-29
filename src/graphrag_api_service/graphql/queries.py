# src/graphrag_api_service/graphql/queries.py
# GraphQL query definitions
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL query resolvers for GraphRAG operations."""


import logging
import strawberry
from strawberry.types import Info

from ..config import settings
from ..graph.operations import GraphOperations
from ..system.operations import SystemOperations
from ..workspace.manager import WorkspaceManager
from ..workspace.models import WorkspaceStatus as WorkspaceModelStatus
from .optimization import get_field_selector, get_complexity_analyzer, get_query_cache
from .types import (
    AdvancedQueryResult,
    AnomalyDetectionResult,
    ApplicationInfo,
    ApplicationInterfaces,
    CacheStatistics,
    CentralityMeasures,
    ClusteringResult,
    CommunityDetectionResult,
    Entity,
    EntityConnection,
    EntityEdge,
    GraphEdge,
    GraphNode,
    GraphQLIndexingJobStatus,
    GraphQLIndexingStage,
    GraphStatistics,
    GraphVisualization,
    IndexingJobConnection,
    IndexingJobDetail,
    IndexingJobEdge,
    IndexingJobProgress,
    IndexingJobSummary,
    IndexingStatistics,
    MultiHopQueryInput,
    PageInfo,
    PerformanceMetrics,
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

logger = logging.getLogger(__name__)


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
        """Query entities from the knowledge graph with optimization.

        Args:
            info: GraphQL context information
            name: Optional entity name filter
            type: Optional entity type filter
            first: Number of entities to return
            after: Cursor for pagination

        Returns:
            EntityConnection with entities and pagination info
        """
        # Validate query complexity
        complexity_analyzer = get_complexity_analyzer()
        complexity_analyzer.validate_complexity(info)

        # Get field selector for optimization
        field_selector = get_field_selector()
        query_cache = get_query_cache()

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

        # Optimize query based on selected fields
        base_query = {
            "entity_name": name,
            "entity_type": type,
            "limit": first,
            "offset": offset,
        }
        optimized_query = field_selector.optimize_entity_query(info, base_query)

        # Check cache first
        selected_fields = field_selector.get_selected_fields(info, "Entity")
        cache_key = query_cache.generate_cache_key("entities", optimized_query, selected_fields)

        if not query_cache.is_expired(cache_key):
            cached_result = query_cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for entity query: {cache_key}")
                return cached_result["result"]

        result = await graph_ops.query_entities(
            data_path=settings.graphrag_data_path,
            **optimized_query,
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

        entity_connection = EntityConnection(edges=edges, page_info=page_info, total_count=result["total_count"])

        # Cache the result
        query_cache.set(cache_key, entity_connection, ttl=300)
        logger.debug(f"Cached entity query result: {cache_key}")

        return entity_connection

    @strawberry.field
    async def entity(self, info: Info, id: str) -> Entity | None:
        """Get a specific entity by ID with optimization.

        Args:
            info: GraphQL context information
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        # Validate query complexity
        complexity_analyzer = get_complexity_analyzer()
        complexity_analyzer.validate_complexity(info)

        # Get optimization tools
        field_selector = get_field_selector()
        query_cache = get_query_cache()

        graph_ops: GraphOperations = info.context["graph_operations"]

        if not settings.graphrag_data_path:
            return None

        # Check cache first
        selected_fields = field_selector.get_selected_fields(info, "Entity")
        cache_key = query_cache.generate_cache_key("entity", {"id": id}, selected_fields)

        if not query_cache.is_expired(cache_key):
            cached_result = query_cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for entity query: {cache_key}")
                return cached_result["result"]

        # Optimize query based on selected fields
        base_query = {"entity_name": id, "limit": 1}
        optimized_query = field_selector.optimize_entity_query(info, base_query)

        result = await graph_ops.query_entities(
            data_path=settings.graphrag_data_path,
            **optimized_query,
        )

        if result["entities"]:
            e = result["entities"][0]
            entity = Entity(
                id=e["id"],
                title=e["title"],
                type=e["type"],
                description=e["description"],
                degree=e["degree"],
                community_ids=e.get("community_ids", []),
                text_unit_ids=e.get("text_unit_ids", []),
            )

            # Cache the result
            query_cache.set(cache_key, entity, ttl=600)
            logger.debug(f"Cached entity result: {cache_key}")

            return entity
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

    # Indexing Queries
    @strawberry.field
    async def indexing_jobs(
        self,
        info: Info,
        status: GraphQLIndexingJobStatus | None = None,
        first: int = 50,
        after: str | None = None,
    ) -> IndexingJobConnection:
        """List indexing jobs with optional filtering and pagination.

        Args:
            info: GraphQL context information
            status: Optional status filter
            first: Number of jobs to return
            after: Cursor for pagination

        Returns:
            IndexingJobConnection with jobs and pagination info
        """
        from ..indexing.manager import IndexingManager
        from ..indexing.models import IndexingJobStatus as ModelJobStatus

        indexing_manager: IndexingManager = info.context["indexing_manager"]

        # Convert GraphQL enum to model enum if provided
        model_status = None
        if status:
            model_status = ModelJobStatus(status.value)

        # Get jobs from manager
        job_summaries = indexing_manager.list_jobs(status=model_status, limit=first)

        # Convert to GraphQL types
        edges = []
        for i, job in enumerate(job_summaries):
            edge = IndexingJobEdge(
                node=IndexingJobSummary(
                    id=job.id,
                    workspace_id=job.workspace_id,
                    status=GraphQLIndexingJobStatus(job.status.value),
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    overall_progress=job.overall_progress,
                    current_stage=GraphQLIndexingStage(job.current_stage.value),
                    error_message=job.error_message,
                ),
                cursor=str(i),  # Simple cursor implementation
            )
            edges.append(edge)

        return IndexingJobConnection(
            edges=edges,
            page_info=PageInfo(
                has_next_page=len(edges) == first,
                has_previous_page=after is not None,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            total_count=len(edges),
        )

    @strawberry.field
    async def indexing_job(self, info: Info, id: str) -> IndexingJobDetail | None:
        """Get detailed information about a specific indexing job.

        Args:
            info: GraphQL context information
            id: Job ID

        Returns:
            IndexingJobDetail if found, None otherwise
        """
        from ..indexing.manager import IndexingManager

        indexing_manager: IndexingManager = info.context["indexing_manager"]
        job = indexing_manager.get_job(id)

        if not job:
            return None

        return IndexingJobDetail(
            id=job.id,
            workspace_id=job.workspace_id,
            status=GraphQLIndexingJobStatus(job.status.value),
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            priority=job.priority,
            progress=IndexingJobProgress(
                overall_progress=job.progress.overall_progress,
                current_stage=GraphQLIndexingStage(job.progress.current_stage.value),
                stage_progress=job.progress.stage_progress,
                stage_details=job.progress.stage_details,
            ),
        )

    @strawberry.field
    async def indexing_statistics(self, info: Info) -> IndexingStatistics:
        """Get comprehensive indexing statistics.

        Args:
            info: GraphQL context information

        Returns:
            IndexingStatistics with system metrics
        """
        from ..indexing.manager import IndexingManager

        indexing_manager: IndexingManager = info.context["indexing_manager"]
        stats = indexing_manager.get_indexing_stats()

        return IndexingStatistics(
            total_jobs=stats.total_jobs,
            queued_jobs=stats.queued_jobs,
            running_jobs=stats.running_jobs,
            completed_jobs=stats.completed_jobs,
            failed_jobs=stats.failed_jobs,
            cancelled_jobs=stats.cancelled_jobs,
            avg_completion_time=stats.avg_completion_time,
            success_rate=stats.success_rate,
            recent_jobs=stats.recent_jobs,
            recent_completions=stats.recent_completions,
        )

    # Cache Queries
    @strawberry.field
    async def cache_statistics(self, info: Info) -> CacheStatistics:
        """Get cache statistics.

        Args:
            info: GraphQL context information

        Returns:
            CacheStatistics with cache metrics
        """
        # For now, return basic cache statistics
        # In a real implementation, this would query actual cache systems
        return CacheStatistics(
            total_size_bytes=0,
            total_files=0,
            cache_hit_rate=None,
            last_cleared=None,
            cache_types={
                "graph_cache": {"enabled": True, "size": 0},
                "embedding_cache": {"enabled": True, "size": 0},
                "query_cache": {"enabled": True, "size": 0},
            },
        )

    @strawberry.field
    async def multi_hop_query(
        self, query_input: MultiHopQueryInput, info: Info
    ) -> AdvancedQueryResult:
        """Execute a multi-hop query with path finding and scoring.

        Args:
            query_input: Multi-hop query configuration
            info: GraphQL context information

        Returns:
            AdvancedQueryResult with paths and scoring information
        """
        from ..graph.advanced_query_engine import AdvancedQueryEngine, MultiHopQuery

        if not settings.graphrag_data_path:
            raise Exception("GraphRAG data path not configured")

        # Convert GraphQL input to internal model
        query = MultiHopQuery(
            start_entities=query_input.start_entities,
            target_entities=query_input.target_entities,
            max_hops=query_input.max_hops,
            relationship_types=query_input.relationship_types,
            scoring_algorithm=query_input.scoring_algorithm,
        )

        advanced_engine = AdvancedQueryEngine(settings.graphrag_data_path)
        result = await advanced_engine.multi_hop_query(query)

        # Convert entities and relationships to GraphQL types
        entities = [
            Entity(
                id=entity.get("id", ""),
                title=entity.get("title", ""),
                type=entity.get("type", ""),
                description=entity.get("description", ""),
                degree=entity.get("degree", 0),
                community_ids=entity.get("community_ids", []),
                text_unit_ids=entity.get("text_unit_ids", []),
            )
            for entity in result.entities
        ]

        relationships = [
            Relationship(
                id=rel.get("id", ""),
                source=rel.get("source", ""),
                target=rel.get("target", ""),
                type=rel.get("type", ""),
                description=rel.get("description", ""),
                weight=rel.get("weight", 0.0),
                text_unit_ids=rel.get("text_unit_ids", []),
            )
            for rel in result.relationships
        ]

        from .types import QueryPath

        paths = [
            QueryPath(
                entities=path.entities,
                relationships=path.relationships,
                score=path.score,
                confidence=path.confidence,
                path_length=path.path_length,
            )
            for path in result.paths
        ]

        return AdvancedQueryResult(
            entities=entities,
            relationships=relationships,
            paths=paths,
            total_score=result.total_score,
            execution_time_ms=result.execution_time_ms,
            query_metadata=result.query_metadata,
        )

    @strawberry.field
    async def detect_communities(
        self, algorithm: str = "louvain", resolution: float = 1.0, info: Info | None = None
    ) -> CommunityDetectionResult:
        """Detect communities in the knowledge graph.

        Args:
            algorithm: Community detection algorithm
            resolution: Resolution parameter for community detection
            info: GraphQL context information

        Returns:
            CommunityDetectionResult with detected communities
        """
        from ..graph.analytics import GraphAnalytics

        if not settings.graphrag_data_path:
            raise Exception("GraphRAG data path not configured")

        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.detect_communities(algorithm, resolution)

        from .types import Community

        communities = [
            Community(
                id=community["id"],
                level=0,  # Default level
                title=community.get("type", "Unknown"),
                entity_ids=community["entities"],
                relationship_ids=[],  # Default empty list
            )
            for community in result.communities
        ]

        return CommunityDetectionResult(
            communities=communities,
            modularity_score=result.modularity_score,
            algorithm_used=result.algorithm_used,
            execution_time_ms=result.execution_time_ms,
        )

    @strawberry.field
    async def calculate_centrality(
        self, node_ids: list[str] | None = None, info: Info | None = None
    ) -> list[CentralityMeasures]:
        """Calculate centrality measures for graph nodes.

        Args:
            node_ids: Specific node IDs to analyze
            info: GraphQL context information

        Returns:
            List of centrality measures for each node
        """
        from ..graph.analytics import GraphAnalytics

        if not settings.graphrag_data_path:
            raise Exception("GraphRAG data path not configured")

        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        results = await analytics_engine.calculate_centrality_measures(node_ids)

        return [
            CentralityMeasures(
                node_id=result.node_id,
                degree_centrality=result.degree_centrality,
                betweenness_centrality=result.betweenness_centrality,
                closeness_centrality=result.closeness_centrality,
                eigenvector_centrality=result.eigenvector_centrality,
                pagerank=result.pagerank,
            )
            for result in results
        ]

    @strawberry.field
    async def perform_clustering(
        self, algorithm: str = "kmeans", num_clusters: int | None = None, info: Info | None = None
    ) -> ClusteringResult:
        """Perform graph clustering analysis.

        Args:
            algorithm: Clustering algorithm
            num_clusters: Number of clusters
            info: GraphQL context information

        Returns:
            ClusteringResult with cluster assignments
        """
        from ..graph.analytics import GraphAnalytics

        if not settings.graphrag_data_path:
            raise Exception("GraphRAG data path not configured")

        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.perform_clustering(algorithm, num_clusters)

        from .types import Cluster

        clusters = [
            Cluster(
                cluster_id=cluster["cluster_id"],
                entities=cluster["entities"],
                size=cluster["size"],
                centroid=cluster.get("centroid"),
            )
            for cluster in result.clusters
        ]

        return ClusteringResult(
            clusters=clusters,
            silhouette_score=result.silhouette_score,
            algorithm_used=result.algorithm_used,
            num_clusters=result.num_clusters,
        )

    @strawberry.field
    async def detect_anomalies(
        self, method: str = "isolation_forest", threshold: float = 0.1, info: Info | None = None
    ) -> AnomalyDetectionResult:
        """Detect anomalies in the knowledge graph.

        Args:
            method: Anomaly detection method
            threshold: Anomaly threshold
            info: GraphQL context information

        Returns:
            AnomalyDetectionResult with detected anomalies
        """
        from ..graph.analytics import GraphAnalytics

        if not settings.graphrag_data_path:
            raise Exception("GraphRAG data path not configured")

        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.detect_anomalies(method, threshold)

        # Convert entities and relationships to GraphQL types
        anomalous_entities = [
            Entity(
                id=entity.get("id", ""),
                title=entity.get("title", ""),
                type=entity.get("type", ""),
                description=entity.get("description", ""),
                degree=entity.get("degree", 0),
                community_ids=entity.get("community_ids", []),
                text_unit_ids=entity.get("text_unit_ids", []),
            )
            for entity in result.anomalous_entities
        ]

        anomalous_relationships = [
            Relationship(
                id=rel.get("id", ""),
                source=rel.get("source", ""),
                target=rel.get("target", ""),
                type=rel.get("type", ""),
                description=rel.get("description", ""),
                weight=rel.get("weight", 0.0),
                text_unit_ids=rel.get("text_unit_ids", []),
            )
            for rel in result.anomalous_relationships
        ]

        return AnomalyDetectionResult(
            anomalous_entities=anomalous_entities,
            anomalous_relationships=anomalous_relationships,
            anomaly_scores=result.anomaly_scores,
            detection_method=result.detection_method,
        )
