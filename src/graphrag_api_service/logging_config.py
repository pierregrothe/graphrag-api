# src/graphrag_api_service/logging_config.py
# Logging configuration for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Logging configuration and setup for the GraphRAG API service."""

import logging
import sys

from .config import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    # Create formatter
    formatter = logging.Formatter(settings.log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name, typically __name__

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
