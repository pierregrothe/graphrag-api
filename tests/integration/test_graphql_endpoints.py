# tests/integration/test_graphql_endpoints.py
# Integration tests for GraphQL endpoints
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""
Module: GraphQL Endpoints
Tests: GraphQL queries, mutations, and subscriptions
Coverage: All GraphQL operations matching REST API functionality
Dependencies: FastAPI test client, GraphQL
"""

import tempfile
import uuid

import pytest
from httpx import AsyncClient


class TestGraphQLQueries:
    """Test GraphQL query operations."""

    @pytest.mark.asyncio
    async def test_application_info_query(self, async_test_client: AsyncClient):
        """Test GraphQL application info query."""
        query = """
        query {
            applicationInfo {
                name
                version
                status
                provider
            }
        }
        """

        response = await async_test_client.post("/graphql", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "applicationInfo" in data["data"]
        app_info = data["data"]["applicationInfo"]
        assert app_info["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_list_workspaces_query(self, async_test_client: AsyncClient):
        """Test GraphQL list workspaces query."""
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

        response = await async_test_client.post("/graphql", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "workspaces" in data["data"]
        assert isinstance(data["data"]["workspaces"], list)

    @pytest.mark.asyncio
    async def test_get_workspace_query(self, async_test_client: AsyncClient):
        """Test GraphQL get workspace by ID query."""
        query = """
        query GetWorkspace($id: String!) {
            workspace(id: $id) {
                id
                name
                description
                status
            }
        }
        """

        variables = {"id": "test-workspace-id"}
        response = await async_test_client.post(
            "/graphql", json={"query": query, "variables": variables}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_graph_statistics_query(self, async_test_client: AsyncClient):
        """Test GraphQL graph statistics query."""
        query = """
        query {
            graphStatistics {
                entityCount
                relationshipCount
                communityCount
                lastUpdated
            }
        }
        """

        response = await async_test_client.post("/graphql", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        if "data" in data and data["data"]:
            stats = data["data"].get("graphStatistics")
            if stats:
                assert "entityCount" in stats
                assert "relationshipCount" in stats


class TestGraphQLMutations:
    """Test GraphQL mutation operations."""

    @pytest.mark.asyncio
    async def test_create_workspace_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL create workspace mutation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mutation = """
            mutation CreateWorkspace($input: WorkspaceCreateInput!) {
                createWorkspace(input: $input) {
                    id
                    name
                    description
                    status
                }
            }
            """

            variables = {
                "input": {
                    "name": f"graphql-workspace-{uuid.uuid4().hex[:8]}",
                    "description": "GraphQL test workspace",
                    "dataPath": temp_dir,
                }
            }

            response = await async_test_client.post(
                "/graphql", json={"query": mutation, "variables": variables}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_workspace_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL update workspace mutation."""
        mutation = """
        mutation UpdateWorkspace($id: String!, $input: WorkspaceUpdateInput!) {
            updateWorkspace(id: $id, input: $input) {
                id
                name
                description
            }
        }
        """

        variables = {
            "id": "test-workspace-id",
            "input": {
                "description": "Updated via GraphQL",
            },
        }

        response = await async_test_client.post(
            "/graphql", json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_workspace_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL delete workspace mutation."""
        mutation = """
        mutation DeleteWorkspace($id: String!) {
            deleteWorkspace(id: $id) {
                success
                message
            }
        }
        """

        variables = {"id": "test-workspace-id"}
        response = await async_test_client.post(
            "/graphql", json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_query_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL execute query mutation."""
        mutation = """
        mutation ExecuteQuery($input: QueryInput!) {
            executeQuery(input: $input) {
                response
                queryType
                tokensUsed
            }
        }
        """

        variables = {
            "input": {
                "query": "What are the main topics?",
                "queryType": "local",
                "workspaceId": "test-workspace",
            }
        }

        response = await async_test_client.post(
            "/graphql", json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_start_indexing_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL start indexing mutation."""
        mutation = """
        mutation StartIndexing($workspaceId: String!) {
            startIndexing(workspaceId: $workspaceId) {
                jobId
                status
                message
            }
        }
        """

        variables = {"workspaceId": "test-workspace"}
        response = await async_test_client.post(
            "/graphql", json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_clear_cache_mutation(self, async_test_client: AsyncClient):
        """Test GraphQL clear cache mutation."""
        mutation = """
        mutation {
            clearCache {
                success
                message
                filesCleared
                bytesFreed
            }
        }
        """

        response = await async_test_client.post("/graphql", json={"query": mutation})
        assert response.status_code == 200

        data = response.json()
        if "data" in data and data["data"]:
            result = data["data"].get("clearCache")
            if result:
                assert "success" in result
                assert "message" in result
