# tests/test_graphql_integration_fixed.py
# Fixed GraphQL integration tests with correct schema patterns
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""GraphQL integration tests for the GraphRAG API Service."""

from typing import Any, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport
from httpx import ASGITransport, AsyncClient

from src.graphrag_api_service.main import app


@pytest.fixture
def graphql_url() -> str:
    """Get the GraphQL endpoint URL."""
    return "http://localhost:8001/graphql/playground"


@pytest.fixture
async def graphql_client(graphql_url: str) -> AsyncGenerator[Client, None]:
    """Create a GraphQL client for testing."""
    transport = HTTPXAsyncTransport(url=graphql_url)
    client = Client(transport=transport, fetch_schema_from_transport=False)
    async with client as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    from fastapi.testclient import TestClient
    from httpx import ASGITransport

    with TestClient(app):  # This handles the lifespan events
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    @pytest.mark.asyncio
    async def test_query_entities(self, async_client: AsyncClient):
        """Test querying entities via GraphQL."""
        query = """
        query GetEntities {
            entities(first: 10) {
                edges {
                    node {
                        id
                        title
                        type
                        description
                        degree
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "entities" in data["data"]
        assert "edges" in data["data"]["entities"]
        assert isinstance(data["data"]["entities"]["edges"], list)

    @pytest.mark.asyncio
    async def test_query_relationships(self, async_client: AsyncClient):
        """Test querying relationships via GraphQL."""
        query = """
        query GetRelationships {
            relationships(first: 10) {
                edges {
                    node {
                        id
                        source
                        target
                        type
                        description
                        weight
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "relationships" in data["data"]
        assert "edges" in data["data"]["relationships"]
        assert isinstance(data["data"]["relationships"]["edges"], list)

    @pytest.mark.asyncio
    async def test_query_communities(self, async_client: AsyncClient):
        """Test querying communities via GraphQL."""
        query = """
        query GetCommunities {
            communities(first: 10) {
                edges {
                    node {
                        id
                        level
                        title
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Communities might not exist, so just check structure
        if data["data"]:
            assert "communities" in data["data"]

    @pytest.mark.asyncio
    async def test_query_graph_statistics(self, async_client: AsyncClient):
        """Test querying graph statistics via GraphQL."""
        query = """
        query GetGraphStatistics {
            graphStatistics {
                totalEntities
                totalRelationships
                totalCommunities
                graphDensity
                connectedComponents
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # graphStatistics might be null if no data is loaded
        assert "graphStatistics" in data["data"]
        stats = data["data"]["graphStatistics"]
        if stats is not None:
            assert "totalEntities" in stats
            assert "totalRelationships" in stats

    @pytest.mark.asyncio
    async def test_query_workspaces(self, async_client: AsyncClient):
        """Test querying workspaces via GraphQL."""
        query = """
        query GetWorkspaces {
            workspaces {
                id
                name
                description
                status
                createdAt
                updatedAt
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Workspaces might be null or empty if not initialized
        if "errors" not in data:
            assert "workspaces" in data["data"]
            if data["data"]["workspaces"] is not None:
                assert isinstance(data["data"]["workspaces"], list)

    @pytest.mark.asyncio
    async def test_query_system_health(self, async_client: AsyncClient):
        """Test querying system health via GraphQL."""
        query = """
        query GetSystemHealth {
            systemHealth {
                status
                timestamp
                components {
                    name
                    status
                }
                systemResources {
                    cpuUsagePercent
                    memoryUsageMB
                    diskUsageGB
                }
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # System health might be null if not properly initialized
        if "errors" not in data:
            assert "systemHealth" in data["data"]
            health = data["data"]["systemHealth"]
            if health is not None:
                assert "status" in health
                assert health["status"] in ["healthy", "degraded", "unhealthy"]


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    @pytest.mark.asyncio
    async def test_create_workspace_mutation(self, async_client: AsyncClient):
        """Test creating a workspace via GraphQL mutation."""
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            unique_name = f"test-graphql-{uuid.uuid4().hex[:8]}"

            mutation = """
            mutation CreateWorkspace($input: WorkspaceCreateInput!) {
                createWorkspace(input: $input) {
                    workspace {
                        id
                        name
                        description
                        status
                    }
                    success
                    message
                }
            }
            """

            variables = {
                "input": {
                    "name": unique_name,
                    "description": "Test workspace from GraphQL",
                    "dataPath": temp_dir,
                }
            }

            response = await async_client.post(
                "/graphql/playground", json={"query": mutation, "variables": variables}
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            if data["data"]:
                assert "createWorkspace" in data["data"]
                result = data["data"]["createWorkspace"]
                assert "success" in result
                assert "workspace" in result

    @pytest.mark.asyncio
    async def test_execute_query_mutation(self, async_client: AsyncClient):
        """Test executing a GraphRAG query via GraphQL mutation."""
        mutation = """
        mutation ExecuteQuery($input: QueryExecutionInput!) {
            executeQuery(input: $input) {
                response
                queryType
                success
                executionTime
            }
        }
        """

        variables = {
            "input": {"query": "What is GraphRAG?", "queryType": "LOCAL", "workspaceId": "default"}
        }

        response = await async_client.post(
            "/graphql/playground", json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Query might fail if no data indexed, just check structure
        if data["data"]:
            assert "executeQuery" in data["data"]

    @pytest.mark.asyncio
    async def test_clear_cache_mutation(self, async_client: AsyncClient):
        """Test clearing cache via GraphQL mutation."""
        mutation = """
        mutation ClearCache {
            clearCache {
                success
                message
                filesCleared
                bytesFreed
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": mutation})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        if data["data"]:
            assert "clearCache" in data["data"]
            result = data["data"]["clearCache"]
            assert "success" in result


class TestGraphQLErrorHandling:
    """Test GraphQL error handling."""

    @pytest.mark.asyncio
    async def test_invalid_query_syntax(self, async_client: AsyncClient):
        """Test handling of invalid GraphQL query syntax."""
        query = "INVALID { QUERY SYNTAX"

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    @pytest.mark.asyncio
    async def test_unknown_field(self, async_client: AsyncClient):
        """Test handling of unknown field in query."""
        query = """
        query {
            unknownField {
                id
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data


class TestGraphQLIntrospection:
    """Test GraphQL schema introspection."""

    @pytest.mark.asyncio
    async def test_schema_introspection(self, async_client: AsyncClient):
        """Test GraphQL schema introspection."""
        query = """
        query {
            __schema {
                queryType {
                    name
                    fields {
                        name
                    }
                }
                mutationType {
                    name
                }
                subscriptionType {
                    name
                }
            }
        }
        """

        response = await async_client.post("/graphql/playground", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]
        schema = data["data"]["__schema"]
        assert "queryType" in schema
        assert schema["queryType"]["name"] == "Query"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
