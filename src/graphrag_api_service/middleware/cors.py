# src/graphrag_api_service/middleware/cors.py
# CORS middleware configuration
# Author: Pierre Grothé
# Creation Date: 2025-08-29
# Updated: 2025-09-05 - Enhanced with production-ready CORS security

"""CORS middleware configuration for GraphRAG API Service."""

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..logging_config import get_logger

logger = get_logger(__name__)


def get_production_cors_config() -> dict[str, Any]:
    """Get production-ready CORS configuration."""
    # Get allowed origins from environment variable
    allowed_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")

    if allowed_origins_env:
        # Parse comma-separated origins from environment
        allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
    else:
        # Default production origins (should be configured in production)
        allowed_origins = [
            "https://localhost:3000",
            "https://127.0.0.1:3000",
            "https://localhost:8080",
            "https://127.0.0.1:8080",
        ]

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
            "HEAD",
        ],
        "allow_headers": [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
            "Cache-Control",
            "Pragma",
        ],
        "expose_headers": [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-RateLimit-Window",
        ],
        "max_age": 86400,  # 24 hours
    }


def get_development_cors_config() -> dict[str, Any]:
    """Get development CORS configuration (more permissive)."""
    return {
        "allow_origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:5173",
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 600,  # 10 minutes
    }


def get_testing_cors_config() -> dict[str, Any]:
    """Get testing CORS configuration (most permissive)."""
    return {
        "allow_origins": ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 0,  # No caching for tests
    }


def setup_cors_middleware(app: FastAPI, security_middleware: Any = None) -> None:
    """Set up CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        security_middleware: Security middleware instance for CORS configuration
    """
    logger.info("Setting up CORS middleware")

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Get CORS configuration from security middleware first
    cors_config = None
    if security_middleware and hasattr(security_middleware, "get_cors_config"):
        cors_config = security_middleware.get_cors_config()

    # If no security middleware config, use environment-based config
    if not cors_config:
        if environment == "production":
            cors_config = get_production_cors_config()
            logger.info("Using production CORS configuration")
        elif environment == "testing":
            cors_config = get_testing_cors_config()
            logger.info("Using testing CORS configuration")
        else:
            cors_config = get_development_cors_config()
            logger.info("Using development CORS configuration")

    # Apply CORS middleware
    app.add_middleware(CORSMiddleware, **cors_config)

    # Log configuration details
    origins = cors_config.get("allow_origins", [])
    if origins == ["*"]:
        logger.warning("CORS configured to allow all origins - not recommended for production")
    else:
        logger.info(f"CORS middleware configured with origins: {origins}")

    logger.info(f"CORS allows credentials: {cors_config.get('allow_credentials', False)}")
    logger.info(f"CORS max age: {cors_config.get('max_age', 0)} seconds")
