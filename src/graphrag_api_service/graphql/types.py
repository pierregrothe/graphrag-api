# src/graphrag_api_service/graphql/types.py
# GraphQL type definitions for GraphRAG
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL type definitions for GraphRAG entities and operations."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import strawberry

# For GraphQL runtime, we use strawberry.scalars.JSON
# For type checking, we use Any since strawberry.scalars.JSON is not a valid type
if TYPE_CHECKING:
    JSONType = Any
else:
    JSONType = strawberry.scalars.JSON


# Enums
@strawberry.enum
class WorkspaceStatus(Enum):
    """Workspace status enumeration."""

    CREATED = "created"
    READY = "ready"
    INDEXING = "indexing"
    ERROR = "error"


@strawberry.enum
class GraphQLIndexingJobStatus(Enum):
    """GraphQL indexing job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@strawberry.enum
class GraphQLIndexingStage(Enum):
    """GraphQL indexing stage enumeration."""

    INITIALIZATION = "initialization"
    TEXT_EXTRACTION = "text_extraction"
    CHUNKING = "chunking"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    COMMUNITY_DETECTION = "community_detection"
    EMBEDDING_GENERATION = "embedding_generation"
    FINALIZATION = "finalization"


@strawberry.enum
class IndexingJobStatus(Enum):
    """Indexing job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@strawberry.enum
class QueryType(Enum):
    """GraphRAG query type enumeration."""

    LOCAL = "local"
    GLOBAL = "global"


@strawberry.enum
class LLMProvider(Enum):
    """LLM provider enumeration."""

    OLLAMA = "ollama"
    GOOGLE_GEMINI = "google_gemini"


# Entity Types
@strawberry.type
class Entity:
    """GraphQL type for knowledge graph entities."""

    id: str
    title: str
    type: str
    description: str
    degree: int
    community_ids: list[str]
    text_unit_ids: list[str]


@strawberry.type
class Relationship:
    """GraphQL type for entity relationships."""

    id: str
    source: str
    target: str
    type: str
    description: str
    weight: float
    text_unit_ids: list[str]


@strawberry.type
class Community:
    """GraphQL type for graph communities."""

    id: str
    level: int
    title: str
    entity_ids: list[str]
    relationship_ids: list[str]


@strawberry.type
class GraphStatistics:
    """GraphQL type for graph statistics."""

    total_entities: int
    total_relationships: int
    total_communities: int
    entity_types: JSONType
    relationship_types: JSONType
    community_levels: JSONType
    graph_density: float
    connected_components: int


# Indexing Types
@strawberry.type
class IndexingJobProgress:
    """GraphQL type for indexing job progress."""

    overall_progress: float
    current_stage: GraphQLIndexingStage
    stage_progress: float
    stage_details: JSONType


@strawberry.type
class IndexingJobSummary:
    """GraphQL type for indexing job summary."""

    id: str
    workspace_id: str
    status: GraphQLIndexingJobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    overall_progress: float
    current_stage: GraphQLIndexingStage
    error_message: str | None


@strawberry.type
class IndexingJobDetail:
    """GraphQL type for detailed indexing job information."""

    id: str
    workspace_id: str
    status: GraphQLIndexingJobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    retry_count: int
    max_retries: int
    priority: int
    progress: IndexingJobProgress


@strawberry.type
class IndexingStatistics:
    """GraphQL type for indexing statistics."""

    total_jobs: int
    queued_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    avg_completion_time: float | None
    success_rate: float | None
    recent_jobs: int
    recent_completions: int


@strawberry.type
class IndexingJobConnection:
    """GraphQL connection type for indexing jobs."""

    edges: list["IndexingJobEdge"]
    page_info: "PageInfo"
    total_count: int


@strawberry.type
class IndexingJobEdge:
    """GraphQL edge type for indexing jobs."""

    node: IndexingJobSummary
    cursor: str


# Workspace Types
@strawberry.type
class Workspace:
    """GraphQL type for workspaces."""

    id: str
    name: str
    description: str | None
    data_path: str
    status: WorkspaceStatus
    created_at: datetime
    updated_at: datetime
    config: JSONType


@strawberry.type
class IndexingJob:
    """GraphQL type for indexing jobs."""

    id: str
    workspace_id: str
    status: IndexingJobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    progress: int | None
    current_stage: str | None


# Query/Response Types
@strawberry.type
class QueryResponse:
    """GraphQL type for query responses."""

    query: str
    response: str
    context: str | None
    query_type: QueryType
    processing_time: float
    entity_count: int | None
    relationship_count: int | None
    token_count: int | None


@strawberry.type
class IndexResponse:
    """GraphQL type for indexing responses."""

    success: bool
    message: str
    job_id: str | None
    workspace_id: str | None


# Application Info Types
@strawberry.type
class ApplicationInterfaces:
    """GraphQL type for application interfaces."""

    rest_api: str
    graphql: str
    documentation: JSONType


@strawberry.type
class ApplicationInfo:
    """GraphQL type for application information."""

    name: str
    version: str
    status: str
    interfaces: ApplicationInterfaces
    endpoints: JSONType


# System Types
@strawberry.type
class SystemHealth:
    """GraphQL type for system health."""

    status: str
    timestamp: datetime
    components: JSONType
    provider: JSONType
    graphrag: JSONType
    workspaces: JSONType
    graph_data: JSONType
    system_resources: JSONType


@strawberry.type
class SystemStatus:
    """GraphQL type for system status."""

    version: str
    environment: str
    uptime_seconds: float
    provider_info: JSONType
    graph_metrics: JSONType
    indexing_metrics: JSONType
    query_metrics: JSONType
    workspace_metrics: JSONType
    recent_operations: list[JSONType]


@strawberry.type
class ProviderSwitchResult:
    """GraphQL type for provider switch results."""

    success: bool
    previous_provider: str
    current_provider: str
    message: str
    validation_result: JSONType | None


@strawberry.type
class ConfigValidationResult:
    """GraphQL type for configuration validation results."""

    valid: bool
    config_type: str
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    validated_config: JSONType | None


# Pagination Types
@strawberry.type
class PageInfo:
    """GraphQL type for pagination information."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@strawberry.type
class EntityConnection:
    """GraphQL connection type for entities."""

    edges: list["EntityEdge"]
    page_info: PageInfo
    total_count: int


@strawberry.type
class EntityEdge:
    """GraphQL edge type for entities."""

    node: Entity
    cursor: str


@strawberry.type
class RelationshipConnection:
    """GraphQL connection type for relationships."""

    edges: list["RelationshipEdge"]
    page_info: PageInfo
    total_count: int


@strawberry.type
class RelationshipEdge:
    """GraphQL edge type for relationships."""

    node: Relationship
    cursor: str


# Visualization Types
@strawberry.type
class GraphNode:
    """GraphQL type for visualization nodes."""

    id: str
    label: str
    type: str
    size: int
    community: str | None
    description: str


@strawberry.type
class GraphEdge:
    """GraphQL type for visualization edges."""

    source: str
    target: str
    type: str
    weight: float
    label: str | None


@strawberry.type
class GraphVisualization:
    """GraphQL type for graph visualization data."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    layout: str
    metadata: JSONType


# Export Types
@strawberry.type
class GraphExport:
    """GraphQL type for graph export results."""

    download_url: str
    format: str
    file_size: int
    entity_count: int
    relationship_count: int
    expires_at: datetime


# Cache Types
@strawberry.type
class CacheStatistics:
    """GraphQL type for cache statistics."""

    total_size_bytes: int
    total_files: int
    cache_hit_rate: float | None
    last_cleared: datetime | None
    cache_types: JSONType


@strawberry.type
class CacheClearResult:
    """GraphQL type for cache clear operation result."""

    success: bool
    message: str
    files_cleared: int
    bytes_freed: int


# Advanced Query Engine Types
@strawberry.type
class QueryPath:
    """GraphQL type for query path through the knowledge graph."""

    entities: list[str]
    relationships: list[str]
    score: float
    confidence: float
    path_length: int


@strawberry.input
class MultiHopQueryInput:
    """GraphQL input for multi-hop query configuration."""

    start_entities: list[str]
    target_entities: list[str] | None = None
    max_hops: int = 3
    relationship_types: list[str] | None = None
    scoring_algorithm: str = "pagerank"


@strawberry.input
class TemporalQueryInput:
    """GraphQL input for temporal query constraints."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    time_field: str = "created_at"
    temporal_operator: str = "within"


@strawberry.type
class AdvancedQueryResult:
    """GraphQL type for advanced query results."""

    entities: list[Entity]
    relationships: list[Relationship]
    paths: list[QueryPath]
    total_score: float
    execution_time_ms: float
    query_metadata: JSONType


# Graph Analytics Types (using existing Community type from line 112)


@strawberry.type
class CommunityDetectionResult:
    """GraphQL type for community detection results."""

    communities: list[Community]
    modularity_score: float
    algorithm_used: str
    execution_time_ms: float


@strawberry.type
class CentralityMeasures:
    """GraphQL type for node centrality measures."""

    node_id: str
    degree_centrality: float
    betweenness_centrality: float
    closeness_centrality: float
    eigenvector_centrality: float
    pagerank: float


@strawberry.type
class Cluster:
    """GraphQL type for graph cluster."""

    cluster_id: int
    entities: list[str]
    size: int
    centroid: str | None = None


@strawberry.type
class ClusteringResult:
    """GraphQL type for clustering analysis results."""

    clusters: list[Cluster]
    silhouette_score: float
    algorithm_used: str
    num_clusters: int


@strawberry.type
class AnomalyDetectionResult:
    """GraphQL type for anomaly detection results."""

    anomalous_entities: list[Entity]
    anomalous_relationships: list[Relationship]
    anomaly_scores: JSONType
    detection_method: str




@strawberry.type
class PerformanceMetrics:
    """GraphQL type for performance metrics."""

    timestamp: float
    cpu_usage_percent: float
    memory_usage_mb: float
    active_connections: int
    requests_per_second: float
    average_response_time: float
    cache_hit_rate: float


@strawberry.type
class IndexingStatus:
    """GraphQL type for indexing status."""

    workspace_id: str
    status: str
    progress: float
    message: str
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
