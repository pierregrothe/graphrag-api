# tests/test_main.py
# Tests for GraphRAG API Service main module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for the main FastAPI application."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from src.graphrag_api_service.config import (
    API_PREFIX,
    GRAPHQL_PREFIX,
    MAX_COMMUNITY_LEVEL,
    MIN_MAX_TOKENS,
    TEST_DATA_PATH,
    Settings,
)


class TestHealthEndpoints:
    """Test health and basic endpoints."""

    def test_read_root(self, test_client: TestClient, default_settings: Settings):
        """Test root endpoint returns correct information."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "healthy"
        assert data["name"] == default_settings.app_name
        assert data["version"] == default_settings.app_version
        assert "interfaces" in data
        assert "endpoints" in data
        # Check that interfaces are properly structured
        interfaces = data["interfaces"]
        assert interfaces["rest_api"] == API_PREFIX
        assert interfaces["graphql"] == GRAPHQL_PREFIX
        assert "documentation" in interfaces

    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_get_info(self, test_client: TestClient, default_settings: Settings):
        """Test info endpoint returns application information."""
        response = test_client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "debug" in data
        assert "log_level" in data
        assert data["app_name"] == default_settings.app_name
        assert data["version"] == default_settings.app_version


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self, test_client: TestClient):
        """Test 404 error handling."""
        response = test_client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "status_code" in data
        assert data["status_code"] == 404


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_json(self, test_client: TestClient, default_settings: Settings):
        """Test OpenAPI JSON endpoint."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == default_settings.app_name
        assert data["info"]["version"] == default_settings.app_version

    def test_docs_endpoint(self, test_client: TestClient):
        """Test Swagger UI docs endpoint."""
        response = test_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self, test_client: TestClient):
        """Test ReDoc docs endpoint."""
        response = test_client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestGraphRAGEndpoints:
    """Test GraphRAG-specific endpoints using fixtures."""

    def test_graphrag_query_endpoint_without_data_path(
        self, test_client: TestClient, graphrag_query_request: dict
    ):
        """Test GraphRAG query endpoint returns 503 when GraphRAG integration not available."""
        # Use test_client which has rate limiting disabled
        response = test_client.post("/api/query", json=graphrag_query_request)
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert "GraphRAG integration not available" in data["error"]

    def test_graphrag_query_endpoint_with_data_path(
        self, test_client: TestClient, graphrag_query_request: dict
    ):
        """Test GraphRAG query endpoint with configured data path (but no GraphRAG integration)."""
        from unittest.mock import patch

        # Mock the settings to have a data path but GraphRAG integration will still be None
        with patch("src.graphrag_api_service.main.settings") as mock_settings:
            mock_settings.graphrag_data_path = TEST_DATA_PATH
            response = test_client.post("/api/query", json=graphrag_query_request)
            # Should still fail with 503 because graphrag_integration is None in test environment
            assert response.status_code == 503
            data = response.json()
            assert "error" in data
            assert "GraphRAG integration not available" in data["error"]

    def test_graphrag_index_endpoint(self, test_client: TestClient, graphrag_index_request: dict):
        """Test GraphRAG index endpoint with fixture data."""
        response = test_client.post("/api/index", json=graphrag_index_request)
        # Should fail with 503 because graphrag_integration is None in test environment
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert "GraphRAG integration not available" in data["error"]

    def test_graphrag_status_endpoint(self, test_client: TestClient):
        """Test GraphRAG status endpoint."""
        response = test_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "graphrag_configured" in data
        assert "data_path" in data
        assert "config_path" in data
        assert "llm_provider_info" in data
        assert "implementation_status" in data
        assert "available_endpoints" in data
        assert isinstance(data["available_endpoints"], list)
        assert "/api/query" in data["available_endpoints"]

    def test_graphrag_query_validation_error(self, test_client: TestClient):
        """Test GraphRAG query endpoint validation with invalid data."""
        invalid_request = {
            "query": "",  # Empty query should fail validation
            "community_level": MAX_COMMUNITY_LEVEL + 6,  # Invalid community level (above max)
            "max_tokens": MIN_MAX_TOKENS - 50,  # Below minimum
        }
        response = test_client.post("/api/query", json=invalid_request)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"] == "Validation error"

    def test_graphrag_index_missing_data_path(self, test_client: TestClient):
        """Test GraphRAG index endpoint with missing data path."""
        invalid_request = {"data_path": "", "force_reindex": False}  # Empty data path
        response = test_client.post("/api/index", json=invalid_request)
        # Should fail with 503 because graphrag_integration is None in test environment
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert "GraphRAG integration not available" in data["error"]


class TestGraphQLEndpoints:
    """Test GraphQL interface placeholder endpoints."""

    def test_graphql_info_endpoint(self, test_client: TestClient):
        """Test GraphQL info endpoint."""
        response = test_client.get("/graphql/")
        assert response.status_code == 200
        data = response.json()
        assert "interface" in data
        assert data["interface"] == "GraphQL"
        assert "status" in data
        assert data["status"] == "placeholder"
        assert "message" in data
        assert "planned_features" in data
        assert isinstance(data["planned_features"], list)
        assert "rest_api_alternative" in data
        assert data["rest_api_alternative"] == "/api"

    def test_graphql_query_placeholder(self, test_client: TestClient):
        """Test GraphQL query placeholder endpoint."""
        query_payload = {"query": "{ graphrag { status } }", "variables": {}}
        response = test_client.post("/graphql/", json=query_payload)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"] is None
        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert len(data["errors"]) > 0
        error = data["errors"][0]
        assert "message" in error
        assert "not yet implemented" in error["message"].lower()
        assert "extensions" in error
        assert "rest_endpoints" in error["extensions"]

    def test_root_endpoint_shows_interfaces(
        self, test_client: TestClient, default_settings: Settings
    ):
        """Test root endpoint shows available interfaces."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "interfaces" in data
        interfaces = data["interfaces"]
        assert "rest_api" in interfaces
        assert interfaces["rest_api"] == "/api"
        assert "graphql" in interfaces
        assert interfaces["graphql"] == "/graphql"
        assert "documentation" in interfaces
        assert "endpoints" in data
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert endpoints["health"] == "/api/health"
        assert "query" in endpoints
        assert endpoints["query"] == "/api/query"
        assert "status" in endpoints
        assert endpoints["status"] == "/api/status"
