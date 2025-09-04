# src/graphrag_api_service/performance/cache_manager.py
# Advanced Caching System for GraphRAG Operations
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Advanced caching system with TTL, LRU eviction, and performance monitoring."""

import asyncio
import gzip  # Moved from inside set method
import hashlib
import json
import logging
import pickle
import time
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheKeyComponents(BaseModel):
    """Components that form a cache key."""

    namespace: str
    identifier: str
    params: dict[str, Any] | None = None


class CacheConfig(BaseModel):
    """Configuration for the cache manager."""

    max_memory_mb: int = 512
    default_ttl: int = 3600  # 1 hour
    max_entries: int = 1000
    cleanup_interval: int = 300  # 5 minutes
    compression_enabled: bool = True
    metrics_enabled: bool = True


class CacheEntry(BaseModel):
    """Cache entry with metadata."""

    key: str
    data: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: int
    size_bytes: int
    compressed: bool


class CacheMetrics(BaseModel):
    """Cache performance metrics."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    memory_usage_mb: float = 0.0
    hit_rate: float = 0.0
    average_response_time: float = 0.0


class CacheManager:
    """Advanced cache manager with LRU eviction and TTL support."""

    def __init__(self, config: CacheConfig):
        """Initialize the cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self._cache: dict[str, CacheEntry] = {}
        self._access_order: list[str] = []
        self._lock = asyncio.Lock()
        self._metrics = CacheMetrics()
        self._cleanup_task: asyncio.Task[None] | None = None
        self._response_times: list[float] = []

    async def start(self) -> None:
        """Start the cache manager and cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache manager started")

    async def stop(self) -> None:
        """Stop the cache manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache manager stopped")

    def _generate_key(self, components: CacheKeyComponents) -> str:
        """Generate a cache key.

        Args:
            components: Components for the cache key (namespace, identifier, params)

        Returns:
            Generated cache key
        """
        key_data = {
            "namespace": components.namespace,
            "identifier": components.identifier,
            "params": components.params or {},
        }

        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    async def get(self, components: CacheKeyComponents) -> Any | None:
        """Get an item from the cache.

        Args:
            components: Components for the cache key (namespace, identifier, params)

        Returns:
            Cached item if found and valid
        """
        start_time = time.time()
        key = self._generate_key(components)

        async with self._lock:
            self._metrics.total_requests += 1

            entry = self._cache.get(key)
            if entry is None:
                self._metrics.cache_misses += 1
                self._record_response_time(time.time() - start_time)
                return None

            # Check TTL
            if time.time() - entry.created_at > entry.ttl:
                await self._remove_entry(key)
                self._metrics.cache_misses += 1
                self._record_response_time(time.time() - start_time)
                return None

            # Update access metadata
            entry.last_accessed = time.time()
            entry.access_count += 1

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            self._metrics.cache_hits += 1
            self._record_response_time(time.time() - start_time)

            logger.debug("Cache hit for key: %s", key)
            return entry.data

    async def set(
        self,
        components: CacheKeyComponents,
        data: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set an item in the cache.

        Args:
            components: Components for the cache key (namespace, identifier, params)
            data: Data to cache
            ttl: Time to live in seconds

        Returns:
            True if successfully cached
        """
        key = self._generate_key(components)
        ttl = ttl or self.config.default_ttl

        try:
            # Serialize and optionally compress data
            serialized_data = pickle.dumps(data)
            compressed = False

            if self.config.compression_enabled and len(serialized_data) > 1024:
                serialized_data = gzip.compress(serialized_data)
                compressed = True

            size_bytes = len(serialized_data)

            # Check memory limits
            if size_bytes > self.config.max_memory_mb * 1024 * 1024:
                logger.warning("Item too large to cache: %s bytes", size_bytes)
                return False

            async with self._lock:
                # Remove existing entry if present
                if key in self._cache:
                    await self._remove_entry(key)

                # Ensure we have space
                await self._ensure_space(size_bytes)

                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    data=serialized_data,
                    created_at=time.time(),
                    last_accessed=time.time(),
                    access_count=1,
                    ttl=ttl,
                    size_bytes=size_bytes,
                    compressed=compressed,
                )

                self._cache[key] = entry
                self._access_order.append(key)

                await self._update_memory_usage()

                logger.debug("Cached item with key: %s, size: %s bytes", key, size_bytes)
                return True

        except (pickle.PicklingError, OSError) as e:  # Catch specific exceptions
            logger.error("Failed to cache item: %s", e)
            return False

    async def delete(self, components: CacheKeyComponents) -> bool:
        """Delete an item from the cache.

        Args:
            components: Components for the cache key (namespace, identifier, params)

        Returns:
            True if item was deleted
        """
        key = self._generate_key(components)

        async with self._lock:
            if key in self._cache:
                await self._remove_entry(key)
                logger.debug("Deleted cache entry: %s", key)
                return True

        return False

    async def clear_namespace(self, namespace: str) -> int:
        """Clear all entries in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            Number of entries cleared
        """
        cleared_count = 0

        async with self._lock:
            keys_to_remove = []
            for key, _entry in self._cache.items():
                # Check if key belongs to namespace (simplified check)
                if key.startswith(namespace):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                await self._remove_entry(key)
                cleared_count += 1

        logger.info("Cleared %s entries from namespace: %s", cleared_count, namespace)
        return cleared_count

    async def _ensure_space(self, required_bytes: int) -> None:
        """Ensure there's enough space for a new entry.

        Args:
            required_bytes: Bytes required for new entry
        """
        current_memory = sum(entry.size_bytes for entry in self._cache.values())
        max_memory_bytes = self.config.max_memory_mb * 1024 * 1024

        # Check if we need to evict entries
        while (
            len(self._cache) >= self.config.max_entries
            or current_memory + required_bytes > max_memory_bytes
        ):
            if not self._access_order:
                break

            # Remove least recently used entry
            lru_key = self._access_order[0]
            entry = self._cache.get(lru_key)
            if entry:
                current_memory -= entry.size_bytes
                await self._remove_entry(lru_key)
                self._metrics.evictions += 1

    async def _remove_entry(self, key: str) -> None:
        """Remove an entry from the cache.

        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            del self._cache[key]

        if key in self._access_order:
            self._access_order.remove(key)

    async def _update_memory_usage(self) -> None:
        """Update memory usage metrics."""
        total_bytes = sum(entry.size_bytes for entry in self._cache.values())
        self._metrics.memory_usage_mb = total_bytes / (1024 * 1024)

    def _record_response_time(self, response_time: float) -> None:
        """Record response time for metrics.

        Args:
            response_time: Response time in seconds
        """
        self._response_times.append(response_time)

        # Keep only recent response times
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

        # Update average
        if self._response_times:
            self._metrics.average_response_time = sum(self._response_times) / len(
                self._response_times
            )

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired entries."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Catching a general Exception here to prevent the background cleanup loop
                # from crashing due to unforeseen errors, ensuring its continuous operation.
                # Specific exceptions should be handled if known.
                logger.error("Cache cleanup error: %s", e)

    async def _cleanup_expired(self) -> None:
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = []

        async with self._lock:
            for key, entry in self._cache.items():
                if current_time - entry.created_at > entry.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                await self._remove_entry(key)

            if expired_keys:
                await self._update_memory_usage()
                logger.debug("Cleaned up %s expired cache entries", len(expired_keys))

    async def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics.

        Returns:
            Cache metrics
        """
        async with self._lock:
            await self._update_memory_usage()

            # Calculate hit rate
            if self._metrics.total_requests > 0:
                self._metrics.hit_rate = self._metrics.cache_hits / self._metrics.total_requests

            return self._metrics.model_copy()

    async def get_status(self) -> dict[str, Any]:
        """Get cache status information.

        Returns:
            Cache status
        """
        metrics = await self.get_metrics()

        return {
            "entries": len(self._cache),
            "max_entries": self.config.max_entries,
            "memory_usage_mb": metrics.memory_usage_mb,
            "max_memory_mb": self.config.max_memory_mb,
            "hit_rate": metrics.hit_rate,
            "total_requests": metrics.total_requests,
            "cache_hits": metrics.cache_hits,
            "cache_misses": metrics.cache_misses,
            "evictions": metrics.evictions,
            "average_response_time_ms": metrics.average_response_time * 1000,
        }


# Global cache manager instance
# Rationale: Using a global instance for the cache manager simplifies access
# throughout the application and ensures a single, consistent cache state.
# While 'global' is generally discouraged, it's a common and acceptable pattern
# for managing singletons like this in Python applications.
_cache_manager: CacheManager | None = None


async def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance.

    Returns:
        Cache manager instance
    """
    global _cache_manager

    if _cache_manager is None:
        config = CacheConfig()
        _cache_manager = CacheManager(config)
        await _cache_manager.start()

    return _cache_manager


async def cleanup_cache_manager() -> None:
    """Clean up the global cache manager."""
    global _cache_manager

    if _cache_manager is not None:
        await _cache_manager.stop()
        _cache_manager = None
