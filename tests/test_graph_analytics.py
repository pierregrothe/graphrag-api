# tests/test_graph_analytics.py
# Tests for Graph Analytics Module
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for the graph analytics module with community detection, centrality, and clustering."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.graphrag_api_service.graph.analytics import (
    AnomalyDetectionResult,
    CentralityMeasures,
    ClusteringResult,
    CommunityDetectionResult,
    GraphAnalytics,
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
            },
            {
                "id": "entity_2",
                "title": "Entity 2",
                "type": "ORGANIZATION",
                "description": "Test entity 2",
            },
            {
                "id": "entity_3",
                "title": "Entity 3",
                "type": "PERSON",
                "description": "Test entity 3",
            },
            {
                "id": "entity_4",
                "title": "Entity 4",
                "type": "LOCATION",
                "description": "Test entity 4",
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
            },
            {
                "id": "rel_2",
                "source": "entity_2",
                "target": "entity_3",
                "description": "collaborates with",
                "weight": 0.6,
            },
            {
                "id": "rel_3",
                "source": "entity_1",
                "target": "entity_4",
                "description": "located in",
                "weight": 0.9,
            },
        ]
    )


@pytest.fixture
def graph_analytics():
    """Create a graph analytics instance for testing."""
    return GraphAnalytics("/test/data/path")


class TestGraphAnalytics:
    """Test cases for the GraphAnalytics class."""

    @pytest.mark.asyncio
    async def test_load_data_success(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test successful data loading."""
        with (
            patch("os.path.exists", return_value=True),
            patch("pandas.read_parquet") as mock_read_parquet,
        ):

            mock_read_parquet.side_effect = [sample_entities_data, sample_relationships_data]

            await graph_analytics.load_data()

            assert graph_analytics._entities_cache is not None
            assert graph_analytics._relationships_cache is not None
            assert graph_analytics._graph_cache is not None
            assert len(graph_analytics._entities_cache) == 4
            assert len(graph_analytics._relationships_cache) == 3

    @pytest.mark.asyncio
    async def test_load_data_exception(self, graph_analytics):
        """Test data loading with exception."""
        with (
            patch("os.path.exists", return_value=True),
            patch("pandas.read_parquet", side_effect=Exception("Read error")),
        ):

            with pytest.raises(GraphOperationsError, match="Data loading failed"):
                await graph_analytics.load_data()

    @pytest.mark.asyncio
    async def test_detect_communities_success(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test successful community detection."""
        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        result = await graph_analytics.detect_communities("louvain", 1.0)

        assert isinstance(result, CommunityDetectionResult)
        assert result.algorithm_used == "louvain"
        assert result.modularity_score > 0
        assert result.execution_time_ms > 0
        assert len(result.communities) > 0

        # Check community structure
        for community in result.communities:
            assert "id" in community
            assert "entities" in community
            assert "size" in community
            assert community["size"] > 0

    @pytest.mark.asyncio
    async def test_detect_communities_no_data(self, graph_analytics):
        """Test community detection with no data loaded."""
        with patch.object(graph_analytics, "load_data") as mock_load:
            mock_load.return_value = None
            graph_analytics._entities_cache = None
            graph_analytics._relationships_cache = None

            result = await graph_analytics.detect_communities()
            assert len(result.communities) == 0

    @pytest.mark.asyncio
    async def test_calculate_centrality_measures_success(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test successful centrality calculation."""
        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        results = await graph_analytics.calculate_centrality_measures(["entity_1", "entity_2"])

        assert len(results) == 2
        for result in results:
            assert isinstance(result, CentralityMeasures)
            assert result.node_id in ["entity_1", "entity_2"]
            assert 0 <= result.degree_centrality <= 1
            assert 0 <= result.betweenness_centrality <= 1
            assert 0 <= result.closeness_centrality <= 1
            assert 0 <= result.eigenvector_centrality <= 1
            assert 0 <= result.pagerank <= 1

    @pytest.mark.asyncio
    async def test_calculate_centrality_measures_all_nodes(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test centrality calculation for all nodes."""
        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        results = await graph_analytics.calculate_centrality_measures(None)

        assert len(results) == 4  # All entities
        node_ids = {result.node_id for result in results}
        assert node_ids == {"entity_1", "entity_2", "entity_3", "entity_4"}

    @pytest.mark.asyncio
    async def test_calculate_centrality_measures_no_data(self, graph_analytics):
        """Test centrality calculation with no data."""
        with patch.object(graph_analytics, "load_data") as mock_load:
            mock_load.return_value = None
            graph_analytics._entities_cache = None
            graph_analytics._relationships_cache = None

            with pytest.raises(GraphOperationsError):
                await graph_analytics.calculate_centrality_measures(["entity_1"])

    @pytest.mark.asyncio
    async def test_perform_clustering_success(self, graph_analytics, sample_entities_data):
        """Test successful clustering analysis."""
        graph_analytics._entities_cache = sample_entities_data

        result = await graph_analytics.perform_clustering("kmeans", 2)

        assert isinstance(result, ClusteringResult)
        assert result.algorithm_used == "kmeans"
        assert result.num_clusters == 2
        assert result.silhouette_score > 0
        assert len(result.clusters) == 2

        # Check cluster structure
        total_entities = 0
        for cluster in result.clusters:
            assert "cluster_id" in cluster
            assert "entities" in cluster
            assert "size" in cluster
            total_entities += cluster["size"]

        assert total_entities == 4  # All entities should be assigned

    @pytest.mark.asyncio
    async def test_perform_clustering_auto_clusters(self, graph_analytics, sample_entities_data):
        """Test clustering with automatic cluster number determination."""
        graph_analytics._entities_cache = sample_entities_data

        result = await graph_analytics.perform_clustering("kmeans", None)

        assert isinstance(result, ClusteringResult)
        assert result.num_clusters > 0
        assert len(result.clusters) == result.num_clusters

    @pytest.mark.asyncio
    async def test_detect_anomalies_success(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test successful anomaly detection."""
        # Add weight column for relationship anomaly detection
        sample_relationships_data["weight"] = [0.8, 0.6, 0.95]  # 0.95 should be anomalous

        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        result = await graph_analytics.detect_anomalies("isolation_forest", 0.1)

        assert isinstance(result, AnomalyDetectionResult)
        assert result.detection_method == "isolation_forest"
        assert isinstance(result.anomalous_entities, list)
        assert isinstance(result.anomalous_relationships, list)

    @pytest.mark.asyncio
    async def test_detect_anomalies_no_weight_column(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test anomaly detection without weight column."""
        # Remove weight column
        sample_relationships_data = sample_relationships_data.drop(columns=["weight"])

        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        result = await graph_analytics.detect_anomalies()

        assert len(result.anomalous_relationships) == 0  # No weight-based anomalies

    @pytest.mark.asyncio
    async def test_build_graph_representation(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test graph representation building."""
        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        await graph_analytics._build_graph_representation()

        assert graph_analytics._graph_cache is not None
        assert "nodes" in graph_analytics._graph_cache
        assert "edges" in graph_analytics._graph_cache
        assert len(graph_analytics._graph_cache["nodes"]) == 4
        assert len(graph_analytics._graph_cache["edges"]) == 3

    @pytest.mark.asyncio
    async def test_simple_community_detection(self, graph_analytics, sample_entities_data):
        """Test simple community detection implementation."""
        graph_analytics._entities_cache = sample_entities_data

        communities = await graph_analytics._simple_community_detection()

        assert len(communities) > 0
        # Should group by entity type
        community_types = {community["type"] for community in communities}
        assert "PERSON" in community_types
        assert "ORGANIZATION" in community_types
        assert "LOCATION" in community_types

    @pytest.mark.asyncio
    async def test_simple_community_detection_no_type_column(self, graph_analytics):
        """Test community detection without type column."""
        entities_no_type = pd.DataFrame(
            [
                {"id": "entity_1", "title": "Entity 1"},
                {"id": "entity_2", "title": "Entity 2"},
            ]
        )
        graph_analytics._entities_cache = entities_no_type

        communities = await graph_analytics._simple_community_detection()

        assert communities == []  # No communities without type column

    @pytest.mark.asyncio
    async def test_calculate_degree_centrality(self, graph_analytics, sample_relationships_data):
        """Test degree centrality calculation."""
        graph_analytics._relationships_cache = sample_relationships_data
        graph_analytics._entities_cache = pd.DataFrame([{"id": f"entity_{i}"} for i in range(1, 5)])

        centrality = await graph_analytics._calculate_degree_centrality("entity_1")

        assert 0 <= centrality <= 1
        # entity_1 has 2 connections (to entity_2 and entity_4)
        expected_centrality = 2 / 3  # 2 connections out of 3 possible
        assert abs(centrality - expected_centrality) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_degree_centrality_no_relationships(self, graph_analytics):
        """Test degree centrality with no relationships."""
        graph_analytics._relationships_cache = None

        centrality = await graph_analytics._calculate_degree_centrality("entity_1")

        assert centrality == 0.0

    @pytest.mark.asyncio
    async def test_simple_clustering(self, graph_analytics, sample_entities_data):
        """Test simple clustering implementation."""
        graph_analytics._entities_cache = sample_entities_data

        clusters = await graph_analytics._simple_clustering(2)

        assert len(clusters) == 2
        total_entities = sum(cluster["size"] for cluster in clusters)
        assert total_entities == 4  # All entities should be assigned

    @pytest.mark.asyncio
    async def test_detect_entity_anomalies(
        self, graph_analytics, sample_entities_data, sample_relationships_data
    ):
        """Test entity anomaly detection."""
        graph_analytics._entities_cache = sample_entities_data
        graph_analytics._relationships_cache = sample_relationships_data

        anomalies = await graph_analytics._detect_entity_anomalies(0.5)

        # Should detect entities with high degree centrality
        assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_detect_relationship_anomalies(self, graph_analytics, sample_relationships_data):
        """Test relationship anomaly detection."""
        # Add weight column with one high weight
        sample_relationships_data["weight"] = [0.8, 0.6, 0.95]
        graph_analytics._relationships_cache = sample_relationships_data

        anomalies = await graph_analytics._detect_relationship_anomalies(0.1)

        # Should detect the relationship with weight 0.95
        assert len(anomalies) > 0
        assert any(rel["weight"] == 0.95 for rel in anomalies)

    @pytest.mark.asyncio
    async def test_exception_handling(self, graph_analytics):
        """Test exception handling in various methods."""
        # Test community detection exception
        with patch.object(
            graph_analytics, "_simple_community_detection", side_effect=Exception("Community error")
        ):
            with pytest.raises(GraphOperationsError, match="Community detection failed"):
                await graph_analytics.detect_communities()

        # Test centrality calculation exception
        with patch.object(
            graph_analytics,
            "_calculate_degree_centrality",
            side_effect=Exception("Centrality error"),
        ):
            with pytest.raises(GraphOperationsError, match="Centrality calculation failed"):
                await graph_analytics.calculate_centrality_measures(["entity_1"])

        # Test clustering exception
        with patch.object(
            graph_analytics, "_simple_clustering", side_effect=Exception("Clustering error")
        ):
            with pytest.raises(GraphOperationsError, match="Graph clustering failed"):
                await graph_analytics.perform_clustering()

        # Test anomaly detection exception
        with patch.object(
            graph_analytics, "_detect_entity_anomalies", side_effect=Exception("Anomaly error")
        ):
            with pytest.raises(GraphOperationsError, match="Anomaly detection failed"):
                await graph_analytics.detect_anomalies()
