# tests/test_logging_config.py
# Tests for GraphRAG API Service logging configuration module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for the logging configuration module."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import logging
from unittest.mock import patch

from src.graphrag_api_service.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    """Test logging configuration."""

    def test_setup_logging(self):
        """Test logging setup."""
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0

    @patch("src.graphrag_api_service.logging_config.settings")
    def test_debug_log_level(self, mock_settings):
        """Test debug log level configuration."""
        mock_settings.log_level = "DEBUG"
        mock_settings.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_get_logger(self):
        """Test logger creation."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_hierarchy(self):
        """Test logger hierarchy."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        assert child_logger.parent == parent_logger
