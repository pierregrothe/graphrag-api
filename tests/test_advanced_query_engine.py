# tests/test_advanced_query_engine.py
# Tests for Advanced Query Engine
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for the advanced query engine with multi-hop reasoning and temporal support."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from src.graphrag_api_service.graph.advanced_query_engine import (
    AdvancedQueryEngine,
    MultiHopQuery,
    QueryPath,
    QueryResult,
    TemporalQuery,
)
from src.graphrag_api_service.graph.operations import GraphOperationsError


@pytest.fixture
def sample_entities_data():
    """Sample entities data for testing."""
    return pd.DataFrame(
        [
            {
                "id": "entity_1",
                "title": "Entity 1",
                "type": "PERSON",
                "description": "Test entity 1",
                "created_at": "2023-01-01T00:00:00Z",
            },
            {
                "id": "entity_2",
                "title": "Entity 2",
                "type": "ORGANIZATION",
                "description": "Test entity 2",
                "created_at": "2023-06-01T00:00:00Z",
            },
            {
                "id": "entity_3",
                "title": "Entity 3",
                "type": "PERSON",
                "description": "Test entity 3",
                "created_at": "2023-12-01T00:00:00Z",
            },
        ]
    )


@pytest.fixture
def sample_relationships_data():
    """Sample relationships data for testing."""
    return pd.DataFrame(
        [
            {
                "id": "rel_1",
                "source": "entity_1",
                "target": "entity_2",
                "description": "works for",
                "weight": 0.8,
                "created_at": "2023-02-01T00:00:00Z",
            },
            {
                "id": "rel_2",
                "source": "entity_2",
                "target": "entity_3",
                "description": "collaborates with",
                "weight": 0.6,
                "created_at": "2023-07-01T00:00:00Z",
            },
        ]
    )


@pytest.fixture
def advanced_query_engine():
    """Create an advanced query engine instance for testing."""
    return AdvancedQueryEngine("/test/data/path")


class TestAdvancedQueryEngine:
    """Test cases for the AdvancedQueryEngine class."""

    @pytest.mark.asyncio
    async def test_load_data_success(
        self, advanced_query_engine, sample_entities_data, sample_relationships_data
    ):
        """Test successful data loading."""
        with (
            patch("os.path.exists", return_value=True),
            patch("pandas.read_parquet") as mock_read_parquet,
        ):

            mock_read_parquet.side_effect = [sample_entities_data, sample_relationships_data]

            await advanced_query_engine.load_data()

            assert advanced_query_engine._entities_cache is not None
            assert advanced_query_engine._relationships_cache is not None
            assert len(advanced_query_engine._entities_cache) == 3
            assert len(advanced_query_engine._relationships_cache) == 2

    @pytest.mark.asyncio
    async def test_load_data_file_not_found(self, advanced_query_engine):
        """Test data loading when files don't exist."""
        with patch("os.path.exists", return_value=False):
            await advanced_query_engine.load_data()

            assert advanced_query_engine._entities_cache is None
            assert advanced_query_engine._relationships_cache is None

    @pytest.mark.asyncio
    async def test_load_data_exception(self, advanced_query_engine):
        """Test data loading with exception."""
        with (
            patch("os.path.exists", return_value=True),
            patch("pandas.read_parquet", side_effect=Exception("Read error")),
        ):

            with pytest.raises(GraphOperationsError, match="Data loading failed"):
                await advanced_query_engine.load_data()

    @pytest.mark.asyncio
    async def test_multi_hop_query_success(
        self, advanced_query_engine, sample_entities_data, sample_relationships_data
    ):
        """Test successful multi-hop query execution."""
        # Setup mock data
        advanced_query_engine._entities_cache = sample_entities_data
        advanced_query_engine._relationships_cache = sample_relationships_data

        query = MultiHopQuery(
            start_entities=["entity_1"],
            target_entities=["entity_3"],
            max_hops=2,
            scoring_algorithm="pagerank",
        )

        result = await advanced_query_engine.multi_hop_query(query)

        assert isinstance(result, QueryResult)
        assert result.execution_time_ms > 0
        assert result.query_metadata["query_type"] == "multi_hop"
        assert result.query_metadata["max_hops"] == 2
        assert result.query_metadata["scoring_algorithm"] == "pagerank"

    @pytest.mark.asyncio
    async def test_multi_hop_query_no_data(self, advanced_query_engine):
        """Test multi-hop query with no data loaded."""
        query = MultiHopQuery(start_entities=["entity_1"])

        with patch.object(advanced_query_engine, "load_data") as mock_load:
            mock_load.return_value = None
            advanced_query_engine._entities_cache = None
            advanced_query_engine._relationships_cache = None

            result = await advanced_query_engine.multi_hop_query(query)
            assert len(result.entities) == 0
            assert len(result.relationships) == 0

    @pytest.mark.asyncio
    async def test_temporal_query_success(
        self, advanced_query_engine, sample_entities_data, sample_relationships_data
    ):
        """Test successful temporal query execution."""
        # Setup mock data
        advanced_query_engine._entities_cache = sample_entities_data
        advanced_query_engine._relationships_cache = sample_relationships_data

        temporal_constraints = TemporalQuery(
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 6, 30),
            time_field="created_at",
            temporal_operator="within",
        )

        result = await advanced_query_engine.temporal_query({}, temporal_constraints)

        assert isinstance(result, QueryResult)
        assert result.execution_time_ms > 0
        assert result.query_metadata["query_type"] == "temporal"
        assert result.query_metadata["temporal_operator"] == "within"

        # Should filter to entities/relationships within the time range
        assert len(result.entities) <= 3
        assert len(result.relationships) <= 2

    @pytest.mark.asyncio
    async def test_temporal_query_no_time_field(self, advanced_query_engine, sample_entities_data):
        """Test temporal query when time field doesn't exist."""
        # Remove created_at column
        entities_no_time = sample_entities_data.drop(columns=["created_at"])
        advanced_query_engine._entities_cache = entities_no_time
        advanced_query_engine._relationships_cache = pd.DataFrame()

        temporal_constraints = TemporalQuery(
            start_time=datetime(2023, 1, 1), time_field="nonexistent_field"
        )

        result = await advanced_query_engine.temporal_query({}, temporal_constraints)

        # Should return all data when time field doesn't exist
        assert len(result.entities) == 3

    @pytest.mark.asyncio
    async def test_find_paths_basic(self, advanced_query_engine):
        """Test basic path finding functionality."""
        paths = await advanced_query_engine._find_paths(
            start_entities=["entity_1"],
            target_entities=["entity_2"],
            max_hops=2,
            relationship_types=None,
        )

        assert len(paths) > 0
        assert all(isinstance(path, QueryPath) for path in paths)
        assert all(path.path_length >= 0 for path in paths)

    @pytest.mark.asyncio
    async def test_score_paths_pagerank(self, advanced_query_engine):
        """Test path scoring with PageRank algorithm."""
        paths = [
            QueryPath(
                entities=["e1", "e2"],
                relationships=["r1"],
                score=0.0,
                confidence=0.8,
                path_length=1,
            ),
            QueryPath(
                entities=["e1", "e2", "e3"],
                relationships=["r1", "r2"],
                score=0.0,
                confidence=0.6,
                path_length=2,
            ),
        ]

        scored_paths = await advanced_query_engine._score_paths(paths, "pagerank")

        assert len(scored_paths) == 2
        assert all(path.score > 0 for path in scored_paths)
        # Shorter paths should have higher scores with PageRank
        assert scored_paths[0].score >= scored_paths[1].score

    @pytest.mark.asyncio
    async def test_score_paths_betweenness(self, advanced_query_engine):
        """Test path scoring with betweenness algorithm."""
        paths = [
            QueryPath(entities=["e1"], relationships=[], score=0.0, confidence=1.0, path_length=0),
            QueryPath(
                entities=["e1", "e2"],
                relationships=["r1"],
                score=0.0,
                confidence=0.8,
                path_length=1,
            ),
        ]

        scored_paths = await advanced_query_engine._score_paths(paths, "betweenness")

        assert len(scored_paths) == 2
        assert all(path.score > 0 for path in scored_paths)

    @pytest.mark.asyncio
    async def test_apply_temporal_filter_with_constraints(
        self, advanced_query_engine, sample_entities_data
    ):
        """Test temporal filtering with start and end time constraints."""
        temporal_constraints = TemporalQuery(
            start_time=datetime(2023, 5, 1), end_time=datetime(2023, 11, 1), time_field="created_at"
        )

        filtered_data = await advanced_query_engine._apply_temporal_filter(
            sample_entities_data, temporal_constraints
        )

        # Should only include entity_2 (created 2023-06-01)
        assert len(filtered_data) == 1
        assert filtered_data.iloc[0]["id"] == "entity_2"

    @pytest.mark.asyncio
    async def test_apply_temporal_filter_start_only(
        self, advanced_query_engine, sample_entities_data
    ):
        """Test temporal filtering with only start time constraint."""
        temporal_constraints = TemporalQuery(
            start_time=datetime(2023, 6, 1), time_field="created_at"
        )

        filtered_data = await advanced_query_engine._apply_temporal_filter(
            sample_entities_data, temporal_constraints
        )

        # Should include entity_2 and entity_3
        assert len(filtered_data) == 2
        assert set(filtered_data["id"]) == {"entity_2", "entity_3"}

    @pytest.mark.asyncio
    async def test_get_entities_details(self, advanced_query_engine, sample_entities_data):
        """Test getting detailed entity information."""
        advanced_query_engine._entities_cache = sample_entities_data

        details = await advanced_query_engine._get_entities_details(["entity_1", "entity_3"])

        assert len(details) == 2
        assert details[0]["id"] == "entity_1"
        assert details[1]["id"] == "entity_3"

    @pytest.mark.asyncio
    async def test_get_entities_details_no_cache(self, advanced_query_engine):
        """Test getting entity details with no cache."""
        advanced_query_engine._entities_cache = None

        details = await advanced_query_engine._get_entities_details(["entity_1"])

        assert details == []

    @pytest.mark.asyncio
    async def test_get_relationships_details(
        self, advanced_query_engine, sample_relationships_data
    ):
        """Test getting detailed relationship information."""
        advanced_query_engine._relationships_cache = sample_relationships_data

        details = await advanced_query_engine._get_relationships_details(["rel_1"])

        assert len(details) == 1
        assert details[0]["id"] == "rel_1"
        assert details[0]["source"] == "entity_1"
        assert details[0]["target"] == "entity_2"

    @pytest.mark.asyncio
    async def test_multi_hop_query_exception_handling(self, advanced_query_engine):
        """Test multi-hop query exception handling."""
        query = MultiHopQuery(start_entities=["entity_1"])

        with patch.object(
            advanced_query_engine, "_find_paths", side_effect=Exception("Path finding error")
        ):
            with pytest.raises(GraphOperationsError, match="Multi-hop query execution failed"):
                await advanced_query_engine.multi_hop_query(query)

    @pytest.mark.asyncio
    async def test_temporal_query_exception_handling(self, advanced_query_engine):
        """Test temporal query exception handling."""
        temporal_constraints = TemporalQuery()

        # Set up the cache first to avoid load_data() being called
        advanced_query_engine._entities_cache = pd.DataFrame()
        advanced_query_engine._relationships_cache = pd.DataFrame()

        with patch.object(
            advanced_query_engine, "_apply_temporal_filter", side_effect=Exception("Filter error")
        ):
            with pytest.raises(GraphOperationsError, match="Temporal query execution failed"):
                await advanced_query_engine.temporal_query({}, temporal_constraints)
