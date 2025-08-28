# tests/test_main.py
# Tests for GraphRAG API Service main module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for the main FastAPI application."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.graphrag_api_service.main import app
from src.graphrag_api_service.config import settings

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and basic endpoints."""
    
    def test_read_root(self):
        """Test root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "healthy"
        assert "docs_url" in data
        assert "redoc_url" in data
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_get_info(self):
        """Test info endpoint returns application information."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "debug" in data
        assert "log_level" in data
        assert data["app_name"] == settings.app_name
        assert data["version"] == settings.app_version


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self):
        """Test 404 error handling."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "status_code" in data
        assert data["status_code"] == 404


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_json(self):
        """Test OpenAPI JSON endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == settings.app_name
        assert data["info"]["version"] == settings.app_version
    
    def test_docs_endpoint(self):
        """Test Swagger UI docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self):
        """Test ReDoc docs endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]