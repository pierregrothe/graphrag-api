"""
Graph query service implementation.

This service handles all graph querying operations with proper error handling,
caching, and performance optimization.
"""

import asyncio
from typing import Any

from ..exceptions import ProcessingError, ValidationError
from ..security import get_security_logger
from .interfaces import BaseService, GraphQueryServiceProtocol


class GraphQueryService(BaseService, GraphQueryServiceProtocol):
    """Service for graph query operations."""

    def __init__(self, graph_operations: Any, cache_service: Any = None) -> None:
        super().__init__("graphrag.services.graph_query")
        self.graph_operations = graph_operations
        self.cache_service = cache_service
        self.security_logger = get_security_logger()

    async def get_entities(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get entities from the knowledge graph with caching and validation.

        Parameters
        ----------
        workspace_id : str
            Workspace identifier
        limit : int, default=50
            Maximum number of entities to return
        offset : int, default=0
            Number of entities to skip
        filters : dict, optional
            Entity filters (name, type, etc.)

        Returns
        -------
        dict
            Entities data with metadata

        Raises
        ------
        ValidationError
            If parameters are invalid
        ProcessingError
            If graph operation fails
        """
        try:
            # Validate parameters
            self._validate_pagination(limit, offset)
            self._validate_workspace_id(workspace_id)

            # Check cache first
            cache_key = f"entities:{workspace_id}:{limit}:{offset}:{hash(str(filters))}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    self.logger.debug(f"Cache hit for entities query: {cache_key}")
                    return dict(cached_result)

            # Execute query in thread pool to avoid blocking
            result = await asyncio.to_thread(
                self._execute_entities_query, workspace_id, limit, offset, filters or {}
            )

            # Cache result
            if self.cache_service and result:
                await self.cache_service.set(cache_key, result, ttl=300)  # 5 minutes

            self.logger.info(
                f"Retrieved {len(result.get('entities', []))} entities for workspace {workspace_id}"
            )
            return result

        except Exception as e:
            raise self._handle_service_error(e, "get_entities")

    async def get_relationships(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get relationships from the knowledge graph.

        Parameters
        ----------
        workspace_id : str
            Workspace identifier
        limit : int, default=50
            Maximum number of relationships to return
        offset : int, default=0
            Number of relationships to skip
        filters : dict, optional
            Relationship filters

        Returns
        -------
        dict
            Relationships data with metadata
        """
        try:
            # Validate parameters
            self._validate_pagination(limit, offset)
            self._validate_workspace_id(workspace_id)

            # Check cache
            cache_key = f"relationships:{workspace_id}:{limit}:{offset}:{hash(str(filters))}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return dict(cached_result)

            # Execute query
            result = await asyncio.to_thread(
                self._execute_relationships_query, workspace_id, limit, offset, filters or {}
            )

            # Cache result
            if self.cache_service and result:
                await self.cache_service.set(cache_key, result, ttl=300)

            return result

        except Exception as e:
            raise self._handle_service_error(e, "get_relationships")

    async def search_entities(
        self, workspace_id: str, query: str, limit: int = 50
    ) -> dict[str, Any]:
        """Search entities by text query.

        Parameters
        ----------
        workspace_id : str
            Workspace identifier
        query : str
            Search query text
        limit : int, default=50
            Maximum number of results

        Returns
        -------
        dict
            Search results with relevance scores
        """
        try:
            # Validate parameters
            self._validate_workspace_id(workspace_id)
            if not query or not query.strip():
                raise ValidationError("Search query cannot be empty", field="query")

            if limit > 1000:
                raise ValidationError("Search limit cannot exceed 1000", field="limit")

            # Execute search
            result = await asyncio.to_thread(
                self._execute_entity_search, workspace_id, query.strip(), limit
            )

            return result

        except Exception as e:
            raise self._handle_service_error(e, "search_entities")

    async def health_check(self) -> dict[str, Any]:
        """Perform service health check."""
        try:
            # Test basic graph operations
            test_result = await asyncio.to_thread(self.graph_operations.test_connection)

            return {
                "service": "graph_query",
                "status": "healthy" if test_result else "degraded",
                "cache_available": self.cache_service is not None,
                "timestamp": asyncio.get_event_loop().time(),
            }
        except Exception as e:
            return {
                "service": "graph_query",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            }

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Validate pagination parameters."""
        if limit <= 0 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000", field="limit", value=limit)

        if offset < 0:
            raise ValidationError("Offset must be non-negative", field="offset", value=offset)

    def _validate_workspace_id(self, workspace_id: str) -> None:
        """Validate workspace ID format."""
        if not workspace_id or not workspace_id.strip():
            raise ValidationError("Workspace ID cannot be empty", field="workspace_id")

        # Additional workspace ID validation can be added here
        if len(workspace_id) > 255:
            raise ValidationError(
                "Workspace ID too long (max 255 characters)", field="workspace_id"
            )

    def _execute_entities_query(
        self, workspace_id: str, limit: int, offset: int, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute entities query (CPU-intensive, runs in thread pool)."""
        try:
            # This would call the actual graph operations
            # Implementation depends on the specific graph backend
            entities = self.graph_operations.query_entities(
                workspace_id=workspace_id, limit=limit, offset=offset, filters=filters
            )

            return {
                "entities": entities,
                "total_count": len(entities),
                "limit": limit,
                "offset": offset,
                "workspace_id": workspace_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to execute entities query: {e}")
            raise ProcessingError(
                message="Failed to retrieve entities",
                operation="query_entities",
                details={"workspace_id": workspace_id, "error": str(e)},
            )

    def _execute_relationships_query(
        self, workspace_id: str, limit: int, offset: int, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute relationships query (CPU-intensive, runs in thread pool)."""
        try:
            relationships = self.graph_operations.query_relationships(
                workspace_id=workspace_id, limit=limit, offset=offset, filters=filters
            )

            return {
                "relationships": relationships,
                "total_count": len(relationships),
                "limit": limit,
                "offset": offset,
                "workspace_id": workspace_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to execute relationships query: {e}")
            raise ProcessingError(
                message="Failed to retrieve relationships",
                operation="query_relationships",
                details={"workspace_id": workspace_id, "error": str(e)},
            )

    def _execute_entity_search(self, workspace_id: str, query: str, limit: int) -> dict[str, Any]:
        """Execute entity search (CPU-intensive, runs in thread pool)."""
        try:
            results = self.graph_operations.search_entities(
                workspace_id=workspace_id, query=query, limit=limit
            )

            return {
                "results": results,
                "query": query,
                "total_count": len(results),
                "limit": limit,
                "workspace_id": workspace_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to execute entity search: {e}")
            raise ProcessingError(
                message="Failed to search entities",
                operation="search_entities",
                details={"workspace_id": workspace_id, "query": query, "error": str(e)},
            )
