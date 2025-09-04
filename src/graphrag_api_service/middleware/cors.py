# src/graphrag_api_service/middleware/cors.py
# CORS middleware configuration
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""CORS middleware configuration for GraphRAG API Service."""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_cors_middleware(app: FastAPI, security_middleware: Any) -> None:
    """Set up CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        security_middleware: Security middleware instance for CORS configuration
    """
    logger.info("Setting up CORS middleware")

    # Get CORS configuration from security middleware
    cors_config = security_middleware.get_cors_config() if security_middleware else None

    if cors_config:
        app.add_middleware(CORSMiddleware, **cors_config)
        logger.info(
            f"CORS middleware configured with origins: {cors_config.get('allow_origins', [])}"
        )
    else:
        # Use default CORS configuration for testing
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug("Using default CORS configuration for testing")
