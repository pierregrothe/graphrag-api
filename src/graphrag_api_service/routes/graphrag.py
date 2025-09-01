# src/graphrag_api_service/routes/graphrag.py
# GraphRAG API route handlers
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphRAG API route handlers for query, indexing, and status endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..graphrag_integration import GraphRAGError
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for GraphRAG endpoints
router = APIRouter(prefix="/api", tags=["GraphRAG"])


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


# Dependency injection functions (to be called from main.py)
def setup_graphrag_routes(graphrag_integration, workspace_manager):
    """Setup GraphRAG routes with dependencies."""

    @router.post("/query", response_model=QueryResponse)
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

    @router.post("/index", response_model=IndexResponse)
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
            raise HTTPException(
                status_code=500, detail="Internal server error during indexing"
            ) from e

    @router.get("/status")
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

    return router
