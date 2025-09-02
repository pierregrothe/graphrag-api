# tests/conftest.py
# Pytest fixtures for GraphRAG API Service tests
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Pytest fixtures for GraphRAG API Service test suite."""

import os
import warnings
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.main import app

# Suppress passlib bcrypt warnings
warnings.filterwarnings("ignore", message=".*bcrypt.*")
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")


# Global fixture to disable rate limiting for all tests
@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Automatically disable rate limiting for all tests."""
    with patch.dict(os.environ, {"TESTING": "true", "RATE_LIMITING_ENABLED": "false"}):
        # Also patch the security middleware to ensure rate limiting is disabled
        from src.graphrag_api_service.security.middleware import reset_security_middleware

        reset_security_middleware()
        yield


# Configuration Fixtures
@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture that provides a clean environment without any settings."""
    # Clear GraphRAG-related environment variables
    env_vars_to_clear = [
        "APP_NAME",
        "DEBUG",
        "PORT",
        "LOG_LEVEL",
        "GRAPHRAG_CONFIG_PATH",
        "GRAPHRAG_DATA_PATH",
        "LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_LLM_MODEL",
        "OLLAMA_EMBEDDING_MODEL",
        "GOOGLE_API_KEY",
        "GOOGLE_PROJECT_ID",
        "GEMINI_MODEL",
        "GOOGLE_LOCATION",
        "GOOGLE_CLOUD_USE_VERTEX_AI",
        "VERTEX_AI_ENDPOINT",
        "VERTEX_AI_LOCATION",
    ]

    # Store which ones were actually cleared
    cleared_vars = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            cleared_vars[var] = os.environ.pop(var)

    yield

    # Restore only the variables we cleared (don't touch global environment)
    for var, value in cleared_vars.items():
        os.environ[var] = value


@pytest.fixture
def default_settings(clean_env) -> Settings:
    """Fixture providing default settings without environment overrides."""
    # Use clean_env fixture to ensure no environment variables are set
    # Create settings without loading any .env file to get true defaults
    from src.graphrag_api_service.config import Settings

    return Settings()


@pytest.fixture
def ollama_settings() -> Settings:
    """Fixture providing Ollama provider configuration."""
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_LLM_MODEL": "gemma:4b",
            "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text",
        },
    ):
        return Settings()


@pytest.fixture
def gemini_settings() -> Settings:
    """Fixture providing Google Gemini provider configuration."""
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_API_KEY": "test_api_key",
            "GOOGLE_PROJECT_ID": "test_project_id",
            "GEMINI_MODEL": "gemini-2.5-flash",
        },
    ):
        return Settings()


@pytest.fixture
def vertex_ai_settings() -> Settings:
    """Fixture providing Vertex AI configuration."""
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_PROJECT_ID": "vertex_project_id",
            "GOOGLE_CLOUD_USE_VERTEX_AI": "true",
            "VERTEX_AI_LOCATION": "us-central1",
            "VERTEX_AI_ENDPOINT": "https://custom-vertex.googleapis.com",
        },
    ):
        return Settings()


@pytest.fixture
def custom_app_settings() -> Settings:
    """Fixture providing custom application configuration."""
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "Test GraphRAG API",
            "DEBUG": "true",
            "PORT": "9000",
            "LOG_LEVEL": "DEBUG",
            "GRAPHRAG_CONFIG_PATH": "/test/config",
            "GRAPHRAG_DATA_PATH": "/test/data",
        },
    ):
        return Settings()


# Provider Configuration Fixtures
@pytest.fixture
def ollama_config() -> dict[str, Any]:
    """Fixture providing Ollama provider configuration dictionary."""
    return {
        "base_url": "http://localhost:11434",
        "llm_model": "gemma:4b",
        "embedding_model": "nomic-embed-text",
    }


@pytest.fixture
def gemini_config() -> dict[str, Any]:
    """Fixture providing Gemini provider configuration dictionary."""
    return {
        "api_key": "test_api_key",
        "project_id": "test_project_id",
        "model": "gemini-2.5-flash",
        "embedding_model": "text-embedding-004",
        "location": "us-central1",
        "use_vertex_ai": False,
        "vertex_ai_endpoint": None,
        "vertex_ai_location": "us-central1",
    }


@pytest.fixture
def vertex_ai_config() -> dict[str, Any]:
    """Fixture providing Vertex AI provider configuration dictionary."""
    return {
        "api_key": None,
        "project_id": "vertex_project_id",
        "model": "gemini-2.5-flash",
        "embedding_model": "text-embedding-004",
        "location": "us-central1",
        "use_vertex_ai": True,
        "vertex_ai_endpoint": "https://custom-vertex.googleapis.com",
        "vertex_ai_location": "us-central1",
    }


# FastAPI Test Client Fixtures
@pytest.fixture
def test_client() -> TestClient:
    """Fixture providing FastAPI test client with data paths configured."""
    from src.graphrag_api_service.security.middleware import (
        get_security_middleware,
        reset_security_middleware,
    )

    with patch.dict(
        os.environ,
        {
            "GRAPHRAG_DATA_PATH": "/test/data",
            "GRAPHRAG_CONFIG_PATH": "/test/config",
            "TESTING": "true",  # Disable rate limiting for tests
            "RATE_LIMITING_ENABLED": "false",
        },
    ):
        # Reset security middleware to pick up new environment variables
        reset_security_middleware()

        # Verify that rate limiting is disabled
        middleware = get_security_middleware()
        assert middleware.rate_limiter is None, "Rate limiter should be disabled for tests"

        return TestClient(app)


@pytest.fixture
def authenticated_client() -> TestClient:
    """Fixture providing authenticated FastAPI test client (future use)."""
    from src.graphrag_api_service.security.middleware import (
        get_security_middleware,
        reset_security_middleware,
    )

    # Placeholder for when authentication is implemented
    with patch.dict(
        os.environ,
        {
            "GRAPHRAG_DATA_PATH": "/test/data",
            "GRAPHRAG_CONFIG_PATH": "/test/config",
            "TESTING": "true",  # Disable rate limiting for tests
            "RATE_LIMITING_ENABLED": "false",
        },
    ):
        # Reset security middleware to pick up new environment variables
        reset_security_middleware()

        # Verify that rate limiting is disabled
        middleware = get_security_middleware()
        assert middleware.rate_limiter is None, "Rate limiter should be disabled for tests"

        client = TestClient(app)
        # Future: Add authentication headers
        return client


# Mock Response Fixtures
@pytest.fixture
def mock_ollama_response() -> dict[str, Any]:
    """Fixture providing mock Ollama API response."""
    return {
        "response": "This is a test response from Ollama.",
        "context": [1, 2, 3, 4, 5],
        "created_at": "2025-08-28T12:00:00.000000Z",
        "model": "gemma:4b",
        "done": True,
        "total_duration": 1000000000,
        "load_duration": 100000000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 200000000,
        "eval_count": 20,
        "eval_duration": 700000000,
    }


@pytest.fixture
def mock_ollama_embedding_response() -> dict[str, Any]:
    """Fixture providing mock Ollama embedding response."""
    return {
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 256,  # 1280 dimensions
        "model": "nomic-embed-text",
        "created_at": "2025-08-28T12:00:00.000000Z",
    }


@pytest.fixture
def mock_gemini_response() -> dict[str, Any]:
    """Fixture providing mock Gemini API response structure."""
    return {
        "text": "This is a test response from Gemini.",
        "finish_reason": "STOP",
        "safety_ratings": [],
        "token_count": 25,
        "grounding_attributions": [],
    }


@pytest.fixture
def mock_gemini_embedding_response() -> dict[str, Any]:
    """Fixture providing mock Gemini embedding response."""
    return {"embedding": {"values": [0.1, 0.2, 0.3, 0.4, 0.5] * 154}}  # 770 dimensions


# Error Scenario Fixtures
@pytest.fixture
def connection_error_config() -> dict[str, Any]:
    """Fixture providing configuration that will cause connection errors."""
    return {
        "base_url": "http://nonexistent:9999",
        "llm_model": "nonexistent:model",
        "embedding_model": "nonexistent-embed",
    }


@pytest.fixture
def invalid_api_key_config() -> dict[str, Any]:
    """Fixture providing invalid API key configuration."""
    return {
        "api_key": "invalid_api_key",
        "project_id": "invalid_project_id",
        "model": "gemini-2.5-flash",
        "embedding_model": "text-embedding-004",
        "location": "us-central1",
        "use_vertex_ai": False,
        "vertex_ai_endpoint": None,
        "vertex_ai_location": "us-central1",
    }


# Sample Data Fixtures
@pytest.fixture
def sample_queries() -> list[str]:
    """Fixture providing sample queries for testing."""
    return [
        "What is the main topic of this document?",
        "Summarize the key findings.",
        "What are the recommendations?",
        "How does this relate to previous research?",
        "What are the limitations of this study?",
    ]


@pytest.fixture
def sample_documents() -> list[str]:
    """Fixture providing sample documents for indexing tests."""
    return [
        "This is a sample document about artificial intelligence and machine learning.",
        "GraphRAG combines knowledge graphs with retrieval-augmented generation.",
        "The future of AI involves better integration with structured knowledge.",
        "Natural language processing has made significant advances in recent years.",
        "Large language models are transforming how we interact with information.",
    ]


@pytest.fixture
def graphrag_query_request() -> dict[str, Any]:
    """Fixture providing GraphRAG query request payload."""
    return {
        "query": "What is the main topic discussed in the documents?",
        "community_level": 2,
        "response_type": "multiple paragraphs",
        "max_tokens": 1500,
    }


@pytest.fixture
def graphrag_index_request() -> dict[str, Any]:
    """Fixture providing GraphRAG index request payload."""
    return {
        "data_path": "/test/data/documents",
        "config_path": "/test/config/graphrag.yaml",
        "force_reindex": False,
    }


# Async Fixtures for Provider Testing
@pytest.fixture
def event_loop():
    """Fixture providing event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
