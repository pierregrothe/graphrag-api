# tests/test_graph_operations.py
# Tests for graph operations and knowledge graph analysis
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for graph operations and knowledge graph analysis functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.graph.operations import GraphOperations, GraphOperationsError
from src.graphrag_api_service.main import app


class TestGraphOperations:
    """Test graph operations functionality."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def graph_operations(self, settings):
        """Create graph operations instance."""
        return GraphOperations(settings)

    @pytest.fixture
    def sample_entities_df(self):
        """Create sample entities DataFrame."""
        return pd.DataFrame(
            [
                {
                    "id": "entity1",
                    "title": "Entity One",
                    "type": "Person",
                    "description": "A sample entity for testing",
                    "degree": 5,
                    "community_ids": ["comm1", "comm2"],
                    "text_unit_ids": ["unit1", "unit2"],
                },
                {
                    "id": "entity2",
                    "title": "Entity Two",
                    "type": "Organization",
                    "description": "Another sample entity for testing purposes",
                    "degree": 3,
                    "community_ids": ["comm1"],
                    "text_unit_ids": ["unit3"],
                },
                {
                    "id": "entity3",
                    "title": "Test Entity",
                    "type": "Person",
                    "description": "Third entity for comprehensive testing",
                    "degree": 8,
                    "community_ids": ["comm2", "comm3"],
                    "text_unit_ids": ["unit4", "unit5"],
                },
            ]
        )

    @pytest.fixture
    def sample_relationships_df(self):
        """Create sample relationships DataFrame."""
        return pd.DataFrame(
            [
                {
                    "id": "rel1",
                    "source": "Entity One",
                    "target": "Entity Two",
                    "type": "WorksWith",
                    "description": "Professional collaboration",
                    "weight": 0.8,
                    "text_unit_ids": ["unit1"],
                },
                {
                    "id": "rel2",
                    "source": "Entity Two",
                    "target": "Test Entity",
                    "type": "KnowsAbout",
                    "description": "Knowledge sharing relationship",
                    "weight": 0.6,
                    "text_unit_ids": ["unit2", "unit3"],
                },
            ]
        )

    @pytest.fixture
    def sample_communities_df(self):
        """Create sample communities DataFrame."""
        return pd.DataFrame(
            [
                {"id": "comm1", "level": 0, "title": "Community 1"},
                {"id": "comm2", "level": 1, "title": "Community 2"},
                {"id": "comm3", "level": 0, "title": "Community 3"},
            ]
        )

    @pytest.fixture
    def temp_graph_data(self, sample_entities_df, sample_relationships_df, sample_communities_df):
        """Create temporary graph data directory with parquet files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output" / "artifacts"
            output_dir.mkdir(parents=True)

            # Save DataFrames as parquet files
            sample_entities_df.to_parquet(output_dir / "create_final_entities.parquet")
            sample_relationships_df.to_parquet(output_dir / "create_final_relationships.parquet")
            sample_communities_df.to_parquet(output_dir / "create_final_communities.parquet")

            yield temp_dir

    @pytest.mark.asyncio
    async def test_query_entities_all(self, graph_operations, temp_graph_data):
        """Test querying all entities without filters."""
        result = await graph_operations.query_entities(temp_graph_data)

        assert "entities" in result
        assert "total_count" in result
        assert result["total_count"] == 3
        assert len(result["entities"]) == 3
        assert result["limit"] == 50
        assert result["offset"] == 0

        # Check entity structure
        entity = result["entities"][0]
        assert "id" in entity
        assert "title" in entity
        assert "type" in entity
        assert "description" in entity

    @pytest.mark.asyncio
    async def test_query_entities_with_name_filter(self, graph_operations, temp_graph_data):
        """Test querying entities with name filter."""
        result = await graph_operations.query_entities(temp_graph_data, entity_name="Test")

        assert result["total_count"] == 1
        assert len(result["entities"]) == 1
        assert result["entities"][0]["title"] == "Test Entity"

    @pytest.mark.asyncio
    async def test_query_entities_with_type_filter(self, graph_operations, temp_graph_data):
        """Test querying entities with type filter."""
        result = await graph_operations.query_entities(temp_graph_data, entity_type="Person")

        assert result["total_count"] == 2
        assert len(result["entities"]) == 2
        for entity in result["entities"]:
            assert entity["type"] == "Person"

    @pytest.mark.asyncio
    async def test_query_entities_with_pagination(self, graph_operations, temp_graph_data):
        """Test querying entities with pagination."""
        # First page
        result1 = await graph_operations.query_entities(temp_graph_data, limit=2, offset=0)
        assert len(result1["entities"]) == 2
        assert result1["limit"] == 2
        assert result1["offset"] == 0

        # Second page
        result2 = await graph_operations.query_entities(temp_graph_data, limit=2, offset=2)
        assert len(result2["entities"]) == 1
        assert result2["offset"] == 2

    @pytest.mark.asyncio
    async def test_query_entities_missing_data(self, graph_operations):
        """Test querying entities when data is missing."""
        with pytest.raises(GraphOperationsError, match="Entities data not found"):
            await graph_operations.query_entities("/nonexistent/path")

    @pytest.mark.asyncio
    async def test_query_relationships_all(self, graph_operations, temp_graph_data):
        """Test querying all relationships without filters."""
        result = await graph_operations.query_relationships(temp_graph_data)

        assert "relationships" in result
        assert "total_count" in result
        assert result["total_count"] == 2
        assert len(result["relationships"]) == 2

        # Check relationship structure
        relationship = result["relationships"][0]
        assert "id" in relationship
        assert "source" in relationship
        assert "target" in relationship
        assert "type" in relationship

    @pytest.mark.asyncio
    async def test_query_relationships_with_filters(self, graph_operations, temp_graph_data):
        """Test querying relationships with filters."""
        result = await graph_operations.query_relationships(
            temp_graph_data, source_entity="Entity One"
        )

        assert result["total_count"] == 1
        assert result["relationships"][0]["source"] == "Entity One"

    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, graph_operations, temp_graph_data):
        """Test getting comprehensive graph statistics."""
        result = await graph_operations.get_graph_statistics(temp_graph_data)

        assert "total_entities" in result
        assert "total_relationships" in result
        assert "total_communities" in result
        assert result["total_entities"] == 3
        assert result["total_relationships"] == 2
        assert result["total_communities"] == 3

        assert "entity_types" in result
        assert "relationship_types" in result
        assert "community_levels" in result
        assert "graph_density" in result

        # Check entity types distribution
        assert result["entity_types"]["Person"] == 2
        assert result["entity_types"]["Organization"] == 1

        # Check graph density is calculated
        assert isinstance(result["graph_density"], float)
        assert 0.0 <= result["graph_density"] <= 1.0

    @pytest.mark.asyncio
    async def test_generate_visualization(self, graph_operations, temp_graph_data):
        """Test generating graph visualization data."""
        result = await graph_operations.generate_visualization(
            temp_graph_data, entity_limit=10, relationship_limit=10
        )

        assert "nodes" in result
        assert "edges" in result
        assert "layout" in result
        assert "metadata" in result

        # Check nodes structure
        assert len(result["nodes"]) <= 10
        if result["nodes"]:
            node = result["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "size" in node

        # Check edges structure
        if result["edges"]:
            edge = result["edges"][0]
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge

        # Check metadata
        metadata = result["metadata"]
        assert "total_nodes" in metadata
        assert "total_edges" in metadata
        assert "generated_at" in metadata

    @pytest.mark.asyncio
    async def test_export_graph_json(self, graph_operations, temp_graph_data):
        """Test exporting graph data in JSON format."""
        result = await graph_operations.export_graph(
            temp_graph_data, format="json", include_entities=True, include_relationships=True
        )

        assert "download_url" in result
        assert "format" in result
        assert "file_size" in result
        assert "entity_count" in result
        assert "relationship_count" in result
        assert "expires_at" in result

        assert result["format"] == "json"
        assert result["entity_count"] == 3
        assert result["relationship_count"] == 2
        assert result["file_size"] > 0

    @pytest.mark.asyncio
    async def test_export_graph_with_limits(self, graph_operations, temp_graph_data):
        """Test exporting graph data with entity and relationship limits."""
        result = await graph_operations.export_graph(
            temp_graph_data, format="json", entity_limit=1, relationship_limit=1
        )

        assert result["entity_count"] == 1
        assert result["relationship_count"] == 1

    def test_load_parquet_file_success(self, graph_operations, temp_graph_data, sample_entities_df):
        """Test successfully loading parquet file."""
        df = graph_operations._load_parquet_file(temp_graph_data, "create_final_entities.parquet")
        assert df is not None
        assert len(df) == 3
        assert "title" in df.columns

    def test_load_parquet_file_missing(self, graph_operations):
        """Test loading non-existent parquet file."""
        df = graph_operations._load_parquet_file("/nonexistent", "missing.parquet")
        assert df is None


class TestGraphAPI:
    """Test graph API endpoints."""

    def test_query_entities_endpoint_no_data_path(self):
        """Test entities endpoint when data path not configured."""
        client = TestClient(app)
        response = client.get("/api/graph/entities")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "GraphRAG data path not configured" in data["error"]

    def test_query_relationships_endpoint_no_data_path(self):
        """Test relationships endpoint when data path not configured."""
        client = TestClient(app)
        response = client.get("/api/graph/relationships")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "GraphRAG data path not configured" in data["error"]

    def test_graph_stats_endpoint_no_data_path(self):
        """Test graph stats endpoint when data path not configured."""
        client = TestClient(app)
        response = client.get("/api/graph/stats")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "GraphRAG data path not configured" in data["error"]

    def test_graph_visualization_endpoint_no_data_path(self):
        """Test visualization endpoint when data path not configured."""
        client = TestClient(app)
        response = client.post(
            "/api/graph/visualization",
            json={
                "entity_limit": 50,
                "relationship_limit": 100,
                "layout_algorithm": "force_directed",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "GraphRAG data path not configured" in data["error"]

    def test_graph_export_endpoint_no_data_path(self):
        """Test export endpoint when data path not configured."""
        client = TestClient(app)
        response = client.post(
            "/api/graph/export",
            json={"format": "json", "include_entities": True, "include_relationships": True},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "GraphRAG data path not configured" in data["error"]

    @patch("src.graphrag_api_service.main.settings")
    @patch("src.graphrag_api_service.main.graph_operations")
    async def test_query_entities_endpoint_success(self, mock_graph_ops, mock_settings):
        """Test successful entities query."""
        from unittest.mock import AsyncMock

        mock_settings.graphrag_data_path = "/test/data"
        mock_graph_ops.query_entities = AsyncMock(
            return_value={
                "entities": [
                    {"id": "1", "title": "Test", "type": "Person", "description": "Test entity"}
                ],
                "total_count": 1,
                "limit": 50,
                "offset": 0,
            }
        )

        client = TestClient(app)
        response = client.get("/api/graph/entities?entity_name=Test")

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert len(data["entities"]) == 1

    @patch("src.graphrag_api_service.main.settings")
    @patch("src.graphrag_api_service.main.graph_operations")
    async def test_graph_stats_endpoint_success(self, mock_graph_ops, mock_settings):
        """Test successful graph statistics endpoint."""
        from unittest.mock import AsyncMock

        mock_settings.graphrag_data_path = "/test/data"
        mock_graph_ops.get_graph_statistics = AsyncMock(
            return_value={
                "total_entities": 100,
                "total_relationships": 200,
                "total_communities": 10,
                "entity_types": {"Person": 50, "Organization": 50},
                "relationship_types": {"WorksWith": 100, "KnowsAbout": 100},
                "community_levels": {"0": 5, "1": 5},
                "graph_density": 0.02,
                "connected_components": 1,
            }
        )

        client = TestClient(app)
        response = client.get("/api/graph/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 100
        assert data["total_relationships"] == 200
        assert data["graph_density"] == 0.02
