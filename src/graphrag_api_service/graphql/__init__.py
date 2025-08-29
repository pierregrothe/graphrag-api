# src/graphrag_api_service/graphql/__init__.py
# GraphQL module initialization
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL module for GraphRAG API service."""

from .mutations import Mutation
from .queries import Query
from .schema import create_graphql_router, schema
from .types import (
    CacheClearResult,
    CacheStatistics,
    ConfigValidationResult,
    Entity,
    EntityConnection,
    GraphExport,
    GraphStatistics,
    GraphVisualization,
    IndexingJob,
    IndexingJobConnection,
    IndexingJobDetail,
    IndexingJobStatus,
    IndexingJobSummary,
    IndexingStatistics,
    IndexResponse,
    LLMProvider,
    ProviderSwitchResult,
    QueryResponse,
    QueryType,
    Relationship,
    RelationshipConnection,
    SystemHealth,
    SystemStatus,
    Workspace,
    WorkspaceStatus,
)

__all__ = [
    # Schema
    "schema",
    "create_graphql_router",
    # Query and Mutation
    "Query",
    "Mutation",
    # Types
    "Entity",
    "EntityConnection",
    "Relationship",
    "RelationshipConnection",
    "GraphStatistics",
    "GraphVisualization",
    "GraphExport",
    "Workspace",
    "WorkspaceStatus",
    "IndexingJob",
    "IndexingJobConnection",
    "IndexingJobDetail",
    "IndexingJobStatus",
    "IndexingJobSummary",
    "IndexingStatistics",
    "IndexResponse",
    "QueryResponse",
    "QueryType",
    "SystemHealth",
    "SystemStatus",
    "ProviderSwitchResult",
    "ConfigValidationResult",
    "LLMProvider",
    "CacheStatistics",
    "CacheClearResult",
]
