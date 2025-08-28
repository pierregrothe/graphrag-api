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
from .indexing import IndexingManager
from .indexing.models import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobStatus,
    IndexingJobSummary,
    IndexingStats,
)
from .logging_config import get_logger, setup_logging
from .providers import register_providers
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

# Initialize workspace manager and indexing manager
workspace_manager = WorkspaceManager(settings)
indexing_manager = IndexingManager(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Register LLM providers
    register_providers()
    logger.info("LLM providers registered successfully")

    # Start indexing manager
    await indexing_manager.start()
    logger.info("Indexing manager started successfully")

    yield

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


# Register routers with the main app
app.include_router(api_router)
app.include_router(graphql_router)
