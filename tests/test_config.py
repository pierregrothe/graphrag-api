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

from src.graphrag_api_service.config import LLMProvider, Settings


class TestSettings:
    """Test configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        assert settings.app_name == "GraphRAG API Service"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8001
        assert settings.log_level == "INFO"
        assert settings.graphrag_config_path is None
        assert settings.graphrag_data_path is None

    @patch.dict(
        os.environ,
        {"APP_NAME": "Custom GraphRAG", "DEBUG": "true", "PORT": "9000", "LOG_LEVEL": "DEBUG"},
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
        {"GRAPHRAG_CONFIG_PATH": "/path/to/config", "GRAPHRAG_DATA_PATH": "/path/to/data"},
    )
    def test_graphrag_paths(self):
        """Test GraphRAG path configuration."""
        settings = Settings()
        assert settings.graphrag_config_path == "/path/to/config"
        assert settings.graphrag_data_path == "/path/to/data"


class TestLLMProviderConfiguration:
    """Test LLM provider configuration."""

    def test_default_ollama_provider(self):
        """Test default Ollama provider configuration."""
        settings = Settings()
        assert settings.llm_provider == LLMProvider.OLLAMA
        assert settings.is_ollama_provider() is True
        assert settings.is_google_gemini_provider() is False
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_llm_model == "gemma:4b"
        assert settings.ollama_embedding_model == "nomic-embed-text"

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "google_gemini",
            "GOOGLE_API_KEY": "test_key",
            "GOOGLE_PROJECT_ID": "test_project",
        },
    )
    def test_google_gemini_provider(self):
        """Test Google Gemini provider configuration."""
        settings = Settings()
        assert settings.llm_provider == LLMProvider.GOOGLE_GEMINI
        assert settings.is_google_gemini_provider() is True
        assert settings.is_ollama_provider() is False
        assert settings.google_api_key == "test_key"
        assert settings.google_project_id == "test_project"
        assert settings.gemini_model == "gemini-2.5-flash"

    @patch.dict(os.environ, {"LLM_PROVIDER": "google_gemini"})
    def test_google_gemini_validation_missing_api_key(self):
        """Test validation error when Google API key is missing."""
        with pytest.raises(ValueError, match="google_api_key is required"):
            Settings()

    @patch.dict(os.environ, {"LLM_PROVIDER": "google_gemini", "GOOGLE_API_KEY": "test_key"})
    def test_google_gemini_validation_missing_project_id(self):
        """Test validation error when Google project ID is missing."""
        with pytest.raises(ValueError, match="google_project_id is required"):
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
