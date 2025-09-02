# tests/unit/test_config.py
# Unit tests for configuration module
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""
Module: Configuration
Tests: Settings validation, environment variable loading, provider configuration
Coverage: Default settings, environment overrides, provider-specific settings
Dependencies: None
"""

import os
from unittest.mock import patch

import pytest

from src.graphrag_api_service.config import LLMProvider, Settings


class TestConfigurationSettings:
    """Test configuration settings and environment variables."""

    def test_default_settings_loads_correctly(self):
        """Test that default settings load with expected values."""
        settings = Settings()
        assert settings.app_name == "GraphRAG API Service"
        assert settings.app_version == "0.1.0"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8001

    def test_environment_override_works(self):
        """Test that environment variables override default settings."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Custom App",
                "PORT": "9000",
                "DEBUG": "true",
            },
        ):
            settings = Settings()
            assert settings.app_name == "Custom App"
            assert settings.port == 9000
            assert settings.debug is True

    def test_graphrag_paths_configuration(self):
        """Test GraphRAG data and config path settings."""
        test_data_path = "/test/data"
        test_config_path = "/test/config"
        
        with patch.dict(
            os.environ,
            {
                "GRAPHRAG_DATA_PATH": test_data_path,
                "GRAPHRAG_CONFIG_PATH": test_config_path,
            },
        ):
            settings = Settings()
            assert settings.graphrag_data_path == test_data_path
            assert settings.graphrag_config_path == test_config_path


class TestLLMProviderConfiguration:
    """Test LLM provider configuration."""

    def test_ollama_provider_default_configuration(self):
        """Test default Ollama provider configuration."""
        settings = Settings()
        assert settings.llm_provider == LLMProvider.OLLAMA
        assert settings.is_ollama_provider() is True
        assert settings.ollama_base_url == "http://localhost:11434"

    def test_google_gemini_provider_configuration(self):
        """Test Google Gemini provider configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google_gemini",
                "GOOGLE_API_KEY": "test_key",
                "GOOGLE_PROJECT_ID": "test_project",
            },
        ):
            settings = Settings()
            assert settings.llm_provider == LLMProvider.GOOGLE_GEMINI
            assert settings.is_google_gemini_provider() is True
            assert settings.google_api_key == "test_key"
            assert settings.google_project_id == "test_project"

    def test_provider_validation_missing_google_api_key(self):
        """Test validation error when Google API key is missing."""
        from pydantic_settings import SettingsConfigDict

        class TestSettings(Settings):
            model_config = SettingsConfigDict(
                case_sensitive=False,
                env_file=None,
                env_file_encoding="utf-8",
            )

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google_gemini",
                "GOOGLE_PROJECT_ID": "test_project",
                "GOOGLE_CLOUD_USE_VERTEX_AI": "false",
            },
        ):
            with pytest.raises(
                ValueError,
                match="google_api_key is required when using google_gemini provider",
            ):
                TestSettings()

    def test_provider_info_method_returns_correct_data(self):
        """Test that get_provider_info returns correct provider information."""
        settings = Settings()
        info = settings.get_provider_info()
        
        assert "provider" in info
        assert info["provider"] == "ollama"
        assert "base_url" in info or "project_id" in info