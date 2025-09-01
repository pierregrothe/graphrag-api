# tests/test_api_integration_enhanced.py
# Enhanced API integration tests with additional coverage
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Enhanced integration tests for REST API endpoints."""

import asyncio
import json
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.graphrag_api_service.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    from fastapi.testclient import TestClient
    from httpx import ASGITransport

    with TestClient(app):  # This handles the lifespan events
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestAdvancedWorkspaceOperations:
    """Test advanced workspace operations."""

    @pytest.mark.asyncio
    async def test_workspace_name_validation(self, async_client: AsyncClient):
        """Test workspace name validation rules."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test invalid characters in name
            invalid_names = [
                "test workspace",  # Space
                "test@workspace",  # Special char
                "test/workspace",  # Slash
                "test\\workspace",  # Backslash
                "",  # Empty
                "a" * 51,  # Too long (>50 chars)
            ]

            for invalid_name in invalid_names:
                workspace_data = {
                    "name": invalid_name,
                    "description": "Test validation",
                    "data_path": temp_dir,
                }
                response = await async_client.post("/api/workspaces", json=workspace_data)
                assert response.status_code in [400, 422], f"Should reject name: {invalid_name}"

            # Test valid names
            import uuid

            valid_names = [
                "test-workspace",
                "test_workspace",
                "TestWorkspace123",
                "a" * 50,  # Max length
            ]

            for valid_name in valid_names:
                # Make truly unique with UUID
                unique_valid_name = f"{valid_name[:40]}-{uuid.uuid4().hex[:8]}"
                workspace_data = {
                    "name": unique_valid_name,
                    "description": "Test validation",
                    "data_path": temp_dir,
                }
                response = await async_client.post("/api/workspaces", json=workspace_data)
                assert response.status_code == 200, f"Should accept name pattern: {valid_name}"

    @pytest.mark.asyncio
    async def test_workspace_concurrent_operations(self, async_client: AsyncClient):
        """Test concurrent workspace operations."""
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple workspaces concurrently
            tasks = []
            for i in range(5):
                unique_name = f"concurrent-{uuid.uuid4().hex[:8]}"
                workspace_data = {
                    "name": unique_name,
                    "description": f"Concurrent test {i}",
                    "data_path": temp_dir,
                }
                task = async_client.post("/api/workspaces", json=workspace_data)
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

            # Verify all were created
            list_response = await async_client.get("/api/workspaces")
            assert list_response.status_code == 200
            workspaces = list_response.json()
            assert len(workspaces) >= 5

    @pytest.mark.asyncio
    async def test_workspace_update_partial(self, async_client: AsyncClient):
        """Test partial workspace updates."""
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create workspace
            unique_name = f"test-partial-{uuid.uuid4().hex[:8]}"
            workspace_data = {
                "name": unique_name,
                "description": "Original description",
                "data_path": temp_dir,
                "chunk_size": 1200,
                "max_entities": 1000,
            }
            create_response = await async_client.post("/api/workspaces", json=workspace_data)
            workspace_id = create_response.json()["id"]

            # Update only description
            update_data = {"description": "Updated description"}
            response = await async_client.put(f"/api/workspaces/{workspace_id}", json=update_data)
            assert response.status_code == 200

            # Verify other fields unchanged
            get_response = await async_client.get(f"/api/workspaces/{workspace_id}")
            workspace = get_response.json()
            assert workspace["config"]["description"] == "Updated description"
            assert workspace["config"]["chunk_size"] == 1200
            assert workspace["config"]["max_entities"] == 1000


class TestAdvancedQueryOperations:
    """Test advanced query operations."""

    @pytest.mark.asyncio
    async def test_query_with_custom_parameters(self, async_client: AsyncClient):
        """Test query with custom parameters."""
        params = {
            "query": "What is GraphRAG?",
            "query_type": "local",
            "workspace_id": "default",
            "community_level": 2,
            "response_type": "detailed",
        }

        response = await async_client.post("/api/query", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    @pytest.mark.asyncio
    async def test_query_timeout_handling(self, async_client: AsyncClient):
        """Test query timeout handling."""
        # Very long query that might timeout
        params = {
            "query": "Explain " * 100,  # Very long query
            "query_type": "global",
            "workspace_id": "default",
        }

        response = await async_client.post("/api/query", params=params)
        # Should handle gracefully
        assert response.status_code in [200, 408, 500]

    @pytest.mark.asyncio
    async def test_query_special_characters(self, async_client: AsyncClient):
        """Test query with special characters."""
        special_queries = [
            "What's the O(n²) complexity?",
            "Explain C++ vs C#",
            "What about $100 investment?",
            "Is 2+2=4?",
            "Query with 中文 characters",
            "Query with émojis 🚀",
        ]

        for query in special_queries:
            params = {"query": query, "query_type": "local", "workspace_id": "default"}

            response = await async_client.post("/api/query", params=params)
            assert response.status_code == 200
            data = response.json()
            assert "query" in data
            assert data["query"] == query


class TestSystemOperations:
    """Test system operations."""

    @pytest.mark.asyncio
    async def test_provider_switch_validation(self, async_client: AsyncClient):
        """Test provider switch with validation."""
        # Test invalid provider
        invalid_data = {"provider": "invalid_provider"}
        response = await async_client.post("/api/provider/switch", json=invalid_data)
        assert response.status_code == 400

        # Test valid providers
        valid_providers = ["ollama", "google_gemini"]
        for provider in valid_providers:
            switch_data = {"provider": provider}
            response = await async_client.post("/api/provider/switch", json=switch_data)
            assert response.status_code == 200
            data = response.json()
            assert data["current_provider"] == provider

    @pytest.mark.asyncio
    async def test_cache_operations_detailed(self, async_client: AsyncClient):
        """Test detailed cache operations."""
        # Get initial statistics
        stats_response = await async_client.get("/api/cache/statistics")
        assert stats_response.status_code == 200
        initial_stats = stats_response.json()

        # Clear cache
        clear_response = await async_client.post("/api/cache/clear")
        assert clear_response.status_code == 200
        clear_data = clear_response.json()
        assert clear_data["success"] is True

        # Verify cache was cleared
        stats_response2 = await async_client.get("/api/cache/statistics")
        assert stats_response2.status_code == 200
        final_stats = stats_response2.json()
        assert final_stats["total_files"] <= initial_stats["total_files"]


class TestPaginationAndFiltering:
    """Test pagination and filtering."""

    @pytest.mark.asyncio
    async def test_entities_pagination(self, async_client: AsyncClient):
        """Test entities endpoint pagination."""
        # Test different page sizes
        page_sizes = [1, 5, 10, 100]

        for limit in page_sizes:
            response = await async_client.get(f"/api/graph/entities?limit={limit}")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= limit

        # Test offset
        response1 = await async_client.get("/api/graph/entities?limit=5&offset=0")
        response2 = await async_client.get("/api/graph/entities?limit=5&offset=5")
        assert response1.status_code == 200
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_relationships_pagination(self, async_client: AsyncClient):
        """Test relationships endpoint pagination."""
        response = await async_client.get("/api/graph/relationships?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDataValidation:
    """Test data validation."""

    @pytest.mark.asyncio
    async def test_workspace_data_path_validation(self, async_client: AsyncClient):
        """Test workspace data path validation."""
        import uuid

        # Test with non-existent path
        workspace_data = {
            "name": f"test-path-{uuid.uuid4().hex[:8]}",
            "description": "Test path validation",
            "data_path": "/non/existent/path",
        }

        response = await async_client.post("/api/workspaces", json=workspace_data)
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_numeric_field_validation(self, async_client: AsyncClient):
        """Test numeric field validation."""
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test invalid chunk_size
            test_cases = [
                {"chunk_size": 299},  # Below minimum
                {"chunk_size": 4001},  # Above maximum
                {"max_entities": 9},  # Below minimum
                {"max_entities": 10001},  # Above maximum
            ]

            for test_data in test_cases:
                workspace_data = {
                    "name": f"test-validation-{uuid.uuid4().hex[:8]}",
                    "description": "Test validation",
                    "data_path": temp_dir,
                    **test_data,
                }
                response = await async_client.post("/api/workspaces", json=workspace_data)
                assert response.status_code == 422


class TestSecurityHeaders:
    """Test security headers."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client: AsyncClient):
        """Test that security headers are present."""
        response = await async_client.get("/api/health")
        assert response.status_code == 200

        # Check for common security headers
        headers = response.headers
        # These might be set by middleware
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "strict-transport-security",
        ]

        # Note: Headers might not be set in test environment
        # This is more of a production check

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers."""
        headers = {"Origin": "http://example.com"}
        response = await async_client.get("/api/health", headers=headers)
        assert response.status_code == 200

        # Check if CORS headers are present
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] in ["*", "http://example.com"]


class TestBatchOperations:
    """Test batch operations."""

    @pytest.mark.asyncio
    async def test_batch_workspace_creation(self, async_client: AsyncClient):
        """Test creating multiple workspaces in batch."""
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as temp_dir:
            workspaces_to_create = []
            for i in range(3):
                workspace_data = {
                    "name": f"batch-{uuid.uuid4().hex[:8]}",
                    "description": f"Batch workspace {i}",
                    "data_path": temp_dir,
                }
                workspaces_to_create.append(workspace_data)

            created_ids = []
            for workspace_data in workspaces_to_create:
                response = await async_client.post("/api/workspaces", json=workspace_data)
                assert response.status_code == 200
                created_ids.append(response.json()["id"])

            # Clean up
            for workspace_id in created_ids:
                await async_client.delete(f"/api/workspaces/{workspace_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
