# src/graphrag_api_service/main.py
# Main FastAPI application for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Main FastAPI application module for GraphRAG API service."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import API_PREFIX, GRAPHQL_PREFIX, settings
from .logging_config import get_logger, setup_logging
from .providers import register_providers

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Register LLM providers
    register_providers()
    logger.info("LLM providers registered successfully")

    yield
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A FastAPI-based API for the microsoft/graphrag library with REST API and GraphQL interfaces",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Create API router for REST endpoints
api_router = APIRouter(prefix=API_PREFIX, tags=["REST API"])
# Create GraphQL router for GraphQL endpoints
graphql_router = APIRouter(prefix=GRAPHQL_PREFIX, tags=["GraphQL API"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Root endpoints (not under /api prefix)
@app.get("/", tags=["Root"])
async def read_root() -> dict[str, Any]:
    """Root endpoint providing basic API information and available interfaces.

    Returns:
        Dict containing API name, version, status, and available interfaces
    """
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
            "status": "/api/status",
            "query": "/api/query",
            "index": "/api/index",
        },
    }


# REST API endpoints under /api prefix
@api_router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict containing health status
    """
    logger.debug("Health check accessed")
    return {"status": "healthy"}


@api_router.get("/info", tags=["Information"])
async def get_info() -> dict[str, Any]:
    """Get application information and configuration.

    Returns:
        Dict containing application information
    """
    logger.info("Info endpoint accessed")
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "graphrag_config_path": settings.graphrag_config_path,
        "graphrag_data_path": settings.graphrag_data_path,
        "llm_provider_info": settings.get_provider_info(),
    }


# Pydantic models for GraphRAG endpoints
class QueryRequest(BaseModel):
    """Request model for GraphRAG query endpoint."""

    query: str = Field(..., description="The question or query to ask")
    community_level: int = Field(
        default=2, ge=0, le=4, description="Community level for hierarchical search (0-4)"
    )
    response_type: str = Field(
        default="multiple paragraphs",
        description="Type of response format (e.g., 'multiple paragraphs', 'single paragraph', 'single sentence')",
    )
    max_tokens: int = Field(default=1500, ge=100, le=4000, description="Maximum tokens in response")


class QueryResponse(BaseModel):
    """Response model for GraphRAG query endpoint."""

    answer: str = Field(..., description="The answer to the query")
    sources: list[str] = Field(default_factory=list, description="Source references used")
    community_level: int = Field(..., description="Community level used for the query")
    tokens_used: int = Field(default=0, description="Number of tokens used in the response")


class IndexRequest(BaseModel):
    """Request model for GraphRAG indexing endpoint."""

    data_path: str = Field(..., description="Path to the data directory to index")
    config_path: str | None = Field(
        None, description="Optional path to GraphRAG configuration file"
    )
    force_reindex: bool = Field(
        default=False, description="Whether to force reindexing existing data"
    )


class IndexResponse(BaseModel):
    """Response model for GraphRAG indexing endpoint."""

    status: str = Field(..., description="Status of the indexing operation")
    message: str = Field(..., description="Detailed message about the operation")
    files_processed: int = Field(default=0, description="Number of files processed")
    entities_extracted: int = Field(default=0, description="Number of entities extracted")
    relationships_extracted: int = Field(default=0, description="Number of relationships extracted")


# GraphRAG REST API endpoints
@api_router.post("/query", response_model=QueryResponse, tags=["GraphRAG"])
async def query_graphrag(request: QueryRequest) -> QueryResponse:
    """Query the GraphRAG system with a question.

    This endpoint allows you to ask questions against your indexed knowledge graph.
    The system will use the graph structure to provide comprehensive answers.

    Args:
        request: Query request containing the question and parameters

    Returns:
        QueryResponse containing the answer and metadata

    Raises:
        HTTPException: If GraphRAG is not configured or query fails
    """
    logger.info(f"GraphRAG query received: {request.query[:100]}...")

    # Check if GraphRAG is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    # TODO: Implement actual GraphRAG query logic
    # This is a placeholder implementation
    logger.warning("GraphRAG query endpoint is not yet fully implemented")

    return QueryResponse(
        answer=f"This is a placeholder response for query: '{request.query}'. GraphRAG integration is not yet implemented.",
        sources=["placeholder_source.txt"],
        community_level=request.community_level,
        tokens_used=len(request.query.split()) * 2,  # Rough estimate
    )


@api_router.post("/index", response_model=IndexResponse, tags=["GraphRAG"])
async def index_data(request: IndexRequest) -> IndexResponse:
    """Index data using GraphRAG.

    This endpoint processes documents and creates a knowledge graph with entities,
    relationships, and communities for efficient retrieval.

    Args:
        request: Index request containing data path and configuration

    Returns:
        IndexResponse containing the status and statistics

    Raises:
        HTTPException: If indexing fails or paths are invalid
    """
    logger.info(f"GraphRAG indexing requested for path: {request.data_path}")

    # Basic validation
    if not request.data_path:
        raise HTTPException(status_code=400, detail="Data path is required")

    # TODO: Implement actual GraphRAG indexing logic
    # This is a placeholder implementation
    logger.warning("GraphRAG indexing endpoint is not yet fully implemented")

    return IndexResponse(
        status="completed",
        message=f"Placeholder indexing completed for {request.data_path}. Actual GraphRAG integration pending.",
        files_processed=0,
        entities_extracted=0,
        relationships_extracted=0,
    )


@api_router.get("/status", tags=["GraphRAG"])
async def get_graphrag_status() -> dict[str, Any]:
    """Get GraphRAG system status and configuration.

    Returns:
        Dict containing GraphRAG configuration and status information
    """
    logger.info("GraphRAG status requested")

    return {
        "graphrag_configured": bool(settings.graphrag_data_path),
        "data_path": settings.graphrag_data_path,
        "config_path": settings.graphrag_config_path,
        "llm_provider_info": settings.get_provider_info(),
        "implementation_status": "multi-provider configuration implemented",
        "available_endpoints": [
            "/api/query",
            "/api/index",
            "/api/status",
        ],
    }


# GraphQL placeholder endpoints
@graphql_router.get("/", tags=["GraphQL"])
async def graphql_info() -> dict[str, Any]:
    """GraphQL interface information endpoint.

    Returns:
        Dict containing GraphQL interface information and status
    """
    logger.info("GraphQL info endpoint accessed")
    return {
        "interface": "GraphQL",
        "status": "placeholder",
        "message": "GraphQL interface is planned for future implementation",
        "current_implementation": "REST API endpoints available at /api",
        "planned_features": [
            "GraphQL schema for GraphRAG queries",
            "Real-time subscriptions for indexing progress",
            "Nested queries for complex data relationships",
            "GraphQL playground for interactive queries",
        ],
        "rest_api_alternative": "/api",
    }


@graphql_router.post("/", tags=["GraphQL"])
async def graphql_query_placeholder(request: dict) -> dict[str, Any]:
    """GraphQL query placeholder endpoint.

    Args:
        request: GraphQL query request (placeholder)

    Returns:
        Dict containing placeholder response
    """
    logger.info("GraphQL query placeholder accessed")
    return {
        "data": None,
        "errors": [
            {
                "message": "GraphQL interface is not yet implemented. Please use REST API at /api",
                "extensions": {
                    "code": "NOT_IMPLEMENTED",
                    "rest_endpoints": {
                        "query": "/api/query",
                        "index": "/api/index",
                        "status": "/api/status",
                    },
                },
            }
        ],
    }


# Register routers with the main app
app.include_router(api_router)
app.include_router(graphql_router)
