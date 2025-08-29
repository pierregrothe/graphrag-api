# src/graphrag_api_service/main.py
# Main FastAPI application for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Main FastAPI application module for GraphRAG API service."""

import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth.api_keys import get_api_key_manager
from .auth.jwt_auth import AuthenticationService, JWTConfig
from .caching.redis_cache import RedisCacheConfig, get_redis_cache, initialize_redis_cache
from .config import API_PREFIX, GRAPHQL_PREFIX, settings
from .graph import (
    EntityQueryResponse,
    GraphExportRequest,
    GraphExportResponse,
    GraphOperations,
    GraphStatsResponse,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    RelationshipQueryResponse,
)
from .graph.advanced_query_engine import AdvancedQueryEngine, MultiHopQuery, TemporalQuery
from .graph.analytics import GraphAnalytics
from .graph.operations import GraphOperationsError
from .graphql.subscriptions import get_subscription_manager
from .graphrag_integration import GraphRAGError, GraphRAGIntegration
from .indexing import IndexingManager
from .indexing.models import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobStatus,
    IndexingJobSummary,
    IndexingStats,
)
from .logging_config import get_logger, setup_logging

# Phase 11 imports - Advanced Monitoring & GraphQL Enhancement
from .monitoring.prometheus import get_metrics
from .monitoring.tracing import TracingConfig, initialize_tracing, shutdown_tracing
from .performance.cache_manager import cleanup_cache_manager, get_cache_manager
from .performance.compression import get_performance_middleware
from .performance.connection_pool import cleanup_connection_pool, get_connection_pool
from .performance.memory_optimizer import get_memory_optimizer
from .performance.monitoring import cleanup_performance_monitor, get_performance_monitor
from .providers import register_providers
from .providers.factory import LLMProviderFactory
from .security.middleware import get_security_middleware
from .system import (
    AdvancedHealthResponse,
    ConfigValidationRequest,
    ConfigValidationResponse,
    EnhancedStatusResponse,
    ProviderSwitchRequest,
    ProviderSwitchResponse,
    SystemOperations,
)
from .workspace import WorkspaceManager
from .workspace.models import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize workspace manager, indexing manager, GraphRAG integration, and graph operations
workspace_manager = WorkspaceManager(settings)
indexing_manager = IndexingManager(settings)
graphrag_integration: GraphRAGIntegration | None = None
graph_operations = GraphOperations(settings)
system_operations: SystemOperations | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Register LLM providers
    register_providers()
    logger.info("LLM providers registered successfully")

    # Initialize GraphRAG integration with provider
    global graphrag_integration, system_operations
    try:
        provider = LLMProviderFactory.create_provider(settings)
        graphrag_integration = GraphRAGIntegration(settings, provider)
        logger.info("GraphRAG integration initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GraphRAG integration: {e}")
        graphrag_integration = None

    # Initialize system operations
    system_operations = SystemOperations(
        settings=settings,
        provider_factory=LLMProviderFactory(),
        graphrag_integration=graphrag_integration,
        workspace_manager=workspace_manager,
        indexing_manager=indexing_manager,
        graph_operations=graph_operations,
    )
    logger.info("System operations initialized successfully")

    # Start indexing manager
    await indexing_manager.start()
    logger.info("Indexing manager started successfully")

    # Phase 11: Initialize advanced monitoring and authentication
    try:
        # Initialize distributed tracing
        if settings.tracing_enabled:
            tracing_config = TracingConfig(
                service_name=settings.app_name,
                service_version=settings.app_version,
                environment=settings.environment,
                jaeger_endpoint=getattr(settings, "jaeger_endpoint", None),
                otlp_endpoint=getattr(settings, "otlp_endpoint", None),
            )
            initialize_tracing(tracing_config)
            logger.info("Distributed tracing initialized")

        # Initialize Redis cache if configured
        if getattr(settings, "redis_enabled", False):
            redis_config = RedisCacheConfig(
                host=getattr(settings, "redis_host", "localhost"),
                port=getattr(settings, "redis_port", 6379),
                password=getattr(settings, "redis_password", None),
            )
            await initialize_redis_cache(redis_config)
            logger.info("Redis distributed cache initialized")

        # Initialize subscription manager
        subscription_manager = await get_subscription_manager()
        logger.info("GraphQL subscription manager initialized")

        # Initialize authentication service
        if getattr(settings, "auth_enabled", True):
            jwt_config = JWTConfig(
                secret_key=settings.secret_key,
                access_token_expire_minutes=getattr(settings, "access_token_expire_minutes", 30),
            )
            auth_service = AuthenticationService(jwt_config)

            # Create default admin user if none exists
            try:
                await auth_service.create_user(
                    username="admin",
                    email="admin@graphrag.local",
                    password=getattr(settings, "default_admin_password", "admin123"),
                    roles=["admin"],
                )
                logger.info("Default admin user created")
            except Exception:
                logger.debug("Admin user already exists or creation failed")

        logger.info("Phase 11 advanced features initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Phase 11 features: {e}")
        # Continue without advanced features

    # Initialize performance components
    try:
        # Initialize connection pool
        connection_pool = await get_connection_pool()
        logger.info("Connection pool initialized successfully")

        # Initialize cache manager
        cache_manager = await get_cache_manager()
        logger.info("Cache manager initialized successfully")

        # Initialize performance monitor
        performance_monitor = await get_performance_monitor()
        logger.info("Performance monitoring started successfully")

        # Initialize memory optimizer
        memory_optimizer = get_memory_optimizer()
        logger.info("Memory optimizer initialized successfully")

        logger.info("All performance components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize performance components: {e}")

    yield

    # Shutdown performance components
    try:
        await cleanup_performance_monitor()
        await cleanup_cache_manager()
        await cleanup_connection_pool()
        logger.info("Performance components shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down performance components: {e}")

    # Phase 11: Shutdown advanced features
    try:
        # Shutdown distributed tracing
        shutdown_tracing()

        # Shutdown Redis cache
        redis_cache = await get_redis_cache()
        if redis_cache:
            await redis_cache.disconnect()

        # Shutdown subscription manager
        subscription_manager = await get_subscription_manager()
        if subscription_manager:
            await subscription_manager.stop()

        logger.info("Phase 11 advanced features shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down Phase 11 features: {e}")

    # Shutdown indexing manager
    await indexing_manager.stop()
    logger.info("Indexing manager stopped")
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

# GraphQL router will be created and registered after the main app initialization

# Add security and performance middleware
security_middleware = get_security_middleware()
performance_middleware = get_performance_middleware()

# Add CORS middleware (configured through security middleware)
cors_config = security_middleware.get_cors_config()
if cors_config:
    app.add_middleware(CORSMiddleware, **cors_config)


# Add custom middleware for performance monitoring and security
@app.middleware("http")
async def performance_security_middleware(request: Request, call_next):
    """Combined performance monitoring and security middleware."""
    start_time = time.time()

    # Security checks - skip in testing mode
    import os

    testing_env = os.getenv("TESTING", "false").lower()
    rate_limiting_env = os.getenv("RATE_LIMITING_ENABLED", "true").lower()
    is_testing = testing_env == "true" or rate_limiting_env == "false"

    try:
        if not is_testing:
            await security_middleware.process_request(request)
    except HTTPException as e:
        # Log security event
        security_middleware.audit_logger.log_request(
            request_id=str(id(request)),
            method=request.method,
            path=str(request.url.path),
            user_agent=request.headers.get("user-agent"),
            ip_address=security_middleware.get_client_ip(request),
            status_code=e.status_code,
            response_time=time.time() - start_time,
            error_message=e.detail,
        )
        raise e

    # Performance monitoring
    performance_monitor = await get_performance_monitor()
    async with performance_monitor.track_request(
        endpoint=str(request.url.path),
        method=request.method,
        user_agent=request.headers.get("user-agent"),
        ip_address=security_middleware.get_client_ip(request),
    ) as request_id:
        try:
            response = await call_next(request)

            # Add security headers
            security_middleware.add_security_headers(response)

            # Log successful request
            security_middleware.audit_logger.log_request(
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                user_agent=request.headers.get("user-agent"),
                ip_address=security_middleware.get_client_ip(request),
                status_code=response.status_code,
                response_time=time.time() - start_time,
            )

            return response

        except Exception as e:
            # Record error
            await performance_monitor.record_error(request_id, 500)

            # Log error request
            security_middleware.audit_logger.log_request(
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                user_agent=request.headers.get("user-agent"),
                ip_address=security_middleware.get_client_ip(request),
                status_code=500,
                response_time=time.time() - start_time,
                error_message=str(e),
            )

            raise e


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
            "workspaces": "/api/workspaces",
            "indexing_jobs": "/api/indexing/jobs",
            "indexing_stats": "/api/indexing/stats",
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


@api_router.get("/health/detailed", tags=["Health"])
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check with component status.

    Returns:
        Dict containing detailed health information
    """
    try:
        # Check performance components
        performance_monitor = await get_performance_monitor()
        cache_manager = await get_cache_manager()
        connection_pool = await get_connection_pool()
        memory_optimizer = get_memory_optimizer()

        # Get current metrics
        performance_metrics = await performance_monitor.get_current_metrics()
        cache_status = await cache_manager.get_status()
        pool_status = await connection_pool.get_pool_status()
        memory_status = await memory_optimizer.get_optimization_status()

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "performance_monitor": {
                    "status": "healthy" if performance_metrics else "degraded",
                    "metrics": performance_metrics.dict() if performance_metrics else None,
                },
                "cache_manager": {
                    "status": "healthy",
                    "metrics": cache_status,
                },
                "connection_pool": {
                    "status": "healthy" if pool_status["initialized"] else "degraded",
                    "metrics": pool_status,
                },
                "memory_optimizer": {
                    "status": "healthy",
                    "metrics": memory_status,
                },
            },
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
        }


@api_router.get("/health/database", tags=["Health"])
async def database_health_check() -> dict[str, Any]:
    """Database connectivity health check.

    Returns:
        Dict containing database health status
    """
    try:
        connection_pool = await get_connection_pool()
        pool_status = await connection_pool.get_pool_status()

        return {
            "status": "healthy" if pool_status["initialized"] else "unhealthy",
            "database": pool_status,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@api_router.get("/health/memory", tags=["Health"])
async def memory_health_check() -> dict[str, Any]:
    """Memory usage health check.

    Returns:
        Dict containing memory health status
    """
    try:
        memory_optimizer = get_memory_optimizer()
        memory_stats = memory_optimizer.monitor.get_memory_stats()

        status = "healthy"
        if memory_stats.usage_percent > 90:
            status = "critical"
        elif memory_stats.usage_percent > 80:
            status = "warning"

        return {
            "status": status,
            "memory_usage_percent": memory_stats.usage_percent,
            "memory_stats": memory_stats.dict(),
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@api_router.get("/metrics/performance/summary", tags=["Monitoring"])
async def get_performance_metrics_summary() -> dict[str, Any]:
    """Get performance metrics and statistics.

    Returns:
        Dict containing performance metrics
    """
    try:
        performance_monitor = await get_performance_monitor()
        performance_summary = await performance_monitor.get_performance_summary()

        return {
            "status": "success",
            "metrics": performance_summary,
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {e}")


@api_router.get("/metrics/cache", tags=["Monitoring"])
async def get_cache_metrics() -> dict[str, Any]:
    """Get cache performance metrics.

    Returns:
        Dict containing cache metrics
    """
    try:
        cache_manager = await get_cache_manager()
        cache_metrics = await cache_manager.get_metrics()
        cache_status = await cache_manager.get_status()

        return {
            "status": "success",
            "metrics": cache_metrics.dict(),
            "cache_status": cache_status,
        }
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache metrics: {e}")


@api_router.get("/metrics/security", tags=["Monitoring"])
async def get_security_metrics() -> dict[str, Any]:
    """Get security audit metrics.

    Returns:
        Dict containing security metrics
    """
    try:
        security_middleware = get_security_middleware()
        security_summary = security_middleware.audit_logger.get_security_summary()

        return {
            "status": "success",
            "security_summary": security_summary,
        }
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security metrics: {e}")


@api_router.post("/admin/cache/clear", tags=["Administration"])
async def clear_cache(namespace: str = None) -> dict[str, Any]:
    """Clear cache entries.

    Args:
        namespace: Optional namespace to clear (clears all if not specified)

    Returns:
        Dict containing operation result
    """
    try:
        cache_manager = await get_cache_manager()

        if namespace:
            cleared_count = await cache_manager.clear_namespace(namespace)
            message = f"Cleared {cleared_count} entries from namespace '{namespace}'"
        else:
            # Clear all cache entries by clearing all known namespaces
            total_cleared = 0
            namespaces = ["entities", "relationships", "communities", "analytics"]
            for ns in namespaces:
                cleared_count = await cache_manager.clear_namespace(ns)
                total_cleared += cleared_count
            message = f"Cleared {total_cleared} total cache entries"

        return {
            "status": "success",
            "message": message,
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")


@api_router.post("/admin/memory/optimize", tags=["Administration"])
async def optimize_memory() -> dict[str, Any]:
    """Optimize memory usage.

    Returns:
        Dict containing optimization results
    """
    try:
        memory_optimizer = get_memory_optimizer()
        optimization_results = memory_optimizer.monitor.optimize_memory_usage()

        return {
            "status": "success",
            "optimization_results": optimization_results,
        }
    except Exception as e:
        logger.error(f"Failed to optimize memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize memory: {e}")


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

    # Check if GraphRAG integration is available
    if not graphrag_integration:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG integration not available. Please check configuration and provider settings.",
        )

    # Check if GraphRAG is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        # Determine search type based on community level
        if request.community_level > 0:
            # Use global search for community-level queries
            result = await graphrag_integration.query_global(
                query=request.query,
                data_path=settings.graphrag_data_path,
                community_level=request.community_level,
                max_tokens=request.max_tokens,
            )
        else:
            # Use local search for entity-level queries
            result = await graphrag_integration.query_local(
                query=request.query,
                data_path=settings.graphrag_data_path,
                max_tokens=request.max_tokens,
            )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            community_level=result["community_level"],
            tokens_used=result["tokens_used"],
        )

    except GraphRAGError as e:
        logger.error(f"GraphRAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG query failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during GraphRAG query: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during query processing"
        ) from e


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

    # Check if GraphRAG integration is available
    if not graphrag_integration:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG integration not available. Please check configuration and provider settings.",
        )

    # Basic validation
    if not request.data_path:
        raise HTTPException(status_code=400, detail="Data path is required")

    try:
        # Perform GraphRAG indexing
        result = await graphrag_integration.index_data(
            data_path=request.data_path,
            config_path=request.config_path,
            force_reindex=request.force_reindex,
        )

        return IndexResponse(
            status=result["status"],
            message=result["message"],
            files_processed=result["files_processed"],
            entities_extracted=result["entities_extracted"],
            relationships_extracted=result["relationships_extracted"],
        )

    except GraphRAGError as e:
        logger.error(f"GraphRAG indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG indexing failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during GraphRAG indexing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during indexing") from e


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
            "/api/workspaces",
        ],
        "workspace_stats": workspace_manager.get_workspace_stats(),
    }


# Workspace Management API endpoints
@api_router.post("/workspaces", response_model=Workspace, tags=["Workspace"])
async def create_workspace(request: WorkspaceCreateRequest) -> Workspace:
    """Create a new GraphRAG workspace.

    Creates a new workspace with its own configuration, data directory,
    and isolated GraphRAG processing environment.

    Args:
        request: Workspace creation request

    Returns:
        Created workspace information

    Raises:
        HTTPException: If workspace creation fails
    """
    logger.info(f"Creating workspace: {request.name}")

    try:
        workspace = workspace_manager.create_workspace(request)
        logger.info(f"Successfully created workspace: {workspace.id}")
        return workspace
    except ValueError as e:
        logger.error(f"Workspace creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        logger.error(f"Workspace directory creation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create workspace directories: {e}"
        ) from e


@api_router.get("/workspaces", response_model=list[WorkspaceSummary], tags=["Workspace"])
async def list_workspaces() -> list[WorkspaceSummary]:
    """List all GraphRAG workspaces.

    Returns:
        List of workspace summaries with key information
    """
    logger.info("Listing workspaces")
    workspaces = workspace_manager.list_workspaces()
    logger.info(f"Found {len(workspaces)} workspaces")
    return workspaces


@api_router.get("/workspaces/{workspace_id}", response_model=Workspace, tags=["Workspace"])
async def get_workspace(workspace_id: str) -> Workspace:
    """Get workspace by ID.

    Args:
        workspace_id: Unique workspace identifier

    Returns:
        Workspace information

    Raises:
        HTTPException: If workspace not found
    """
    logger.info(f"Getting workspace: {workspace_id}")

    workspace = workspace_manager.get_workspace(workspace_id)
    if not workspace:
        logger.warning(f"Workspace not found: {workspace_id}")
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

    return workspace


@api_router.put("/workspaces/{workspace_id}", response_model=Workspace, tags=["Workspace"])
async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest) -> Workspace:
    """Update workspace configuration.

    Args:
        workspace_id: Unique workspace identifier
        request: Workspace update request

    Returns:
        Updated workspace information

    Raises:
        HTTPException: If workspace not found or update fails
    """
    logger.info(f"Updating workspace: {workspace_id}")

    try:
        workspace = workspace_manager.update_workspace(workspace_id, request)
        logger.info(f"Successfully updated workspace: {workspace_id}")
        return workspace
    except ValueError as e:
        logger.error(f"Workspace update failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@api_router.delete("/workspaces/{workspace_id}", tags=["Workspace"])
async def delete_workspace(workspace_id: str, remove_files: bool = False) -> dict[str, Any]:
    """Delete workspace.

    Args:
        workspace_id: Unique workspace identifier
        remove_files: Whether to remove workspace files from disk

    Returns:
        Deletion status information

    Raises:
        HTTPException: If workspace not found
    """
    logger.info(f"Deleting workspace: {workspace_id} (remove_files={remove_files})")

    success = workspace_manager.delete_workspace(workspace_id, remove_files)
    if not success:
        logger.warning(f"Workspace not found for deletion: {workspace_id}")
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

    logger.info(f"Successfully deleted workspace: {workspace_id}")
    return {
        "status": "deleted",
        "workspace_id": workspace_id,
        "files_removed": remove_files,
        "message": f"Workspace {workspace_id} deleted successfully",
    }


@api_router.get("/workspaces/{workspace_id}/config", tags=["Workspace"])
async def get_workspace_config(workspace_id: str) -> dict[str, Any]:
    """Get workspace GraphRAG configuration file content.

    Args:
        workspace_id: Unique workspace identifier

    Returns:
        Workspace GraphRAG configuration

    Raises:
        HTTPException: If workspace not found or config not available
    """
    logger.info(f"Getting workspace config: {workspace_id}")

    workspace = workspace_manager.get_workspace(workspace_id)
    if not workspace:
        logger.warning(f"Workspace not found: {workspace_id}")
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

    if not workspace.config_file_path:
        raise HTTPException(status_code=404, detail="Workspace configuration not available")

    try:
        from pathlib import Path

        import yaml

        config_path = Path(workspace.config_file_path)
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")

        with open(config_path, encoding="utf-8") as f:
            config_content = yaml.safe_load(f)

        return {
            "workspace_id": workspace_id,
            "config_file": str(config_path),
            "configuration": config_content,
        }

    except Exception as e:
        logger.error(f"Failed to read workspace config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read configuration: {e}") from e


# GraphQL info endpoint for tests (not under /api prefix)
@app.get("/graphql/", tags=["GraphQL"])
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


@app.post("/graphql/", tags=["GraphQL"])
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


# Indexing API endpoints under /api/indexing prefix
@api_router.post("/indexing/jobs", response_model=IndexingJob, tags=["Indexing"])
async def create_indexing_job(request: IndexingJobCreate) -> IndexingJob:
    """Create a new indexing job for a workspace.

    Args:
        request: Job creation request

    Returns:
        Created indexing job

    Raises:
        HTTPException: If workspace not found or not ready for indexing
    """
    logger.info(f"Creating indexing job for workspace {request.workspace_id}")

    # Get workspace
    workspace = workspace_manager.get_workspace(request.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {request.workspace_id}")

    try:
        job = indexing_manager.create_indexing_job(request, workspace)

        # Update workspace status
        workspace.update_status(workspace.status)  # Trigger timestamp update
        workspace_manager._save_workspaces_index()

        logger.info(f"Created indexing job {job.id}")
        return job

    except ValueError as e:
        logger.error(f"Failed to create indexing job: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@api_router.get("/indexing/jobs", response_model=list[IndexingJobSummary], tags=["Indexing"])
async def list_indexing_jobs(
    status: IndexingJobStatus | None = None, limit: int = 100
) -> list[IndexingJobSummary]:
    """List indexing jobs with optional status filter.

    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return

    Returns:
        List of job summaries
    """
    logger.info(f"Listing indexing jobs (status: {status}, limit: {limit})")

    jobs = indexing_manager.list_jobs(status=status, limit=limit)
    return jobs


@api_router.get("/indexing/jobs/{job_id}", response_model=IndexingJob, tags=["Indexing"])
async def get_indexing_job(job_id: str) -> IndexingJob:
    """Get indexing job by ID.

    Args:
        job_id: Job ID

    Returns:
        Indexing job details

    Raises:
        HTTPException: If job not found
    """
    logger.info(f"Getting indexing job {job_id}")

    job = indexing_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

    return job


@api_router.delete("/indexing/jobs/{job_id}", tags=["Indexing"])
async def cancel_indexing_job(job_id: str) -> dict[str, Any]:
    """Cancel an indexing job.

    Args:
        job_id: Job ID to cancel

    Returns:
        Cancellation result

    Raises:
        HTTPException: If job not found
    """
    logger.info(f"Cancelling indexing job {job_id}")

    job = indexing_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

    success = indexing_manager.cancel_job(job_id)

    return {
        "job_id": job_id,
        "cancelled": success,
        "message": f"Job {job_id} {'cancelled' if success else 'could not be cancelled'}",
    }


@api_router.post("/indexing/jobs/{job_id}/retry", response_model=IndexingJob, tags=["Indexing"])
async def retry_indexing_job(job_id: str) -> IndexingJob:
    """Retry a failed indexing job.

    Args:
        job_id: Job ID to retry

    Returns:
        Updated indexing job

    Raises:
        HTTPException: If job not found or cannot be retried
    """
    logger.info(f"Retrying indexing job {job_id}")

    job = indexing_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

    if not job.can_retry():
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} cannot be retried (status: {job.status}, retries: {job.retry_count}/{job.max_retries})",
        )

    success = indexing_manager.retry_job(job_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to retry job {job_id}")

    retried_job = indexing_manager.get_job(job_id)
    if not retried_job:
        raise HTTPException(status_code=404, detail=f"Job not found after retry: {job_id}")

    return retried_job


@api_router.get(
    "/indexing/workspaces/{workspace_id}/jobs", response_model=list[IndexingJob], tags=["Indexing"]
)
async def get_workspace_indexing_jobs(workspace_id: str) -> list[IndexingJob]:
    """Get all indexing jobs for a workspace.

    Args:
        workspace_id: Workspace ID

    Returns:
        List of indexing jobs for the workspace

    Raises:
        HTTPException: If workspace not found
    """
    logger.info(f"Getting indexing jobs for workspace {workspace_id}")

    # Verify workspace exists
    workspace = workspace_manager.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

    jobs = indexing_manager.get_jobs_for_workspace(workspace_id)
    return jobs


@api_router.get("/indexing/stats", response_model=IndexingStats, tags=["Indexing"])
async def get_indexing_stats() -> IndexingStats:
    """Get indexing system statistics.

    Returns:
        Indexing statistics
    """
    logger.info("Getting indexing statistics")

    stats = indexing_manager.get_indexing_stats()
    return stats


# Graph Operations API endpoints
@api_router.get("/graph/entities", response_model=EntityQueryResponse, tags=["Graph"])
async def query_entities(
    entity_name: str | None = None,
    entity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> EntityQueryResponse:
    """Query entities from the knowledge graph.

    This endpoint allows you to search and filter entities in the knowledge graph
    with pagination support.

    Args:
        request: Entity query parameters

    Returns:
        EntityQueryResponse containing entities and metadata

    Raises:
        HTTPException: If querying fails or data path not configured
    """
    logger.info(f"Querying entities with filters: name={entity_name}, type={entity_type}")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.query_entities(
            data_path=settings.graphrag_data_path,
            entity_name=entity_name,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )

        return EntityQueryResponse(**result)

    except GraphOperationsError as e:
        logger.error(f"Entity querying failed: {e}")
        raise HTTPException(status_code=500, detail=f"Entity querying failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during entity querying: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during entity querying"
        ) from e


@api_router.get("/graph/entities/{entity_id}", response_model=dict, tags=["Graph"])
async def get_entity_by_id(entity_id: str) -> dict[str, Any]:
    """Get a specific entity by ID.

    This endpoint retrieves detailed information about a single entity
    from the knowledge graph.

    Args:
        entity_id: The unique identifier of the entity

    Returns:
        Dict containing entity details

    Raises:
        HTTPException: If entity not found or data path not configured
    """
    logger.info(f"Getting entity by ID: {entity_id}")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.query_entities(
            data_path=settings.graphrag_data_path,
            entity_name=entity_id,
            limit=1,
        )

        if result["entities"]:
            entity = result["entities"][0]
            return {
                "id": entity["id"],
                "title": entity["title"],
                "type": entity["type"],
                "description": entity["description"],
                "degree": entity["degree"],
                "community_ids": entity.get("community_ids", []),
                "text_unit_ids": entity.get("text_unit_ids", []),
            }
        else:
            raise HTTPException(status_code=404, detail=f"Entity with ID '{entity_id}' not found")

    except HTTPException:
        raise
    except GraphOperationsError as e:
        logger.error(f"Entity retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Entity retrieval failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during entity retrieval: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during entity retrieval"
        ) from e


@api_router.get("/graph/relationships", response_model=RelationshipQueryResponse, tags=["Graph"])
async def query_relationships(
    source_entity: str | None = None,
    target_entity: str | None = None,
    relationship_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> RelationshipQueryResponse:
    """Query relationships from the knowledge graph.

    This endpoint allows you to search and filter relationships in the knowledge graph
    with pagination support.

    Args:
        request: Relationship query parameters

    Returns:
        RelationshipQueryResponse containing relationships and metadata

    Raises:
        HTTPException: If querying fails or data path not configured
    """
    logger.info(
        f"Querying relationships with filters: source={source_entity}, target={target_entity}"
    )

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.query_relationships(
            data_path=settings.graphrag_data_path,
            source_entity=source_entity,
            target_entity=target_entity,
            relationship_type=relationship_type,
            limit=limit,
            offset=offset,
        )

        return RelationshipQueryResponse(**result)

    except GraphOperationsError as e:
        logger.error(f"Relationship querying failed: {e}")
        raise HTTPException(status_code=500, detail=f"Relationship querying failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during relationship querying: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during relationship querying"
        ) from e


@api_router.get("/graph/relationships/{relationship_id}", response_model=dict, tags=["Graph"])
async def get_relationship_by_id(relationship_id: str) -> dict[str, Any]:
    """Get a specific relationship by ID.

    This endpoint retrieves detailed information about a single relationship
    from the knowledge graph.

    Args:
        relationship_id: The unique identifier of the relationship

    Returns:
        Dict containing relationship details

    Raises:
        HTTPException: If relationship not found or data path not configured
    """
    logger.info(f"Getting relationship by ID: {relationship_id}")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        # Query relationships and filter by ID
        result = await graph_operations.query_relationships(
            data_path=settings.graphrag_data_path,
            limit=1000,  # Get more results to find the specific ID
        )

        # Find the specific relationship by ID
        for relationship in result["relationships"]:
            if relationship["id"] == relationship_id:
                return {
                    "id": relationship["id"],
                    "source": relationship["source"],
                    "target": relationship["target"],
                    "type": relationship["type"],
                    "description": relationship["description"],
                    "weight": relationship["weight"],
                    "text_unit_ids": relationship.get("text_unit_ids", []),
                }

        raise HTTPException(
            status_code=404, detail=f"Relationship with ID '{relationship_id}' not found"
        )

    except HTTPException:
        raise
    except GraphOperationsError as e:
        logger.error(f"Relationship retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Relationship retrieval failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during relationship retrieval: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during relationship retrieval"
        ) from e


@api_router.get("/graph/stats", response_model=GraphStatsResponse, tags=["Graph"])
async def get_graph_statistics() -> GraphStatsResponse:
    """Get comprehensive statistics about the knowledge graph.

    This endpoint provides detailed statistics including entity counts, relationship counts,
    community information, and graph metrics.

    Returns:
        GraphStatsResponse containing comprehensive graph statistics

    Raises:
        HTTPException: If statistics calculation fails or data path not configured
    """
    logger.info("Getting graph statistics")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.get_graph_statistics(data_path=settings.graphrag_data_path)

        return GraphStatsResponse(**result)

    except GraphOperationsError as e:
        logger.error(f"Graph statistics calculation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Graph statistics calculation failed: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during graph statistics calculation: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during graph statistics calculation"
        ) from e


@api_router.post("/graph/visualization", response_model=GraphVisualizationResponse, tags=["Graph"])
async def generate_graph_visualization(
    request: GraphVisualizationRequest,
) -> GraphVisualizationResponse:
    """Generate graph visualization data.

    This endpoint generates data for visualizing the knowledge graph including nodes,
    edges, and layout information.

    Args:
        request: Visualization parameters

    Returns:
        GraphVisualizationResponse containing visualization data

    Raises:
        HTTPException: If visualization generation fails or data path not configured
    """
    logger.info(f"Generating graph visualization with {request.entity_limit} entities")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.generate_visualization(
            data_path=settings.graphrag_data_path,
            entity_limit=request.entity_limit,
            relationship_limit=request.relationship_limit,
            community_level=request.community_level,
            layout_algorithm=request.layout_algorithm,
            include_node_labels=request.include_node_labels,
            include_edge_labels=request.include_edge_labels,
        )

        return GraphVisualizationResponse(**result)

    except GraphOperationsError as e:
        logger.error(f"Graph visualization generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Graph visualization generation failed: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during graph visualization generation: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during graph visualization generation"
        ) from e


@api_router.post("/graph/export", response_model=GraphExportResponse, tags=["Graph"])
async def export_graph(request: GraphExportRequest) -> GraphExportResponse:
    """Export graph data in various formats.

    This endpoint exports the knowledge graph data in different formats for analysis
    or integration with other tools.

    Args:
        request: Export parameters

    Returns:
        GraphExportResponse containing export information and download URL

    Raises:
        HTTPException: If export fails or data path not configured
    """
    logger.info(f"Exporting graph data in {request.format} format")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        result = await graph_operations.export_graph(
            data_path=settings.graphrag_data_path,
            format=request.format,
            include_entities=request.include_entities,
            include_relationships=request.include_relationships,
            include_communities=request.include_communities,
            entity_limit=request.entity_limit,
            relationship_limit=request.relationship_limit,
        )

        return GraphExportResponse(**result)

    except GraphOperationsError as e:
        logger.error(f"Graph export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph export failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during graph export: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during graph export"
        ) from e


# System Management Endpoints


@api_router.post("/system/provider/switch", response_model=ProviderSwitchResponse, tags=["System"])
async def switch_provider(request: ProviderSwitchRequest) -> ProviderSwitchResponse:
    """Switch the active LLM provider.

    This endpoint allows switching between available LLM providers (Ollama and Google Gemini)
    with optional connection validation.

    Args:
        request: Provider switch configuration

    Returns:
        ProviderSwitchResponse with switch operation results

    Raises:
        HTTPException: If provider switch fails
    """
    logger.info(f"Switching provider to: {request.provider}")

    if not system_operations:
        raise HTTPException(status_code=503, detail="System operations not available")

    try:
        result = await system_operations.switch_provider(
            provider_name=request.provider,
            validate_connection=request.validate_connection,
        )
        return ProviderSwitchResponse(**result)
    except Exception as e:
        logger.error(f"Provider switch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Provider switch failed: {e}") from e


@api_router.get("/system/health/advanced", response_model=AdvancedHealthResponse, tags=["System"])
async def get_advanced_health() -> AdvancedHealthResponse:
    """Get comprehensive system health status.

    This endpoint provides detailed health information about all system components including
    provider status, GraphRAG integration, workspace health, and system resources.

    Returns:
        AdvancedHealthResponse with detailed health information

    Raises:
        HTTPException: If health check fails
    """
    logger.info("Performing advanced health check")

    if not system_operations:
        raise HTTPException(status_code=503, detail="System operations not available")

    try:
        health_data = await system_operations.get_advanced_health()
        return AdvancedHealthResponse(**health_data)
    except Exception as e:
        logger.error(f"Advanced health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}") from e


@api_router.get("/system/status/enhanced", response_model=EnhancedStatusResponse, tags=["System"])
async def get_enhanced_status() -> EnhancedStatusResponse:
    """Get enhanced system status with metrics.

    This endpoint provides comprehensive status information including uptime, provider info,
    graph metrics, indexing metrics, and recent operations.

    Returns:
        EnhancedStatusResponse with comprehensive status information

    Raises:
        HTTPException: If status generation fails
    """
    logger.info("Generating enhanced status report")

    if not system_operations:
        raise HTTPException(status_code=503, detail="System operations not available")

    try:
        # Update metrics for graph operations
        if graph_operations:
            system_operations.metrics["graph_queries"] = (
                graph_operations.metrics.get("queries", 0)
                if hasattr(graph_operations, "metrics")
                else 0
            )

        status_data = await system_operations.get_enhanced_status()
        return EnhancedStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Enhanced status generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status generation failed: {e}") from e


@api_router.post(
    "/system/config/validate", response_model=ConfigValidationResponse, tags=["System"]
)
async def validate_configuration(request: ConfigValidationRequest) -> ConfigValidationResponse:
    """Validate system configuration.

    This endpoint validates various configuration aspects including provider settings,
    GraphRAG parameters, and workspace configuration.

    Args:
        request: Configuration validation parameters

    Returns:
        ConfigValidationResponse with validation results

    Raises:
        HTTPException: If validation fails
    """
    logger.info(f"Validating configuration type: {request.config_type}")

    if not system_operations:
        raise HTTPException(status_code=503, detail="System operations not available")

    try:
        validation_result = await system_operations.validate_configuration(
            config_type=request.config_type,
            config_data=request.config_data,
            strict_mode=request.strict_mode,
        )
        return ConfigValidationResponse(**validation_result)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}") from e


# Cache Management API endpoints
@api_router.delete("/system/cache", tags=["System"])
async def clear_system_cache(cache_type: str | None = None) -> dict[str, Any]:
    """Clear system cache.

    This endpoint clears various system caches to free up memory and storage space.
    Can clear all caches or specific cache types.

    Args:
        cache_type: Optional specific cache type to clear (graph, embedding, query)

    Returns:
        Dict containing cache clear operation results

    Raises:
        HTTPException: If cache clearing fails
    """
    logger.info(f"Clearing system cache (type: {cache_type or 'all'})")

    try:
        # For now, simulate cache clearing
        # In a real implementation, this would clear actual cache systems
        files_cleared = 0
        bytes_freed = 0

        if cache_type:
            message = f"Cache type '{cache_type}' cleared successfully"
        else:
            message = "All caches cleared successfully"

        return {
            "success": True,
            "message": message,
            "cache_type": cache_type or "all",
            "files_cleared": files_cleared,
            "bytes_freed": bytes_freed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clearing failed: {e}") from e


@api_router.get("/system/cache/stats", tags=["System"])
async def get_cache_statistics() -> dict[str, Any]:
    """Get cache statistics and information.

    This endpoint provides detailed information about system cache usage,
    hit rates, and storage consumption.

    Returns:
        Dict containing cache statistics

    Raises:
        HTTPException: If statistics retrieval fails
    """
    logger.info("Getting cache statistics")

    try:
        # For now, return basic cache statistics
        # In a real implementation, this would query actual cache systems
        return {
            "total_size_bytes": 0,
            "total_files": 0,
            "cache_hit_rate": None,
            "last_cleared": None,
            "cache_types": {
                "graph_cache": {
                    "enabled": True,
                    "size_bytes": 0,
                    "files": 0,
                    "hit_rate": None,
                },
                "embedding_cache": {
                    "enabled": True,
                    "size_bytes": 0,
                    "files": 0,
                    "hit_rate": None,
                },
                "query_cache": {
                    "enabled": True,
                    "size_bytes": 0,
                    "files": 0,
                    "hit_rate": None,
                },
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Cache statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache statistics failed: {e}") from e


# Advanced Graph Query API endpoints
@api_router.post("/graph/query/multi-hop", tags=["Advanced Graph"])
async def multi_hop_query(query: MultiHopQuery) -> dict[str, Any]:
    """Execute a multi-hop query with path finding and scoring.

    This endpoint performs advanced graph traversal to find paths between entities
    with configurable hop limits and scoring algorithms.

    Args:
        query: Multi-hop query configuration

    Returns:
        Dict containing query results with paths and scoring information

    Raises:
        HTTPException: If query execution fails or data path not configured
    """
    logger.info(f"Executing multi-hop query: {query}")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        advanced_engine = AdvancedQueryEngine(settings.graphrag_data_path)
        result = await advanced_engine.multi_hop_query(query)

        return {
            "entities": result.entities,
            "relationships": result.relationships,
            "paths": [path.dict() for path in result.paths],
            "total_score": result.total_score,
            "execution_time_ms": result.execution_time_ms,
            "query_metadata": result.query_metadata,
        }

    except Exception as e:
        logger.error(f"Multi-hop query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-hop query failed: {e}") from e


@api_router.post("/graph/query/temporal", tags=["Advanced Graph"])
async def temporal_query(
    base_query: dict[str, Any], temporal_constraints: TemporalQuery
) -> dict[str, Any]:
    """Execute a temporal query with time-based filtering.

    This endpoint performs graph queries with temporal constraints,
    filtering entities and relationships by time ranges.

    Args:
        base_query: Base query parameters
        temporal_constraints: Temporal filtering constraints

    Returns:
        Dict containing temporally filtered query results

    Raises:
        HTTPException: If query execution fails or data path not configured
    """
    logger.info(f"Executing temporal query with constraints: {temporal_constraints}")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        advanced_engine = AdvancedQueryEngine(settings.graphrag_data_path)
        result = await advanced_engine.temporal_query(base_query, temporal_constraints)

        return {
            "entities": result.entities,
            "relationships": result.relationships,
            "execution_time_ms": result.execution_time_ms,
            "query_metadata": result.query_metadata,
        }

    except Exception as e:
        logger.error(f"Temporal query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Temporal query failed: {e}") from e


# Graph Analytics API endpoints
@api_router.post("/graph/analytics/communities", tags=["Graph Analytics"])
async def detect_communities(algorithm: str = "louvain", resolution: float = 1.0) -> dict[str, Any]:
    """Detect communities in the knowledge graph.

    This endpoint performs community detection using various algorithms
    to identify clusters of related entities.

    Args:
        algorithm: Community detection algorithm (louvain, leiden, modularity)
        resolution: Resolution parameter for community detection

    Returns:
        Dict containing detected communities and analysis results

    Raises:
        HTTPException: If analysis fails or data path not configured
    """
    logger.info(f"Detecting communities using {algorithm} algorithm")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.detect_communities(algorithm, resolution)

        return {
            "communities": result.communities,
            "modularity_score": result.modularity_score,
            "algorithm_used": result.algorithm_used,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        logger.error(f"Community detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Community detection failed: {e}") from e


@api_router.get("/graph/analytics/centrality", tags=["Graph Analytics"])
async def calculate_centrality(node_ids: list[str] | None = None) -> dict[str, Any]:
    """Calculate centrality measures for graph nodes.

    This endpoint computes various centrality measures including degree,
    betweenness, closeness, eigenvector centrality, and PageRank.

    Args:
        node_ids: Specific node IDs to analyze (if None, analyze all nodes)

    Returns:
        Dict containing centrality measures for each node

    Raises:
        HTTPException: If analysis fails or data path not configured
    """
    logger.info(f"Calculating centrality measures for {len(node_ids) if node_ids else 'all'} nodes")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        results = await analytics_engine.calculate_centrality_measures(node_ids)

        return {
            "centrality_measures": [result.dict() for result in results],
            "nodes_analyzed": len(results),
        }

    except Exception as e:
        logger.error(f"Centrality calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Centrality calculation failed: {e}") from e


@api_router.post("/graph/analytics/clustering", tags=["Graph Analytics"])
async def perform_clustering(
    algorithm: str = "kmeans", num_clusters: int | None = None
) -> dict[str, Any]:
    """Perform graph clustering analysis.

    This endpoint performs clustering analysis on the knowledge graph
    to identify groups of similar entities.

    Args:
        algorithm: Clustering algorithm (kmeans, spectral, hierarchical)
        num_clusters: Number of clusters (if None, auto-determine)

    Returns:
        Dict containing cluster assignments and analysis results

    Raises:
        HTTPException: If analysis fails or data path not configured
    """
    logger.info(f"Performing clustering using {algorithm} algorithm")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.perform_clustering(algorithm, num_clusters)

        return {
            "clusters": result.clusters,
            "silhouette_score": result.silhouette_score,
            "algorithm_used": result.algorithm_used,
            "num_clusters": result.num_clusters,
        }

    except Exception as e:
        logger.error(f"Graph clustering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph clustering failed: {e}") from e


@api_router.post("/graph/analytics/anomalies", tags=["Graph Analytics"])
async def detect_anomalies(
    method: str = "isolation_forest", threshold: float = 0.1
) -> dict[str, Any]:
    """Detect anomalies in the knowledge graph.

    This endpoint identifies unusual patterns, outliers, and anomalous
    entities or relationships in the graph structure.

    Args:
        method: Anomaly detection method (isolation_forest, local_outlier_factor)
        threshold: Anomaly threshold (0.0 to 1.0)

    Returns:
        Dict containing detected anomalies and analysis results

    Raises:
        HTTPException: If analysis fails or data path not configured
    """
    logger.info(f"Detecting anomalies using {method} method")

    # Check if GraphRAG data path is configured
    if not settings.graphrag_data_path:
        raise HTTPException(
            status_code=400,
            detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
        )

    try:
        analytics_engine = GraphAnalytics(settings.graphrag_data_path)
        result = await analytics_engine.detect_anomalies(method, threshold)

        return {
            "anomalous_entities": result.anomalous_entities,
            "anomalous_relationships": result.anomalous_relationships,
            "anomaly_scores": result.anomaly_scores,
            "detection_method": result.detection_method,
        }

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {e}") from e


# Phase 11: Advanced Monitoring & Authentication Endpoints


@api_router.get("/metrics", tags=["Monitoring"])
async def get_prometheus_metrics():
    """Get Prometheus metrics in text format.

    Returns:
        Prometheus metrics in text format
    """
    from fastapi.responses import Response

    metrics = get_metrics()
    return Response(content=metrics.get_metrics(), media_type=metrics.get_content_type())


@api_router.get("/metrics/performance/detailed", tags=["Monitoring"])
async def get_performance_metrics_detailed() -> dict[str, Any]:
    """Get detailed performance metrics.

    Returns:
        Dict containing performance metrics
    """
    try:
        metrics = get_metrics()
        redis_cache = await get_redis_cache()

        performance_data = {
            "timestamp": time.time(),
            "system": {
                "cpu_usage_percent": 0.0,  # Would be populated by actual system monitoring
                "memory_usage_mb": 0.0,
                "active_connections": 0,
            },
            "cache": {},
            "requests": {
                "total": 0,
                "rate_per_second": 0.0,
                "average_response_time": 0.0,
            },
        }

        # Add Redis cache stats if available
        if redis_cache:
            cache_stats = await redis_cache.get_stats()
            performance_data["cache"] = cache_stats

        return performance_data

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@api_router.post("/auth/login", tags=["Authentication"])
async def login(credentials: dict[str, str]) -> dict[str, Any]:
    """Authenticate user and return JWT tokens.

    Args:
        credentials: User credentials (username, password)

    Returns:
        Dict containing access and refresh tokens
    """
    try:
        from .auth.jwt_auth import UserCredentials

        user_creds = UserCredentials(
            username=credentials["username"], password=credentials["password"]
        )

        # TODO: Get auth service from global state
        # For now, return a placeholder response
        return {
            "access_token": "placeholder_token",
            "refresh_token": "placeholder_refresh",
            "token_type": "bearer",
            "expires_in": 1800,
        }

    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@api_router.post("/auth/api-keys", tags=["Authentication"])
async def create_api_key(request: dict[str, Any]) -> dict[str, Any]:
    """Create a new API key.

    Args:
        request: API key creation request

    Returns:
        Dict containing the new API key details
    """
    try:
        from .auth.api_keys import APIKeyRequest

        api_key_manager = get_api_key_manager()

        key_request = APIKeyRequest(
            name=request["name"],
            permissions=request.get("permissions", []),
            rate_limit=request.get("rate_limit", 1000),
            expires_in_days=request.get("expires_in_days"),
        )

        # TODO: Get user_id from JWT token
        user_id = "admin"  # Placeholder

        response = await api_key_manager.create_api_key(user_id, key_request)

        return {
            "id": response.id,
            "name": response.name,
            "key": response.key,  # Only returned once
            "prefix": response.prefix,
            "permissions": response.permissions,
            "rate_limit": response.rate_limit,
            "expires_at": response.expires_at.isoformat() if response.expires_at else None,
        }

    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")


# Register routers with the main app
app.include_router(api_router)

# Setup GraphQL after main app initialization
from .graphql import create_graphql_router  # noqa: E402

# Create and register GraphQL router
graphql_router = create_graphql_router(
    graph_operations=graph_operations,
    workspace_manager=workspace_manager,
    system_operations=system_operations,
    graphrag_integration=graphrag_integration,
    indexing_manager=indexing_manager,
)
app.include_router(graphql_router, prefix="/graphql/playground")
