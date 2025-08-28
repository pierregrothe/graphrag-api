# tests/test_config.py
# Tests for GraphRAG API Service configuration module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for the configuration module."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import os
from unittest.mock import patch

import pytest

from src.graphrag_api_service.config import (
    ENV_APP_NAME,
    ENV_DEBUG,
    ENV_GRAPHRAG_CONFIG_PATH,
    ENV_GRAPHRAG_DATA_PATH,
    ENV_LOG_LEVEL,
    ENV_PORT,
    TEST_CONFIG_PATH,
    TEST_DATA_PATH,
    LLMProvider,
    Settings,
)


class TestSettings:
    """Test configuration settings."""

    def test_default_settings(self, default_settings: Settings):
        """Test default configuration values (without .env file)."""
        # Use the default_settings fixture that provides clean environment
        assert default_settings.app_name == "GraphRAG API Service"
        assert default_settings.app_version == "0.1.0"
        assert default_settings.debug is False
        assert default_settings.host == "0.0.0.0"
        assert default_settings.port == 8001
        assert default_settings.log_level == "INFO"
        assert default_settings.graphrag_config_path is None
        assert default_settings.graphrag_data_path is None

    @patch.dict(
        os.environ,
        {
            ENV_APP_NAME: "Custom GraphRAG",
            ENV_DEBUG: "true",
            ENV_PORT: "9000",
            ENV_LOG_LEVEL: "DEBUG",
        },
    )
    def test_environment_override(self):
        """Test that environment variables override defaults."""
        settings = Settings()
        assert settings.app_name == "Custom GraphRAG"
        assert settings.debug is True
        assert settings.port == 9000  # Environment override should still work
        assert settings.log_level == "DEBUG"

    @patch.dict(
        os.environ,
        {ENV_GRAPHRAG_CONFIG_PATH: TEST_CONFIG_PATH, ENV_GRAPHRAG_DATA_PATH: TEST_DATA_PATH},
    )
    def test_graphrag_paths(self):
        """Test GraphRAG path configuration."""
        settings = Settings()
        assert settings.graphrag_config_path == TEST_CONFIG_PATH
        assert settings.graphrag_data_path == TEST_DATA_PATH


class TestLLMProviderConfiguration:
    """Test LLM provider configuration."""

    def test_default_ollama_provider(self, default_settings: Settings):
        """Test default Ollama provider configuration."""
        assert default_settings.llm_provider == LLMProvider.OLLAMA
        assert default_settings.is_ollama_provider() is True
        assert default_settings.is_google_gemini_provider() is False
        assert default_settings.ollama_base_url == "http://localhost:11434"
        assert default_settings.ollama_llm_model == "gemma:4b"
        assert default_settings.ollama_embedding_model == "nomic-embed-text"

    def test_google_gemini_provider(self, gemini_settings: Settings):
        """Test Google Gemini provider configuration."""
        assert gemini_settings.llm_provider == LLMProvider.GOOGLE_GEMINI
        assert gemini_settings.is_google_gemini_provider() is True
        assert gemini_settings.is_ollama_provider() is False
        assert gemini_settings.google_api_key == "test_api_key"
        assert gemini_settings.google_project_id == "test_project_id"
        assert gemini_settings.gemini_model == "gemini-2.5-flash"

    @patch.dict(os.environ, {"LLM_PROVIDER": "google_gemini", "GOOGLE_PROJECT_ID": "test_project"})
    def test_google_gemini_validation_missing_api_key(self):
        """Test validation error when Google API key is missing."""
        with pytest.raises(
            ValueError,
            match="google_api_key is required when using google_gemini provider without Vertex AI",
        ):
            Settings()

    @patch.dict(os.environ, {"LLM_PROVIDER": "google_gemini", "GOOGLE_API_KEY": "test_key"})
    def test_google_gemini_validation_missing_project_id(self):
        """Test validation error when Google project ID is missing."""
        with pytest.raises(
            ValueError, match="google_project_id is required when using google_gemini provider"
        ):
            Settings()

    def test_ollama_provider_info(self):
        """Test Ollama provider info method."""
        settings = Settings()
        provider_info = settings.get_provider_info()
        assert provider_info["provider"] == "ollama"
        assert provider_info["base_url"] == "http://localhost:11434"
        assert provider_info["llm_model"] == "gemma:4b"
        assert provider_info["embedding_model"] == "nomic-embed-text"

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_API_KEY": "test_key",
            "GOOGLE_PROJECT_ID": "test_project",
        },
    )
    def test_google_gemini_provider_info(self):
        """Test Google Gemini provider info method."""
        settings = Settings()
        provider_info = settings.get_provider_info()
        assert provider_info["provider"] == "google_gemini"
        assert provider_info["project_id"] == "test_project"
        assert provider_info["location"] == "us-central1"
        assert provider_info["llm_model"] == "gemini-2.5-flash"
        assert provider_info["use_vertex_ai"] is False
        assert provider_info["vertex_ai_endpoint"] is None
        assert provider_info["vertex_ai_location"] == "us-central1"

    @patch.dict(
        os.environ,
        {
            "OLLAMA_BASE_URL": "http://custom:8080",
            "OLLAMA_LLM_MODEL": "llama2",
            "OLLAMA_EMBEDDING_MODEL": "all-minilm",
        },
    )
    def test_custom_ollama_configuration(self):
        """Test custom Ollama configuration via environment variables."""
        settings = Settings()
        assert settings.ollama_base_url == "http://custom:8080"
        assert settings.ollama_llm_model == "llama2"
        assert settings.ollama_embedding_model == "all-minilm"

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_API_KEY": "custom_key",
            "GOOGLE_PROJECT_ID": "custom_project",
            "GEMINI_MODEL": "gemini-2.5-pro",
            "GOOGLE_LOCATION": "europe-west1",
        },
    )
    def test_custom_google_gemini_configuration(self):
        """Test custom Google Gemini configuration via environment variables."""
        settings = Settings()
        assert settings.gemini_model == "gemini-2.5-pro"
        assert settings.google_location == "europe-west1"

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_PROJECT_ID": "vertex_project",
            "GOOGLE_CLOUD_USE_VERTEX_AI": "true",
            "VERTEX_AI_LOCATION": "us-west1",
        },
    )
    def test_vertex_ai_configuration(self):
        """Test Vertex AI configuration without API key."""
        settings = Settings()
        assert settings.google_cloud_use_vertex_ai is True
        assert settings.is_vertex_ai_enabled() is True
        assert settings.vertex_ai_location == "us-west1"
        # No API key required for Vertex AI
        assert settings.google_api_key is None

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_API_KEY": "test_key",
            "GOOGLE_PROJECT_ID": "test_project",
            "GOOGLE_CLOUD_USE_VERTEX_AI": "true",
            "VERTEX_AI_ENDPOINT": "https://custom-vertex.googleapis.com",
        },
    )
    def test_vertex_ai_with_custom_endpoint(self):
        """Test Vertex AI with custom endpoint configuration."""
        settings = Settings()
        provider_info = settings.get_provider_info()
        assert provider_info["use_vertex_ai"] is True
        assert provider_info["vertex_ai_endpoint"] == "https://custom-vertex.googleapis.com"
