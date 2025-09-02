# src/graphrag_api_service/routes/graph.py
# Graph operations API route handlers
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Graph operations API route handlers for entities, relationships, and analytics."""

from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..graph import (
    EntityQueryResponse,
    GraphExportRequest,
    GraphExportResponse,
    GraphStatsResponse,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    RelationshipQueryResponse,
)
from ..graph.operations import GraphOperationsError
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for graph endpoints
router = APIRouter(prefix="/api", tags=["Graph"])


# Dependency injection function (to be called from main.py)
def setup_graph_routes(graph_operations):
    """Setup graph routes with dependencies."""

    @router.get("/graph/entities", response_model=EntityQueryResponse)
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
            entity_name: Optional entity name filter
            entity_type: Optional entity type filter
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            EntityQueryResponse containing entities and metadata

        Raises:
            HTTPException: If GraphRAG is not configured or query fails
        """
        logger.info(f"Querying entities (name: {entity_name}, type: {entity_type}, limit: {limit})")

        # Check if GraphRAG is configured
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

            return result

        except GraphOperationsError as e:
            logger.error(f"Entity query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Entity query failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during entity querying: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error during entity querying"
            ) from e

    @router.get("/graph/entities/{entity_id}", response_model=dict)
    async def get_entity_by_id(entity_id: str) -> dict[str, Any]:
        """Get a specific entity by ID.

        This endpoint retrieves detailed information about a single entity
        from the knowledge graph.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity details including properties and relationships

        Raises:
            HTTPException: If entity not found or GraphRAG not configured
        """
        logger.info(f"Getting entity by ID: {entity_id}")

        # Check if GraphRAG is configured
        if not settings.graphrag_data_path:
            raise HTTPException(
                status_code=400,
                detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
            )

        try:
            result = await graph_operations.get_entity_by_id(
                data_path=settings.graphrag_data_path,
                entity_id=entity_id,
            )

            if not result:
                raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

            return result

        except GraphOperationsError as e:
            logger.error(f"Entity retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=f"Entity retrieval failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during entity retrieval: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error during entity retrieval"
            ) from e

    @router.get("/graph/relationships", response_model=RelationshipQueryResponse)
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
            source_entity: Optional source entity filter
            target_entity: Optional target entity filter
            relationship_type: Optional relationship type filter
            limit: Maximum number of relationships to return
            offset: Number of relationships to skip

        Returns:
            RelationshipQueryResponse containing relationships and metadata

        Raises:
            HTTPException: If GraphRAG is not configured or query fails
        """
        logger.info(
            f"Querying relationships (source: {source_entity}, target: {target_entity}, type: {relationship_type})"
        )

        # Check if GraphRAG is configured
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

            return result

        except GraphOperationsError as e:
            logger.error(f"Relationship query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Relationship query failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during relationship querying: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error during relationship querying"
            ) from e

    @router.get("/graph/relationships/{relationship_id}", response_model=dict)
    async def get_relationship_by_id(relationship_id: str) -> dict[str, Any]:
        """Get a specific relationship by ID.

        This endpoint retrieves detailed information about a single relationship
        from the knowledge graph.

        Args:
            relationship_id: Unique relationship identifier

        Returns:
            Relationship details including properties and connected entities

        Raises:
            HTTPException: If relationship not found or GraphRAG not configured
        """
        logger.info(f"Getting relationship by ID: {relationship_id}")

        # Check if GraphRAG is configured
        if not settings.graphrag_data_path:
            raise HTTPException(
                status_code=400,
                detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
            )

        try:
            result = await graph_operations.get_relationship_by_id(
                data_path=settings.graphrag_data_path,
                relationship_id=relationship_id,
            )

            if not result:
                raise HTTPException(
                    status_code=404, detail=f"Relationship not found: {relationship_id}"
                )

            return result

        except GraphOperationsError as e:
            logger.error(f"Relationship retrieval failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Relationship retrieval failed: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during relationship retrieval: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error during relationship retrieval"
            ) from e

    @router.get("/graph/stats", response_model=GraphStatsResponse)
    async def get_graph_statistics() -> GraphStatsResponse:
        """Get comprehensive statistics about the knowledge graph.

        This endpoint provides detailed statistics including entity counts, relationship counts,
        community information, and graph metrics.

        Returns:
            GraphStatsResponse containing comprehensive graph statistics

        Raises:
            HTTPException: If GraphRAG is not configured or statistics calculation fails
        """
        logger.info("Getting graph statistics")

        # Check if GraphRAG is configured
        if not settings.graphrag_data_path:
            raise HTTPException(
                status_code=400,
                detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
            )

        try:
            result = await graph_operations.get_graph_statistics(
                data_path=settings.graphrag_data_path,
            )

            return result

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

    @router.post("/graph/visualization", response_model=GraphVisualizationResponse)
    async def generate_graph_visualization(
        request: GraphVisualizationRequest,
    ) -> GraphVisualizationResponse:
        """Generate graph visualization data.

        This endpoint creates visualization data for the knowledge graph that can be
        used with graph visualization libraries.

        Args:
            request: Visualization request parameters

        Returns:
            GraphVisualizationResponse containing visualization data

        Raises:
            HTTPException: If GraphRAG is not configured or visualization fails
        """
        logger.info(f"Generating graph visualization (type: {request.visualization_type})")

        # Check if GraphRAG is configured
        if not settings.graphrag_data_path:
            raise HTTPException(
                status_code=400,
                detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
            )

        try:
            result = await graph_operations.generate_visualization(
                data_path=settings.graphrag_data_path,
                request=request,
            )

            return result

        except GraphOperationsError as e:
            logger.error(f"Graph visualization generation failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Graph visualization generation failed: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during graph visualization generation: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during graph visualization generation",
            ) from e

    @router.post("/graph/export", response_model=GraphExportResponse)
    async def export_graph(request: GraphExportRequest) -> GraphExportResponse:
        """Export graph data in various formats.

        This endpoint exports the knowledge graph data in different formats for analysis
        or integration with other tools.

        Args:
            request: Export request parameters

        Returns:
            GraphExportResponse containing export information

        Raises:
            HTTPException: If GraphRAG is not configured or export fails
        """
        logger.info(f"Exporting graph data (format: {request.format})")

        # Check if GraphRAG is configured
        if not settings.graphrag_data_path:
            raise HTTPException(
                status_code=400,
                detail="GraphRAG data path not configured. Please set GRAPHRAG_DATA_PATH environment variable.",
            )

        try:
            result = await graph_operations.export_graph(
                data_path=settings.graphrag_data_path,
                request=request,
            )

            return result

        except GraphOperationsError as e:
            logger.error(f"Graph export failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph export failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during graph export: {e}")
            raise HTTPException(
                status_code=500, detail="Internal server error during graph export"
            ) from e

    # Store graph_operations for testing access
    router.graph_operations = graph_operations

    return router
