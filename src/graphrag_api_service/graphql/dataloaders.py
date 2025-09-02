# src/graphrag_api_service/graphql/dataloaders.py
# DataLoader implementations for GraphQL N+1 query prevention
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""DataLoader implementations to prevent N+1 query problems in GraphQL resolvers."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from ..config import settings
from ..graph.operations import GraphOperations

logger = logging.getLogger(__name__)


class DataLoader:
    """Base DataLoader implementation for batching and caching."""

    def __init__(self, batch_load_fn: Callable, max_batch_size: int = 100):
        """Initialize DataLoader.

        Args:
            batch_load_fn: Function to batch load data
            max_batch_size: Maximum batch size for loading
        """
        self.batch_load_fn = batch_load_fn
        self.max_batch_size = max_batch_size
        self._cache: dict[str, Any] = {}
        self._batch: list[str] = []
        self._batch_promises: dict[str, asyncio.Future] = {}
        self._batch_scheduled = False

    async def load(self, key: str) -> Any:
        """Load a single item by key.

        Args:
            key: Key to load

        Returns:
            Loaded item
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Check if already in current batch
        if key in self._batch_promises:
            return await self._batch_promises[key]

        # Add to batch
        future = asyncio.Future()
        self._batch_promises[key] = future
        self._batch.append(key)

        # Schedule batch execution if not already scheduled
        if not self._batch_scheduled:
            self._batch_scheduled = True
            asyncio.create_task(self._dispatch_batch())

        return await future

    async def load_many(self, keys: list[str]) -> list[Any]:
        """Load multiple items by keys.

        Args:
            keys: Keys to load

        Returns:
            List of loaded items
        """
        return await asyncio.gather(*[self.load(key) for key in keys])

    async def _dispatch_batch(self):
        """Dispatch the current batch for loading."""
        # Wait a tick to allow more items to be added to the batch
        await asyncio.sleep(0)

        if not self._batch:
            self._batch_scheduled = False
            return

        # Get current batch and reset
        current_batch = self._batch[:]
        current_promises = self._batch_promises.copy()
        self._batch.clear()
        self._batch_promises.clear()
        self._batch_scheduled = False

        try:
            # Execute batch load
            results = await self.batch_load_fn(current_batch)

            # Cache and resolve promises
            for i, key in enumerate(current_batch):
                result = results[i] if i < len(results) else None
                self._cache[key] = result

                if key in current_promises:
                    current_promises[key].set_result(result)

        except Exception as e:
            logger.error(f"Batch load failed: {e}")
            # Reject all promises
            for key in current_batch:
                if key in current_promises:
                    current_promises[key].set_exception(e)

    def clear(self, key: str | None = None):
        """Clear cache.

        Args:
            key: Optional specific key to clear, or None to clear all
        """
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


class EntityDataLoader(DataLoader):
    """DataLoader for entities."""

    def __init__(self, graph_operations: GraphOperations):
        """Initialize entity DataLoader.

        Args:
            graph_operations: Graph operations instance
        """
        self.graph_operations = graph_operations
        super().__init__(self._batch_load_entities)

    async def _batch_load_entities(self, entity_ids: list[str]) -> list[dict[str, Any] | None]:
        """Batch load entities by IDs.

        Args:
            entity_ids: List of entity IDs to load

        Returns:
            List of entity data or None for not found
        """
        if not settings.graphrag_data_path:
            return [None] * len(entity_ids)

        try:
            # Query entities in batch
            result = await self.graph_operations.query_entities(
                data_path=settings.graphrag_data_path, entity_ids=entity_ids, limit=len(entity_ids)
            )

            # Create lookup map
            entity_map = {e["id"]: e for e in result.get("entities", [])}

            # Return results in the same order as requested
            return [entity_map.get(entity_id) for entity_id in entity_ids]

        except Exception as e:
            logger.error(f"Failed to batch load entities: {e}")
            return [None] * len(entity_ids)


class RelationshipDataLoader(DataLoader):
    """DataLoader for relationships."""

    def __init__(self, graph_operations: GraphOperations):
        """Initialize relationship DataLoader.

        Args:
            graph_operations: Graph operations instance
        """
        self.graph_operations = graph_operations
        super().__init__(self._batch_load_relationships)

    async def _batch_load_relationships(
        self, relationship_ids: list[str]
    ) -> list[dict[str, Any] | None]:
        """Batch load relationships by IDs.

        Args:
            relationship_ids: List of relationship IDs to load

        Returns:
            List of relationship data or None for not found
        """
        if not settings.graphrag_data_path:
            return [None] * len(relationship_ids)

        try:
            # Query relationships in batch
            result = await self.graph_operations.query_relationships(
                data_path=settings.graphrag_data_path,
                relationship_ids=relationship_ids,
                limit=len(relationship_ids),
            )

            # Create lookup map
            relationship_map = {r["id"]: r for r in result.get("relationships", [])}

            # Return results in the same order as requested
            return [relationship_map.get(rel_id) for rel_id in relationship_ids]

        except Exception as e:
            logger.error(f"Failed to batch load relationships: {e}")
            return [None] * len(relationship_ids)


class EntityRelationshipsDataLoader(DataLoader):
    """DataLoader for entity relationships (for N+1 prevention)."""

    def __init__(self, graph_operations: GraphOperations):
        """Initialize entity relationships DataLoader.

        Args:
            graph_operations: Graph operations instance
        """
        self.graph_operations = graph_operations
        super().__init__(self._batch_load_entity_relationships)

    async def _batch_load_entity_relationships(
        self, entity_ids: list[str]
    ) -> list[list[dict[str, Any]]]:
        """Batch load relationships for multiple entities.

        Args:
            entity_ids: List of entity IDs

        Returns:
            List of relationship lists for each entity
        """
        if not settings.graphrag_data_path:
            return [[] for _ in entity_ids]

        try:
            # Query relationships for all entities at once
            result = await self.graph_operations.query_relationships(
                data_path=settings.graphrag_data_path,
                source_entities=entity_ids,
                limit=1000,  # Large limit to get all relationships
            )

            # Group relationships by source entity
            relationships_by_entity = defaultdict(list)
            for rel in result.get("relationships", []):
                source_id = rel.get("source")
                if source_id in entity_ids:
                    relationships_by_entity[source_id].append(rel)

            # Return results in the same order as requested
            return [relationships_by_entity.get(entity_id, []) for entity_id in entity_ids]

        except Exception as e:
            logger.error(f"Failed to batch load entity relationships: {e}")
            return [[] for _ in entity_ids]


class CommunityDataLoader(DataLoader):
    """DataLoader for communities."""

    def __init__(self, graph_operations: GraphOperations):
        """Initialize community DataLoader.

        Args:
            graph_operations: Graph operations instance
        """
        self.graph_operations = graph_operations
        super().__init__(self._batch_load_communities)

    async def _batch_load_communities(
        self, community_ids: list[str]
    ) -> list[dict[str, Any] | None]:
        """Batch load communities by IDs.

        Args:
            community_ids: List of community IDs to load

        Returns:
            List of community data or None for not found
        """
        if not settings.graphrag_data_path:
            return [None] * len(community_ids)

        try:
            # Query communities in batch
            result = await self.graph_operations.query_communities(
                data_path=settings.graphrag_data_path,
                community_ids=community_ids,
                limit=len(community_ids),
            )

            # Create lookup map
            community_map = {c["id"]: c for c in result.get("communities", [])}

            # Return results in the same order as requested
            return [community_map.get(community_id) for community_id in community_ids]

        except Exception as e:
            logger.error(f"Failed to batch load communities: {e}")
            return [None] * len(community_ids)


def create_dataloaders(graph_operations: GraphOperations) -> dict[str, DataLoader]:
    """Create all DataLoaders for GraphQL context.

    Args:
        graph_operations: Graph operations instance

    Returns:
        Dictionary of DataLoaders
    """
    return {
        "entity_loader": EntityDataLoader(graph_operations),
        "relationship_loader": RelationshipDataLoader(graph_operations),
        "entity_relationships_loader": EntityRelationshipsDataLoader(graph_operations),
        "community_loader": CommunityDataLoader(graph_operations),
    }
