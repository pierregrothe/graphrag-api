# src/graphrag_api_service/graphql/subscriptions.py
# GraphQL Subscriptions for Real-time Updates
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL subscriptions for real-time updates and notifications."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import strawberry
from strawberry.types import Info

from .types import (
    Community,
    Entity,
    IndexingStatus,
    PerformanceMetrics,
    Relationship,
    SystemStatus,
)

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages GraphQL subscriptions and real-time updates."""

    def __init__(self) -> None:
        """Initialize the subscription manager."""
        self._subscribers: dict[str, list[asyncio.Queue]] = {
            "indexing_updates": [],
            "entity_updates": [],
            "relationship_updates": [],
            "community_updates": [],
            "system_updates": [],
            "performance_updates": [],
        }
        self._running = False

    async def start(self) -> None:
        """Start the subscription manager."""
        self._running = True
        logger.info("Subscription manager started")

    async def stop(self) -> None:
        """Stop the subscription manager."""
        self._running = False
        # Close all subscriber queues
        for topic_queues in self._subscribers.values():
            for queue in topic_queues:
                try:
                    queue.put_nowait(None)  # Signal end
                except asyncio.QueueFull:
                    pass
        logger.info("Subscription manager stopped")

    async def subscribe(self, topic: str) -> AsyncGenerator[Any, None]:
        """Subscribe to a topic for real-time updates.

        Args:
            topic: Topic to subscribe to

        Yields:
            Updates for the subscribed topic
        """
        if topic not in self._subscribers:
            raise ValueError(f"Unknown subscription topic: {topic}")

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=100)
        self._subscribers[topic].append(queue)

        try:
            while self._running:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if update is None:  # End signal
                        break
                    yield update
                except TimeoutError:
                    continue
        finally:
            # Remove subscriber
            if queue in self._subscribers[topic]:
                self._subscribers[topic].remove(queue)

    async def publish(self, topic: str, data: Any) -> None:
        """Publish data to all subscribers of a topic.

        Args:
            topic: Topic to publish to
            data: Data to publish
        """
        if topic not in self._subscribers:
            return

        # Send to all subscribers
        for queue in self._subscribers[topic].copy():
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                # Remove full queues
                self._subscribers[topic].remove(queue)

    def get_subscriber_count(self, topic: str) -> int:
        """Get the number of subscribers for a topic.

        Args:
            topic: Topic to check

        Returns:
            Number of subscribers
        """
        return len(self._subscribers.get(topic, []))


# Global subscription manager
_subscription_manager: SubscriptionManager | None = None


async def get_subscription_manager() -> SubscriptionManager:
    """Get the global subscription manager.

    Returns:
        Subscription manager instance
    """
    global _subscription_manager

    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
        await _subscription_manager.start()

    return _subscription_manager


@strawberry.type
class Subscription:
    """GraphQL subscription root type."""

    @strawberry.subscription
    async def indexing_updates(self, info: Info) -> AsyncGenerator[IndexingStatus, None]:
        """Subscribe to indexing status updates.

        Yields:
            Indexing status updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("indexing_updates"):
            if isinstance(update, dict):
                yield IndexingStatus(
                    workspace_id=update.get("workspace_id", ""),
                    status=update.get("status", "unknown"),
                    progress=update.get("progress", 0.0),
                    message=update.get("message", ""),
                    error=update.get("error"),
                    started_at=update.get("started_at"),
                    completed_at=update.get("completed_at"),
                )

    @strawberry.subscription
    async def entity_updates(
        self, info: Info, workspace_id: str | None = None
    ) -> AsyncGenerator[Entity, None]:
        """Subscribe to entity updates.

        Args:
            workspace_id: Optional workspace ID to filter updates

        Yields:
            Entity updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("entity_updates"):
            if isinstance(update, dict):
                # Filter by workspace if specified
                if workspace_id and update.get("workspace_id") != workspace_id:
                    continue

                yield Entity(
                    id=update.get("id", ""),
                    title=update.get("title", ""),
                    type=update.get("type", ""),
                    description=update.get("description", ""),
                    degree=update.get("degree", 0),
                    community_ids=update.get("community_ids", []),
                    text_unit_ids=update.get("text_unit_ids", []),
                )

    @strawberry.subscription
    async def relationship_updates(
        self, info: Info, workspace_id: str | None = None
    ) -> AsyncGenerator[Relationship, None]:
        """Subscribe to relationship updates.

        Args:
            workspace_id: Optional workspace ID to filter updates

        Yields:
            Relationship updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("relationship_updates"):
            if isinstance(update, dict):
                # Filter by workspace if specified
                if workspace_id and update.get("workspace_id") != workspace_id:
                    continue

                yield Relationship(
                    id=update.get("id", ""),
                    source=update.get("source", ""),
                    target=update.get("target", ""),
                    type=update.get("type", ""),
                    description=update.get("description", ""),
                    weight=update.get("weight", 0.0),
                    text_unit_ids=update.get("text_unit_ids", []),
                )

    @strawberry.subscription
    async def community_updates(
        self, info: Info, workspace_id: str | None = None
    ) -> AsyncGenerator[Community, None]:
        """Subscribe to community updates.

        Args:
            workspace_id: Optional workspace ID to filter updates

        Yields:
            Community updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("community_updates"):
            if isinstance(update, dict):
                # Filter by workspace if specified
                if workspace_id and update.get("workspace_id") != workspace_id:
                    continue

                yield Community(
                    id=update.get("id", ""),
                    level=update.get("level", 0),
                    title=update.get("title", ""),
                    entity_ids=update.get("entity_ids", []),
                    relationship_ids=update.get("relationship_ids", []),
                )

    @strawberry.subscription
    async def system_updates(self, info: Info) -> AsyncGenerator[SystemStatus, None]:
        """Subscribe to system status updates.

        Yields:
            System status updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("system_updates"):
            if isinstance(update, dict):
                yield SystemStatus(
                    version=update.get("version", ""),
                    environment=update.get("environment", "development"),
                    uptime_seconds=update.get("uptime_seconds", 0.0),
                    provider_info=update.get("provider_info", {}),
                    graph_metrics=update.get("graph_metrics", {}),
                    indexing_metrics=update.get("indexing_metrics", {}),
                    query_metrics=update.get("query_metrics", {}),
                    workspace_metrics=update.get("workspace_metrics", {}),
                    recent_operations=update.get("recent_operations", []),
                )

    @strawberry.subscription
    async def performance_updates(self, info: Info) -> AsyncGenerator[PerformanceMetrics, None]:
        """Subscribe to performance metrics updates.

        Yields:
            Performance metrics updates
        """
        subscription_manager = await get_subscription_manager()

        async for update in subscription_manager.subscribe("performance_updates"):
            if isinstance(update, dict):
                yield PerformanceMetrics(
                    timestamp=update.get("timestamp", 0.0),
                    cpu_usage_percent=update.get("cpu_usage_percent", 0.0),
                    memory_usage_mb=update.get("memory_usage_mb", 0.0),
                    active_connections=update.get("active_connections", 0),
                    requests_per_second=update.get("requests_per_second", 0.0),
                    average_response_time=update.get("average_response_time", 0.0),
                    cache_hit_rate=update.get("cache_hit_rate", 0.0),
                )
