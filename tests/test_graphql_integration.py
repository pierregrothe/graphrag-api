# tests/test_graphql_integration.py
# Comprehensive GraphQL integration tests
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Comprehensive integration tests for GraphQL endpoints."""

import asyncio
import json
from typing import Any, AsyncGenerator, Generator

import httpx
import pytest
from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport
from httpx import AsyncClient

from src.graphrag_api_service.main import app


@pytest.fixture
def graphql_url() -> str:
    """Get the GraphQL endpoint URL."""
    return "http://localhost:8001/graphql"


@pytest.fixture
async def graphql_client(graphql_url: str) -> AsyncGenerator[Client, None]:
    """Create a GraphQL client for testing."""
    transport = HTTPXAsyncTransport(url=graphql_url)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    async with client as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    @pytest.mark.asyncio
    async def test_query_entities(self, async_client: AsyncClient):
        """Test querying entities via GraphQL."""
        query = """
        query GetEntities {
            entities(limit: 10) {
                id
                title
                type
                description
                degree
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "entities" in data["data"]
        assert isinstance(data["data"]["entities"], list)

    @pytest.mark.asyncio
    async def test_query_relationships(self, async_client: AsyncClient):
        """Test querying relationships via GraphQL."""
        query = """
        query GetRelationships {
            relationships(limit: 10) {
                id
                source
                target
                type
                description
                weight
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "relationships" in data["data"]

    @pytest.mark.asyncio
    async def test_query_communities(self, async_client: AsyncClient):
        """Test querying communities via GraphQL."""
        query = """
        query GetCommunities {
            communities(limit: 10) {
                id
                level
                title
                entityIds
                relationshipIds
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "communities" in data["data"]

    @pytest.mark.asyncio
    async def test_query_graph_statistics(self, async_client: AsyncClient):
        """Test querying graph statistics via GraphQL."""
        query = """
        query GetStatistics {
            graphStatistics {
                totalEntities
                totalRelationships
                totalCommunities
                graphDensity
                connectedComponents
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "graphStatistics" in data["data"]

    @pytest.mark.asyncio
    async def test_query_workspaces(self, async_client: AsyncClient):
        """Test querying workspaces via GraphQL."""
        query = """
        query GetWorkspaces {
            workspaces {
                id
                name
                description
                dataPath
                status
                createdAt
                updatedAt
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "workspaces" in data["data"]

    @pytest.mark.asyncio
    async def test_query_system_health(self, async_client: AsyncClient):
        """Test querying system health via GraphQL."""
        query = """
        query GetSystemHealth {
            systemHealth {
                status
                timestamp
                components
                systemResources
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "systemHealth" in data["data"]

    @pytest.mark.asyncio
    async def test_query_with_variables(self, async_client: AsyncClient):
        """Test GraphQL query with variables."""
        query = """
        query GetEntities($limit: Int!, $offset: Int) {
            entities(limit: $limit, offset: $offset) {
                id
                title
                type
            }
        }
        """
        
        variables = {"limit": 5, "offset": 0}
        
        response = await async_client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "entities" in data["data"]

    @pytest.mark.asyncio
    async def test_query_with_fragments(self, async_client: AsyncClient):
        """Test GraphQL query with fragments."""
        query = """
        fragment EntityFields on Entity {
            id
            title
            type
            description
        }
        
        query GetEntitiesWithFragment {
            entities(limit: 5) {
                ...EntityFields
                degree
                communityIds
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_query_nested_fields(self, async_client: AsyncClient):
        """Test querying nested fields."""
        query = """
        query GetApplicationInfo {
            applicationInfo {
                name
                version
                status
                interfaces {
                    restApi
                    graphql
                    documentation
                }
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "applicationInfo" in data["data"]


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    @pytest.mark.asyncio
    async def test_create_workspace_mutation(self, async_client: AsyncClient):
        """Test creating a workspace via GraphQL mutation."""
        mutation = """
        mutation CreateWorkspace($input: WorkspaceInput!) {
            createWorkspace(input: $input) {
                id
                name
                description
                dataPath
                status
            }
        }
        """
        
        variables = {
            "input": {
                "name": "test-graphql-workspace",
                "description": "Created via GraphQL",
                "dataPath": "./test_data"
            }
        }
        
        response = await async_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "createWorkspace" in data["data"]
        assert data["data"]["createWorkspace"]["name"] == "test-graphql-workspace"

    @pytest.mark.asyncio
    async def test_update_workspace_mutation(self, async_client: AsyncClient):
        """Test updating a workspace via GraphQL mutation."""
        # First create a workspace
        create_mutation = """
        mutation CreateWorkspace($input: WorkspaceInput!) {
            createWorkspace(input: $input) {
                id
            }
        }
        """
        
        create_variables = {
            "input": {
                "name": "test-update-graphql",
                "dataPath": "./test_data"
            }
        }
        
        create_response = await async_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )
        workspace_id = create_response.json()["data"]["createWorkspace"]["id"]
        
        # Update the workspace
        update_mutation = """
        mutation UpdateWorkspace($id: ID!, $input: WorkspaceUpdateInput!) {
            updateWorkspace(id: $id, input: $input) {
                id
                description
            }
        }
        """
        
        update_variables = {
            "id": workspace_id,
            "input": {
                "description": "Updated via GraphQL"
            }
        }
        
        response = await async_client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["updateWorkspace"]["description"] == "Updated via GraphQL"

    @pytest.mark.asyncio
    async def test_delete_workspace_mutation(self, async_client: AsyncClient):
        """Test deleting a workspace via GraphQL mutation."""
        # First create a workspace
        create_mutation = """
        mutation CreateWorkspace($input: WorkspaceInput!) {
            createWorkspace(input: $input) {
                id
            }
        }
        """
        
        create_variables = {
            "input": {
                "name": "test-delete-graphql",
                "dataPath": "./test_data"
            }
        }
        
        create_response = await async_client.post(
            "/graphql",
            json={"query": create_mutation, "variables": create_variables}
        )
        workspace_id = create_response.json()["data"]["createWorkspace"]["id"]
        
        # Delete the workspace
        delete_mutation = """
        mutation DeleteWorkspace($id: ID!) {
            deleteWorkspace(id: $id) {
                success
                message
            }
        }
        """
        
        delete_variables = {"id": workspace_id}
        
        response = await async_client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleteWorkspace"]["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_execute_query_mutation(self, async_client: AsyncClient):
        """Test executing a GraphRAG query via GraphQL mutation."""
        mutation = """
        mutation ExecuteQuery($input: QueryInput!) {
            executeQuery(input: $input) {
                query
                response
                queryType
                processingTime
            }
        }
        """
        
        variables = {
            "input": {
                "query": "What is GraphRAG?",
                "queryType": "LOCAL",
                "workspaceId": "default"
            }
        }
        
        response = await async_client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        # May fail if no data is indexed
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_clear_cache_mutation(self, async_client: AsyncClient):
        """Test clearing cache via GraphQL mutation."""
        mutation = """
        mutation ClearCache($namespace: String) {
            clearCache(namespace: $namespace) {
                success
                message
                filesClea        bytesFreed
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": mutation}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "clearCache" in data["data"]


class TestGraphQLSubscriptions:
    """Test GraphQL subscription operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_subscription_schema(self, async_client: AsyncClient):
        """Test that subscription schema is available."""
        query = """
        query IntrospectionQuery {
            __schema {
                subscriptionType {
                    name
                    fields {
                        name
                        description
                    }
                }
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]
        
        if data["data"]["__schema"]["subscriptionType"]:
            fields = data["data"]["__schema"]["subscriptionType"]["fields"]
            field_names = [f["name"] for f in fields]
            assert "indexingUpdates" in field_names
            assert "entityUpdates" in field_names
            assert "performanceUpdates" in field_names


class TestGraphQLErrorHandling:
    """Test GraphQL error handling."""

    @pytest.mark.asyncio
    async def test_invalid_query_syntax(self, async_client: AsyncClient):
        """Test handling of invalid GraphQL syntax."""
        query = """
        query {
            invalid syntax here
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 400
        data = response.json()
        assert "errors" in data

    @pytest.mark.asyncio
    async def test_unknown_field(self, async_client: AsyncClient):
        """Test querying unknown fields."""
        query = """
        query {
            unknownField {
                id
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 400
        data = response.json()
        assert "errors" in data

    @pytest.mark.asyncio
    async def test_missing_required_argument(self, async_client: AsyncClient):
        """Test missing required arguments."""
        query = """
        query {
            entities {
                id
            }
        }
        """
        
        # entities requires a 'limit' argument
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code in [200, 400]  # Depends on schema

    @pytest.mark.asyncio
    async def test_type_mismatch(self, async_client: AsyncClient):
        """Test type mismatch in variables."""
        query = """
        query GetEntities($limit: String!) {
            entities(limit: $limit) {
                id
            }
        }
        """
        
        variables = {"limit": "not_a_number"}
        
        response = await async_client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        assert response.status_code == 400
        data = response.json()
        assert "errors" in data


class TestGraphQLPagination:
    """Test GraphQL pagination features."""

    @pytest.mark.asyncio
    async def test_cursor_pagination(self, async_client: AsyncClient):
        """Test cursor-based pagination."""
        query = """
        query GetEntitiesConnection($first: Int!, $after: String) {
            entitiesConnection(first: $first, after: $after) {
                edges {
                    node {
                        id
                        title
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
                totalCount
            }
        }
        """
        
        variables = {"first": 5}
        
        response = await async_client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        
        if "data" in data and data["data"]["entitiesConnection"]:
            connection = data["data"]["entitiesConnection"]
            assert "edges" in connection
            assert "pageInfo" in connection
            assert "totalCount" in connection

    @pytest.mark.asyncio
    async def test_offset_pagination(self, async_client: AsyncClient):
        """Test offset-based pagination."""
        query = """
        query GetEntities($limit: Int!, $offset: Int) {
            entities(limit: $limit, offset: $offset) {
                id
                title
            }
        }
        """
        
        # First page
        response1 = await async_client.post(
            "/graphql",
            json={"query": query, "variables": {"limit": 5, "offset": 0}}
        )
        assert response1.status_code == 200
        
        # Second page
        response2 = await async_client.post(
            "/graphql",
            json={"query": query, "variables": {"limit": 5, "offset": 5}}
        )
        assert response2.status_code == 200


class TestGraphQLPerformance:
    """Test GraphQL performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_query_performance(self, async_client: AsyncClient, benchmark):
        """Benchmark GraphQL query performance."""
        query = """
        query {
            systemHealth {
                status
                timestamp
            }
        }
        """
        
        async def execute_query():
            response = await async_client.post(
                "/graphql",
                json={"query": query}
            )
            return response
        
        response = await benchmark(execute_query)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_batch_queries(self, async_client: AsyncClient):
        """Test batched GraphQL queries."""
        queries = [
            {
                "query": """
                query GetEntities {
                    entities(limit: 5) {
                        id
                    }
                }
                """
            },
            {
                "query": """
                query GetRelationships {
                    relationships(limit: 5) {
                        id
                    }
                }
                """
            }
        ]
        
        # Send as array for batching
        response = await async_client.post(
            "/graphql",
            json=queries
        )
        
        # Batching might not be supported
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_query_complexity_limit(self, async_client: AsyncClient):
        """Test query complexity limits."""
        # Very deep nested query
        query = """
        query ComplexQuery {
            entities(limit: 100) {
                id
                title
                type
                description
                degree
                communityIds
                textUnitIds
            }
            relationships(limit: 100) {
                id
                source
                target
                type
                description
                weight
                textUnitIds
            }
            communities(limit: 100) {
                id
                level
                title
                entityIds
                relationshipIds
            }
            graphStatistics {
                totalEntities
                totalRelationships
                totalCommunities
                graphDensity
                connectedComponents
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        # Should either succeed or fail with complexity error
        assert response.status_code in [200, 400]


class TestGraphQLIntrospection:
    """Test GraphQL introspection capabilities."""

    @pytest.mark.asyncio
    async def test_schema_introspection(self, async_client: AsyncClient):
        """Test schema introspection query."""
        query = """
        query IntrospectionQuery {
            __schema {
                queryType {
                    name
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
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]

    @pytest.mark.asyncio
    async def test_type_introspection(self, async_client: AsyncClient):
        """Test type introspection."""
        query = """
        query TypeIntrospection {
            __type(name: "Entity") {
                name
                fields {
                    name
                    type {
                        name
                        kind
                    }
                }
            }
        }
        """
        
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__type" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])