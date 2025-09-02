# tests/integration/test_api_endpoints.py
# Integration tests for REST API endpoints
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""
Module: REST API Endpoints
Tests: All REST API endpoints integration testing
Coverage: Health, workspaces, GraphRAG operations, system operations
Dependencies: FastAPI test client
"""

import tempfile
import uuid

import pytest
from httpx import AsyncClient

from tests.fixtures.clients import async_test_client, test_client


class TestHealthEndpoints:
    """Test health and status endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_app_info(self, async_test_client: AsyncClient):
        """Test root endpoint returns application information."""
        response = await async_test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, async_test_client: AsyncClient):
        """Test health check endpoint returns healthy status."""
        response = await async_test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_info_endpoint_returns_details(self, async_test_client: AsyncClient):
        """Test info endpoint returns application details."""
        response = await async_test_client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "provider" in data


class TestWorkspaceEndpoints:
    """Test workspace management endpoints."""

    @pytest.mark.asyncio
    async def test_create_workspace_valid_data_returns_success(
        self, async_test_client: AsyncClient
    ):
        """Test creating workspace with valid data returns success."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_data = {
                "name": f"test-workspace-{uuid.uuid4().hex[:8]}",
                "description": "Integration test workspace",
                "data_path": temp_dir,
            }
            
            response = await async_test_client.post("/api/workspaces", json=workspace_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "id" in data
            assert data["config"]["name"] == workspace_data["name"]

    @pytest.mark.asyncio
    async def test_list_workspaces_returns_array(self, async_test_client: AsyncClient):
        """Test listing workspaces returns array of workspaces."""
        response = await async_test_client.get("/api/workspaces")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_workspace_invalid_id_returns_404(
        self, async_test_client: AsyncClient
    ):
        """Test getting workspace with invalid ID returns 404."""
        response = await async_test_client.get("/api/workspaces/invalid-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workspace_invalid_id_returns_404(
        self, async_test_client: AsyncClient
    ):
        """Test updating workspace with invalid ID returns 404."""
        update_data = {"description": "Updated description"}
        response = await async_test_client.put(
            "/api/workspaces/invalid-id", json=update_data
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workspace_invalid_id_returns_404(
        self, async_test_client: AsyncClient
    ):
        """Test deleting workspace with invalid ID returns 404."""
        response = await async_test_client.delete("/api/workspaces/invalid-id")
        assert response.status_code == 404


class TestGraphRAGEndpoints:
    """Test GraphRAG operation endpoints."""

    @pytest.mark.asyncio
    async def test_query_endpoint_accepts_request(self, async_test_client: AsyncClient):
        """Test query endpoint accepts valid request."""
        query_data = {
            "query": "What are the main topics?",
            "query_type": "local",
        }
        response = await async_test_client.post("/api/query", params=query_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_index_endpoint_accepts_request(self, async_test_client: AsyncClient):
        """Test index endpoint accepts valid request."""
        index_data = {
            "workspace_id": "test-workspace",
            "force_reindex": "false",
        }
        response = await async_test_client.post("/api/index", data=index_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_status(self, async_test_client: AsyncClient):
        """Test status endpoint returns indexing status."""
        response = await async_test_client.get("/api/status")
        assert response.status_code == 200


class TestGraphOperationEndpoints:
    """Test graph operation endpoints."""

    @pytest.mark.asyncio
    async def test_get_entities_returns_list(self, async_test_client: AsyncClient):
        """Test get entities endpoint returns list."""
        response = await async_test_client.get("/api/graph/entities")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)

    @pytest.mark.asyncio
    async def test_get_relationships_returns_list(self, async_test_client: AsyncClient):
        """Test get relationships endpoint returns list."""
        response = await async_test_client.get("/api/graph/relationships")
        assert response.status_code == 200
        data = response.json()
        assert "relationships" in data
        assert isinstance(data["relationships"], list)

    @pytest.mark.asyncio
    async def test_get_communities_returns_list(self, async_test_client: AsyncClient):
        """Test get communities endpoint returns list."""
        response = await async_test_client.get("/api/graph/communities")
        assert response.status_code == 200
        data = response.json()
        assert "communities" in data
        assert isinstance(data["communities"], list)

    @pytest.mark.asyncio
    async def test_graph_statistics_returns_stats(self, async_test_client: AsyncClient):
        """Test graph statistics endpoint returns stats."""
        response = await async_test_client.get("/api/graph/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "entity_count" in data
        assert "relationship_count" in data


class TestSystemOperationEndpoints:
    """Test system operation endpoints."""

    @pytest.mark.asyncio
    async def test_cache_clear_returns_success(self, async_test_client: AsyncClient):
        """Test cache clear endpoint returns success."""
        response = await async_test_client.post("/api/system/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_cache_statistics_returns_stats(self, async_test_client: AsyncClient):
        """Test cache statistics endpoint returns stats."""
        response = await async_test_client.get("/api/system/cache/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_size_bytes" in data

    @pytest.mark.asyncio
    async def test_provider_switch_accepts_request(self, async_test_client: AsyncClient):
        """Test provider switch endpoint accepts request."""
        switch_data = {
            "provider": "ollama",
            "validate_connection": False,
        }
        response = await async_test_client.post(
            "/api/system/provider/switch", json=switch_data
        )
        assert response.status_code == 200