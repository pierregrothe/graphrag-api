# src/graphrag_api_service/middleware/cors.py
# CORS middleware configuration
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""CORS middleware configuration for GraphRAG API Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_cors_middleware(app: FastAPI, security_middleware) -> None:
    """Setup CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        security_middleware: Security middleware instance for CORS configuration
    """
    logger.info("Setting up CORS middleware")

    # Get CORS configuration from security middleware
    cors_config = security_middleware.get_cors_config()

    if cors_config:
        app.add_middleware(CORSMiddleware, **cors_config)
        logger.info(
            f"CORS middleware configured with origins: {cors_config.get('allow_origins', [])}"
        )
    else:
        logger.warning("No CORS configuration found")
