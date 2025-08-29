# tests/test_graphql.py
# GraphQL API tests
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for GraphQL API functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.graphql import create_graphql_router


@pytest.fixture
def mock_graph_operations():
    """Create mock graph operations."""
    mock = MagicMock()
    mock.query_entities = AsyncMock(
        return_value={
            "entities": [
                {
                    "id": "entity1",
                    "title": "Test Entity",
                    "type": "PERSON",
                    "description": "A test entity",
                    "degree": 5,
                    "community_ids": ["comm1"],
                    "text_unit_ids": ["text1"],
                }
            ],
            "total_count": 1,
        }
    )
    mock.query_relationships = AsyncMock(
        return_value={
            "relationships": [
                {
                    "id": "rel1",
                    "source": "entity1",
                    "target": "entity2",
                    "type": "KNOWS",
                    "description": "Test relationship",
                    "weight": 0.8,
                    "text_unit_ids": ["text1"],
                }
            ],
            "total_count": 1,
        }
    )
    mock.get_graph_statistics = AsyncMock(
        return_value={
            "total_entities": 100,
            "total_relationships": 200,
            "total_communities": 10,
            "entity_types": {"PERSON": 50, "ORGANIZATION": 50},
            "relationship_types": {"KNOWS": 100, "WORKS_FOR": 100},
            "community_levels": {0: 10},
            "graph_density": 0.02,
            "connected_components": 1,
        }
    )
    mock.generate_visualization = AsyncMock(
        return_value={
            "nodes": [
                {
                    "id": "node1",
                    "label": "Node 1",
                    "type": "PERSON",
                    "size": 10,
                    "community": "comm1",
                    "description": "Test node",
                }
            ],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "type": "KNOWS",
                    "weight": 1.0,
                    "label": "knows",
                }
            ],
            "layout": "force_directed",
            "metadata": {},
        }
    )
    return mock


@pytest.fixture
def mock_workspace_manager():
    """Create mock workspace manager."""
    mock = MagicMock()
    mock.list_workspaces = MagicMock(
        return_value=[
            MagicMock(
                id="ws1",
                name="Test Workspace",
                description="A test workspace",
                data_path="/data/test",
                status="ready",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                config=None,
            )
        ]
    )
    mock.get_workspace = MagicMock(
        return_value=MagicMock(
            id="ws1",
            name="Test Workspace",
            description="A test workspace",
            data_path="/data/test",
            status="ready",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            config=None,
        )
    )
    # Create a proper mock workspace object with spec_set to prevent new attributes
    mock_workspace = MagicMock()
    mock_workspace.id = "ws2"
    mock_workspace.name = "New Workspace"
    mock_workspace.description = "A new workspace"
    mock_workspace.data_path = "/data/new"
    mock_workspace.status = "created"
    mock_workspace.created_at = "2025-01-01T00:00:00"
    mock_workspace.updated_at = "2025-01-01T00:00:00"
    mock_workspace.config = None

    mock.create_workspace = MagicMock(return_value=mock_workspace)
    mock.delete_workspace = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_system_operations():
    """Create mock system operations."""
    mock = MagicMock()
    mock.get_advanced_health = AsyncMock(
        return_value={
            "status": "healthy",
            "timestamp": "2025-01-01T00:00:00",
            "components": {"api": "healthy", "graphrag": "healthy"},
            "provider": {"type": "ollama", "status": "connected"},
            "graphrag": {"version": "1.0.0", "status": "ready"},
            "workspaces": {"total": 1, "active": 1},
            "graph_data": {"entities": 100, "relationships": 200},
            "system_resources": {"cpu_percent": 50.0, "memory_percent": 60.0},
        }
    )
    mock.get_enhanced_status = AsyncMock(
        return_value={
            "version": "0.1.0",
            "environment": "development",
            "uptime_seconds": 3600.0,
            "provider_info": {"type": "ollama", "model": "gemma:4b"},
            "graph_metrics": {"total_nodes": 100, "total_edges": 200},
            "indexing_metrics": {"total_jobs": 10, "active_jobs": 1},
            "query_metrics": {"total_queries": 100, "avg_response_time": 0.5},
            "workspace_metrics": {"total_workspaces": 1, "active_workspace": "ws1"},
            "recent_operations": [],
        }
    )
    mock.switch_provider = AsyncMock(
        return_value={
            "success": True,
            "previous_provider": "ollama",
            "current_provider": "google_gemini",
            "message": "Provider switched successfully",
            "validation_result": None,
        }
    )
    mock.validate_config = AsyncMock(
        return_value={
            "valid": True,
            "config_type": "provider",
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "validated_config": {},
        }
    )
    return mock


@pytest.fixture
def mock_graphrag_integration():
    """Create mock GraphRAG integration."""
    mock = MagicMock()
    mock.query = AsyncMock(
        return_value={
            "response": "This is a test response",
            "context": "Test context",
            "processing_time": 0.5,
            "entity_count": 5,
            "relationship_count": 10,
            "token_count": 100,
        }
    )
    mock.index = AsyncMock(
        return_value={
            "success": True,
            "message": "Indexing started",
            "job_id": "job123",
        }
    )
    return mock


@pytest.fixture
def mock_indexing_manager():
    """Create mock indexing manager."""
    mock = MagicMock()
    mock.cancel_job = MagicMock(return_value=True)
    return mock


@pytest.fixture
def graphql_client(
    mock_graph_operations,
    mock_workspace_manager,
    mock_system_operations,
    mock_graphrag_integration,
    mock_indexing_manager,
):
    """Create a test client with GraphQL router."""
    from fastapi import FastAPI

    app = FastAPI()

    # Create GraphQL router with mocks
    graphql_router = create_graphql_router(
        graph_operations=mock_graph_operations,
        workspace_manager=mock_workspace_manager,
        system_operations=mock_system_operations,
        graphrag_integration=mock_graphrag_integration,
        indexing_manager=mock_indexing_manager,
    )

    app.include_router(graphql_router, prefix="/graphql")

    return TestClient(app)


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    def test_query_entities(self, graphql_client, mock_graph_operations):
        """Test querying entities through GraphQL."""
        query = """
        query {
            entities(first: 10) {
                edges {
                    node {
                        id
                        title
                        type
                        description
                    }
                }
                totalCount
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.queries.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "entities" in data["data"]
        assert data["data"]["entities"]["totalCount"] == 1
        assert len(data["data"]["entities"]["edges"]) == 1
        assert data["data"]["entities"]["edges"][0]["node"]["id"] == "entity1"

    def test_query_single_entity(self, graphql_client, mock_graph_operations):
        """Test querying a single entity by ID."""
        query = """
        query {
            entity(id: "entity1") {
                id
                title
                type
                description
                degree
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.queries.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "entity" in data["data"]
        assert data["data"]["entity"]["id"] == "entity1"

    def test_query_relationships(self, graphql_client, mock_graph_operations):
        """Test querying relationships through GraphQL."""
        query = """
        query {
            relationships(first: 10) {
                edges {
                    node {
                        id
                        source
                        target
                        type
                    }
                }
                totalCount
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.queries.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "relationships" in data["data"]
        assert data["data"]["relationships"]["totalCount"] == 1

    def test_query_graph_statistics(self, graphql_client, mock_graph_operations):
        """Test querying graph statistics."""
        query = """
        query {
            graphStatistics {
                totalEntities
                totalRelationships
                totalCommunities
                graphDensity
                connectedComponents
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.queries.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "graphStatistics" in data["data"]
        assert data["data"]["graphStatistics"]["totalEntities"] == 100

    def test_query_workspaces(self, graphql_client, mock_workspace_manager):
        """Test querying workspaces."""
        query = """
        query {
            workspaces {
                id
                name
                description
                status
            }
        }
        """

        response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "workspaces" in data["data"]
        assert len(data["data"]["workspaces"]) == 1
        assert data["data"]["workspaces"][0]["id"] == "ws1"

    def test_query_system_health(self, graphql_client, mock_system_operations):
        """Test querying system health."""
        query = """
        query {
            systemHealth {
                status
                components
                provider
            }
        }
        """

        response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "systemHealth" in data["data"]
        assert data["data"]["systemHealth"]["status"] == "healthy"

    def test_graphrag_query(self, graphql_client, mock_graphrag_integration):
        """Test GraphRAG query execution."""
        query = """
        query {
            graphragQuery(query: "What is the capital of France?", queryType: LOCAL) {
                query
                response
                queryType
                processingTime
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.queries.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "graphragQuery" in data["data"]
        assert data["data"]["graphragQuery"]["response"] == "This is a test response"


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    def test_create_workspace(self, graphql_client, mock_workspace_manager):
        """Test creating a workspace through GraphQL."""
        mutation = """
        mutation {
            createWorkspace(name: "New Workspace", description: "Test workspace") {
                id
                name
                description
                status
            }
        }
        """

        response = graphql_client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "createWorkspace" in data["data"]
        assert data["data"]["createWorkspace"]["id"] == "ws2"
        assert data["data"]["createWorkspace"]["name"] == "New Workspace"

    def test_delete_workspace(self, graphql_client, mock_workspace_manager):
        """Test deleting a workspace through GraphQL."""
        mutation = """
        mutation {
            deleteWorkspace(id: "ws1")
        }
        """

        response = graphql_client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["deleteWorkspace"] is True

    def test_switch_provider(self, graphql_client, mock_system_operations):
        """Test switching LLM provider."""
        mutation = """
        mutation {
            switchProvider(provider: GOOGLE_GEMINI) {
                success
                previousProvider
                currentProvider
                message
            }
        }
        """

        response = graphql_client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "switchProvider" in data["data"]
        assert data["data"]["switchProvider"]["success"] is True

    def test_start_indexing(self, graphql_client, mock_graphrag_integration):
        """Test starting indexing job."""
        mutation = """
        mutation {
            startIndexing(workspaceId: "ws1") {
                success
                message
                jobId
            }
        }
        """

        with patch(
            "src.graphrag_api_service.graphql.mutations.settings.graphrag_data_path",
            "/test/data",
        ):
            response = graphql_client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "startIndexing" in data["data"]
        assert data["data"]["startIndexing"]["success"] is True

    def test_cancel_indexing(self, graphql_client, mock_indexing_manager):
        """Test cancelling indexing job."""
        mutation = """
        mutation {
            cancelIndexing(jobId: "job123")
        }
        """

        response = graphql_client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["cancelIndexing"] is True


class TestGraphQLSchema:
    """Test GraphQL schema definition."""

    def test_schema_introspection(self, graphql_client):
        """Test GraphQL schema introspection."""
        query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """

        response = graphql_client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]
        type_names = [t["name"] for t in data["data"]["__schema"]["types"]]
        assert "Entity" in type_names
        assert "Relationship" in type_names
        assert "Workspace" in type_names
        assert "Query" in type_names
        assert "Mutation" in type_names

    def test_graphiql_playground(self, graphql_client):
        """Test GraphiQL playground availability."""
        response = graphql_client.get("/graphql")

        assert response.status_code == 200
        assert "GraphiQL" in response.text or "graphiql" in response.text.lower()
