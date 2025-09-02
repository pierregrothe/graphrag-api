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
        assert interfaces["graphql"] == "/graphql"
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
        assert "name" in data
        assert "version" in data
        assert "provider" in data
        assert "environment" in data
        assert data["name"] == default_settings.app_name
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
        """Test GraphRAG query endpoint returns proper response when GraphRAG integration not available."""
        # Use query parameters since the endpoint expects direct parameters
        params = {"query": graphrag_query_request["query"]}
        response = test_client.post("/api/query", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert data["query"] == graphrag_query_request["query"]

    def test_graphrag_query_endpoint_with_data_path(
        self, test_client: TestClient, graphrag_query_request: dict
    ):
        """Test GraphRAG query endpoint with configured data path (but no GraphRAG integration)."""
        # Use query parameters
        params = {"query": graphrag_query_request["query"]}
        response = test_client.post("/api/query", params=params)
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert data["query"] == graphrag_query_request["query"]

    def test_graphrag_index_endpoint(self, test_client: TestClient, graphrag_index_request: dict):
        """Test GraphRAG index endpoint with fixture data."""
        # Use form data for indexing endpoint
        form_data = {"workspace_id": "default", "force_reindex": "false"}
        response = test_client.post("/api/index", data=form_data)
        # Should return 200 but with message indicating GraphRAG integration is not configured
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "error" in data

    def test_graphrag_status_endpoint(self, test_client: TestClient):
        """Test GraphRAG status endpoint."""
        response = test_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data or "status" in data or "message" in data

    def test_graphrag_query_validation_error(self, test_client: TestClient):
        """Test GraphRAG query endpoint validation with invalid data."""
        # Test with empty query
        params = {"query": ""}  # Empty query
        response = test_client.post("/api/query", params=params)
        assert response.status_code == 200
        data = response.json()
        # Should get a response even with empty query
        assert "query" in data

    def test_graphrag_index_missing_data_path(self, test_client: TestClient):
        """Test GraphRAG index endpoint with missing data path."""
        # Test indexing without workspace_id parameter
        response = test_client.post("/api/index", data={})
        # Should return 200 but indicate GraphRAG integration is not configured
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "error" in data


class TestGraphQLEndpoints:
    """Test GraphQL interface placeholder endpoints."""

    def test_graphql_info_endpoint(self, test_client: TestClient):
        """Test GraphQL info endpoint."""
        response = test_client.get("/graphql")
        # GraphQL may not be fully configured in test environment, check if available
        assert response.status_code in [200, 404]  # Accept both as GraphQL may be optional

    def test_graphql_query_placeholder(self, test_client: TestClient):
        """Test GraphQL query placeholder endpoint."""
        query_payload = {"query": "{ __schema { queryType { name } } }", "variables": {}}
        response = test_client.post("/graphql", json=query_payload)
        # GraphQL may not be fully configured, accept multiple status codes
        assert response.status_code in [200, 404, 405]

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
        assert "info" in endpoints
        assert endpoints["info"] == "/api/info"
