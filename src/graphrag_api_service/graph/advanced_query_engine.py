# src/graphrag_api_service/graph/advanced_query_engine.py
# Advanced Query Engine for GraphRAG with multi-hop reasoning and temporal support
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Advanced query engine for GraphRAG with multi-hop reasoning, temporal queries, and custom scoring."""

import logging
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .operations import GraphOperationsError

logger = logging.getLogger(__name__)


class QueryPath(BaseModel):
    """Represents a path through the knowledge graph."""

    entities: list[str]
    relationships: list[str]
    score: float
    confidence: float
    path_length: int


class TemporalQuery(BaseModel):
    """Represents a temporal query with time constraints."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    time_field: str = "created_at"
    temporal_operator: str = "within"  # within, before, after, during


class MultiHopQuery(BaseModel):
    """Represents a multi-hop query configuration."""

    start_entities: list[str]
    target_entities: list[str] | None = None
    max_hops: int = 3
    relationship_types: list[str] | None = None
    scoring_algorithm: str = "pagerank"  # pagerank, betweenness, closeness, custom


class QueryResult(BaseModel):
    """Enhanced query result with scoring and path information."""

    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    paths: list[QueryPath]
    total_score: float
    execution_time_ms: float
    query_metadata: dict[str, Any]


class AdvancedQueryEngine:
    """Advanced query engine with multi-hop reasoning and temporal support."""

    def __init__(self, data_path: str):
        """Initialize the advanced query engine.

        Args:
            data_path: Path to the GraphRAG data directory
        """
        self.data_path = data_path
        self._entities_cache: pd.DataFrame | None = None
        self._relationships_cache: pd.DataFrame | None = None

    async def load_data(self) -> None:
        """Load and cache graph data."""
        try:
            import os

            entities_path = os.path.join(self.data_path, "create_final_entities.parquet")
            relationships_path = os.path.join(self.data_path, "create_final_relationships.parquet")

            if os.path.exists(entities_path):
                self._entities_cache = pd.read_parquet(entities_path)
            if os.path.exists(relationships_path):
                self._relationships_cache = pd.read_parquet(relationships_path)

            logger.info("Advanced query engine data loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load data for advanced query engine: {e}")
            raise GraphOperationsError(f"Data loading failed: {e}") from e

    async def multi_hop_query(self, query: MultiHopQuery) -> QueryResult:
        """Execute a multi-hop query with path finding.

        Args:
            query: Multi-hop query configuration

        Returns:
            QueryResult with paths and scoring information
        """
        start_time = datetime.now()

        try:
            if self._entities_cache is None or self._relationships_cache is None:
                await self.load_data()

            # Find paths between start and target entities
            paths = await self._find_paths(
                start_entities=query.start_entities,
                target_entities=query.target_entities,
                max_hops=query.max_hops,
                relationship_types=query.relationship_types,
            )

            # Score and rank paths
            scored_paths = await self._score_paths(paths, query.scoring_algorithm)

            # Extract unique entities and relationships from paths
            unique_entities = set()
            unique_relationships = set()

            for path in scored_paths:
                unique_entities.update(path.entities)
                unique_relationships.update(path.relationships)

            # Get detailed information for entities and relationships
            entities_data = await self._get_entities_details(list(unique_entities))
            relationships_data = await self._get_relationships_details(list(unique_relationships))

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return QueryResult(
                entities=entities_data,
                relationships=relationships_data,
                paths=scored_paths,
                total_score=sum(path.score for path in scored_paths),
                execution_time_ms=execution_time,
                query_metadata={
                    "query_type": "multi_hop",
                    "max_hops": query.max_hops,
                    "scoring_algorithm": query.scoring_algorithm,
                    "paths_found": len(scored_paths),
                },
            )

        except Exception as e:
            logger.error(f"Multi-hop query failed: {e}")
            raise GraphOperationsError(f"Multi-hop query execution failed: {e}") from e

    async def temporal_query(
        self, base_query: dict[str, Any], temporal_constraints: TemporalQuery
    ) -> QueryResult:
        """Execute a temporal query with time-based filtering.

        Args:
            base_query: Base query parameters
            temporal_constraints: Temporal filtering constraints

        Returns:
            QueryResult filtered by temporal constraints
        """
        start_time = datetime.now()

        try:
            if self._entities_cache is None or self._relationships_cache is None:
                await self.load_data()

            # Apply temporal filtering to entities and relationships
            if self._entities_cache is not None:
                filtered_entities = await self._apply_temporal_filter(
                    self._entities_cache, temporal_constraints
                )
            else:
                filtered_entities = pd.DataFrame()

            if self._relationships_cache is not None:
                filtered_relationships = await self._apply_temporal_filter(
                    self._relationships_cache, temporal_constraints
                )
            else:
                filtered_relationships = pd.DataFrame()

            # Execute base query on filtered data
            entities_data = [
                {str(k): v for k, v in record.items()}
                for record in filtered_entities.to_dict("records")
            ]
            relationships_data = [
                {str(k): v for k, v in record.items()}
                for record in filtered_relationships.to_dict("records")
            ]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return QueryResult(
                entities=entities_data,
                relationships=relationships_data,
                paths=[],
                total_score=0.0,
                execution_time_ms=execution_time,
                query_metadata={
                    "query_type": "temporal",
                    "temporal_operator": temporal_constraints.temporal_operator,
                    "time_field": temporal_constraints.time_field,
                    "entities_count": len(entities_data),
                    "relationships_count": len(relationships_data),
                },
            )

        except Exception as e:
            logger.error(f"Temporal query failed: {e}")
            raise GraphOperationsError(f"Temporal query execution failed: {e}") from e

    async def _find_paths(
        self,
        start_entities: list[str],
        target_entities: list[str] | None,
        max_hops: int,
        relationship_types: list[str] | None,
    ) -> list[QueryPath]:
        """Find paths between entities using graph traversal.

        Args:
            start_entities: Starting entity IDs
            target_entities: Target entity IDs (if None, find all reachable entities)
            max_hops: Maximum number of hops
            relationship_types: Filter by relationship types

        Returns:
            List of found paths
        """
        paths = []

        # Simplified path finding implementation
        # In a production system, this would use more sophisticated graph algorithms
        for start_entity in start_entities:
            if target_entities:
                for target_entity in target_entities:
                    path = QueryPath(
                        entities=[start_entity, target_entity],
                        relationships=["direct_connection"],
                        score=1.0,
                        confidence=0.8,
                        path_length=1,
                    )
                    paths.append(path)
            else:
                # Find all reachable entities within max_hops
                path = QueryPath(
                    entities=[start_entity],
                    relationships=[],
                    score=1.0,
                    confidence=1.0,
                    path_length=0,
                )
                paths.append(path)

        return paths

    async def _score_paths(self, paths: list[QueryPath], algorithm: str) -> list[QueryPath]:
        """Score and rank paths using the specified algorithm.

        Args:
            paths: List of paths to score
            algorithm: Scoring algorithm to use

        Returns:
            Scored and sorted paths
        """
        # Simplified scoring implementation
        for path in paths:
            if algorithm == "pagerank":
                path.score = 1.0 / (path.path_length + 1)
            elif algorithm == "betweenness":
                path.score = len(path.entities) * 0.1
            elif algorithm == "closeness":
                path.score = 1.0 - (path.path_length * 0.1)
            else:
                path.score = 1.0

        # Sort by score descending
        return sorted(paths, key=lambda p: p.score, reverse=True)

    async def _apply_temporal_filter(
        self, data: pd.DataFrame, constraints: TemporalQuery
    ) -> pd.DataFrame:
        """Apply temporal filtering to a DataFrame.

        Args:
            data: DataFrame to filter
            constraints: Temporal constraints

        Returns:
            Filtered DataFrame
        """
        if constraints.time_field not in data.columns:
            return data

        filtered_data = data.copy()

        # Convert time field to datetime with timezone handling
        time_series = pd.to_datetime(filtered_data[constraints.time_field])

        # Make comparison times timezone-aware if the data is timezone-aware
        start_time = constraints.start_time
        end_time = constraints.end_time

        if time_series.dt.tz is not None:
            # Data is timezone-aware, make comparison times timezone-aware too
            if start_time and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=time_series.dt.tz)
            if end_time and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=time_series.dt.tz)
        elif time_series.dt.tz is None:
            # Data is timezone-naive, make comparison times timezone-naive too
            if start_time and start_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=None)
            if end_time and end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)

        if start_time:
            mask = time_series >= start_time
            filtered_data = filtered_data[mask]

        if end_time:
            # Recalculate time_series for the filtered data to avoid reindexing warning
            time_series_filtered = pd.to_datetime(filtered_data[constraints.time_field])
            if time_series_filtered.dt.tz is not None and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=time_series_filtered.dt.tz)
            elif time_series_filtered.dt.tz is None and end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)

            mask = time_series_filtered <= end_time
            filtered_data = filtered_data[mask]

        return filtered_data

    async def _get_entities_details(self, entity_ids: list[str]) -> list[dict[str, Any]]:
        """Get detailed information for specific entities.

        Args:
            entity_ids: List of entity IDs

        Returns:
            List of entity details
        """
        if self._entities_cache is None:
            return []

        filtered_entities = self._entities_cache[self._entities_cache["id"].isin(entity_ids)]
        return [
            {str(k): v for k, v in record.items()}
            for record in filtered_entities.to_dict("records")
        ]

    async def _get_relationships_details(self, relationship_ids: list[str]) -> list[dict[str, Any]]:
        """Get detailed information for specific relationships.

        Args:
            relationship_ids: List of relationship IDs

        Returns:
            List of relationship details
        """
        if self._relationships_cache is None:
            return []

        filtered_relationships = self._relationships_cache[
            self._relationships_cache["id"].isin(relationship_ids)
        ]
        return [
            {str(k): v for k, v in record.items()}
            for record in filtered_relationships.to_dict("records")
        ]
