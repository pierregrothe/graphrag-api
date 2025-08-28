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

from src.graphrag_api_service.config import Settings


class TestSettings:
    """Test configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        assert settings.app_name == "GraphRAG API Service"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
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
        assert settings.port == 9000
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
