# src/graphrag_api_service/main.py
# Main FastAPI application for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Main FastAPI application module for GraphRAG API service."""

from fastapi import FastAPI

from .config import API_PREFIX, GRAPHQL_PREFIX, settings
from .dependencies import get_service_container, lifespan
from .logging_config import get_logger, setup_logging
from .middleware import setup_auth_middleware, setup_cors_middleware, setup_error_handlers

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A FastAPI-based API for the microsoft/graphrag library with REST API and GraphQL interfaces",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Get service container
    container = get_service_container()

    # Setup middleware
    setup_cors_middleware(app, container.security_middleware)
    setup_auth_middleware(app, container.security_middleware, container.performance_middleware)
    setup_error_handlers(app)

    # Setup route handlers with dependency injection
    from .routes.graph_v2 import router as graph_router
    from .routes.graphrag_v2 import router as graphrag_router
    from .routes.indexing_v2 import router as indexing_router
    from .routes.system_v2 import router as system_router
    from .routes.workspace_v2 import router as workspace_router

    # Register all v2 routers with dependency injection
    app.include_router(workspace_router)
    app.include_router(graphrag_router)
    app.include_router(graph_router)
    app.include_router(system_router)  # Now includes health endpoints
    app.include_router(indexing_router)

    # Setup GraphQL router
    from .graphql import create_graphql_router

    graphql_router = create_graphql_router(
        graph_operations=container.graph_operations,
        workspace_manager=container.workspace_manager,
        system_operations=container.system_operations,
        graphrag_integration=container.graphrag_integration,
        indexing_manager=container.indexing_manager,
    )
    app.include_router(graphql_router, prefix=GRAPHQL_PREFIX)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint providing API information."""
        logger.info("Root endpoint accessed")
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "healthy",
            "interfaces": {
                "rest_api": API_PREFIX,
                "graphql": GRAPHQL_PREFIX,
                "documentation": {
                    "swagger_ui": "/docs",
                    "redoc": "/redoc",
                    "openapi_json": "/openapi.json",
                },
            },
            "endpoints": {
                "health": "/api/health",
                "info": "/api/info",
                "query": "/api/query",
                "index": "/api/index",
                "workspaces": "/api/workspaces",
                "indexing_jobs": "/api/indexing/jobs",
                "graph": "/api/graph",
            },
        }

    return app


# Create the FastAPI application
app = create_app()
