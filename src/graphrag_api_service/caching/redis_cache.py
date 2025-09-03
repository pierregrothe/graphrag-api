# src/graphrag_api_service/caching/redis_cache.py
# Redis-based Distributed Caching for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Redis-based distributed caching with intelligent invalidation and compression."""

import logging
import pickle
import zlib
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RedisCacheConfig(BaseModel):
    """Redis cache configuration."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30

    # Cache settings
    default_ttl: int = 3600  # 1 hour
    max_value_size: int = 1024 * 1024  # 1MB
    compression_threshold: int = 1024  # Compress values larger than 1KB
    key_prefix: str = "graphrag:"


class RedisDistributedCache:
    """Redis-based distributed cache with advanced features."""

    def __init__(self, config: RedisCacheConfig):
        """Initialize Redis cache.

        Args:
            config: Redis configuration
        """
        self.config = config
        self.redis_pool: redis.ConnectionPool | None = None
        self.redis_client: redis.Redis | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                ssl=self.config.ssl,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
            )

            self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # Test connection
            await self.redis_client.ping()
            self._connected = True

            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
        self._connected = False
        logger.info("Disconnected from Redis")

    def _make_key(self, namespace: str, key: str) -> str:
        """Create a prefixed cache key.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Prefixed key
        """
        return f"{self.config.key_prefix}{namespace}:{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally compress a value.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes
        """
        # Serialize using pickle for Python objects
        serialized = pickle.dumps(value)

        # Compress if value is large enough
        if len(serialized) > self.config.compression_threshold:
            compressed = zlib.compress(serialized)
            # Only use compression if it actually reduces size
            if len(compressed) < len(serialized):
                return b"compressed:" + compressed

        return b"raw:" + serialized

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize and decompress a value.

        Args:
            data: Serialized data

        Returns:
            Deserialized value
        """
        if data.startswith(b"compressed:"):
            compressed_data = data[11:]  # Remove "compressed:" prefix
            decompressed = zlib.decompress(compressed_data)
            return pickle.loads(decompressed)
        elif data.startswith(b"raw:"):
            raw_data = data[4:]  # Remove "raw:" prefix
            return pickle.loads(raw_data)
        else:
            # Fallback for legacy data
            return pickle.loads(data)

    async def get(self, namespace: str, key: str) -> Any | None:
        """Get a value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._connected:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            assert self.redis_client is not None  # Already checked _connected
            data = await self.redis_client.get(cache_key)

            if data is None:
                return None

            return self._deserialize_value(data)

        except Exception as e:
            logger.error(f"Error getting cache value {namespace}:{key}: {e}")
            return None

    async def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        if not self._connected:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            serialized_value = self._serialize_value(value)

            # Check value size
            if len(serialized_value) > self.config.max_value_size:
                logger.warning(f"Value too large for cache: {len(serialized_value)} bytes")
                return False

            ttl = ttl or self.config.default_ttl

            assert self.redis_client is not None  # Already checked _connected
            await self.redis_client.setex(cache_key, ttl, serialized_value)
            return True

        except Exception as e:
            logger.error(f"Error setting cache value {namespace}:{key}: {e}")
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete a value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if successful
        """
        if not self._connected:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            assert self.redis_client is not None  # Already checked _connected
            result = await self.redis_client.delete(cache_key)
            return bool(result > 0)

        except Exception as e:
            logger.error(f"Error deleting cache value {namespace}:{key}: {e}")
            return False

    async def exists(self, namespace: str, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if key exists
        """
        if not self._connected:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            assert self.redis_client is not None  # Already checked _connected
            result = await self.redis_client.exists(cache_key)
            return bool(result > 0)

        except Exception as e:
            logger.error(f"Error checking cache existence {namespace}:{key}: {e}")
            return False

    async def invalidate_pattern(self, namespace: str, pattern: str) -> int:
        """Invalidate all keys matching a pattern.

        Args:
            namespace: Cache namespace
            pattern: Key pattern (supports wildcards)

        Returns:
            Number of keys deleted
        """
        if not self._connected:
            return 0

        try:
            search_pattern = self._make_key(namespace, pattern)
            assert self.redis_client is not None  # Already checked _connected
            keys = await self.redis_client.keys(search_pattern)

            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys matching {search_pattern}")
                return int(deleted)

            return 0

        except Exception as e:
            logger.error(f"Error invalidating cache pattern {namespace}:{pattern}: {e}")
            return 0

    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace.

        Args:
            namespace: Cache namespace to clear

        Returns:
            Number of keys deleted
        """
        return await self.invalidate_pattern(namespace, "*")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self._connected:
            return {"connected": False}

        try:
            assert self.redis_client is not None  # Already checked _connected
            info = await self.redis_client.info()

            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
                ),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate.

        Args:
            hits: Number of cache hits
            misses: Number of cache misses

        Returns:
            Hit rate as percentage
        """
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100


class GraphRAGRedisCache:
    """GraphRAG-specific Redis cache with intelligent invalidation."""

    def __init__(self, redis_cache: RedisDistributedCache):
        """Initialize GraphRAG Redis cache.

        Args:
            redis_cache: Redis cache instance
        """
        self.redis_cache = redis_cache
        self.namespaces = {
            "entities": "entities",
            "relationships": "relationships",
            "communities": "communities",
            "queries": "queries",
            "embeddings": "embeddings",
            "graph_stats": "graph_stats",
        }

    async def cache_entities(
        self, workspace_id: str, entities: list[dict[str, Any]], ttl: int = 3600
    ) -> bool:
        """Cache entity data.

        Args:
            workspace_id: Workspace identifier
            entities: Entity data
            ttl: Time to live

        Returns:
            True if successful
        """
        key = f"workspace:{workspace_id}"
        return await self.redis_cache.set(self.namespaces["entities"], key, entities, ttl)

    async def get_cached_entities(self, workspace_id: str) -> list[dict[str, Any]] | None:
        """Get cached entity data.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Cached entities or None
        """
        key = f"workspace:{workspace_id}"
        return await self.redis_cache.get(self.namespaces["entities"], key)

    async def cache_query_result(self, query_hash: str, result: Any, ttl: int = 1800) -> bool:
        """Cache query result.

        Args:
            query_hash: Hash of the query
            result: Query result
            ttl: Time to live

        Returns:
            True if successful
        """
        return await self.redis_cache.set(self.namespaces["queries"], query_hash, result, ttl)

    async def get_cached_query_result(self, query_hash: str) -> Any | None:
        """Get cached query result.

        Args:
            query_hash: Hash of the query

        Returns:
            Cached result or None
        """
        return await self.redis_cache.get(self.namespaces["queries"], query_hash)

    async def invalidate_workspace_cache(self, workspace_id: str) -> int:
        """Invalidate all cache entries for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            Number of keys invalidated
        """
        total_invalidated = 0

        # Invalidate entities
        total_invalidated += await self.redis_cache.invalidate_pattern(
            self.namespaces["entities"], f"workspace:{workspace_id}*"
        )

        # Invalidate relationships
        total_invalidated += await self.redis_cache.invalidate_pattern(
            self.namespaces["relationships"], f"workspace:{workspace_id}*"
        )

        # Invalidate communities
        total_invalidated += await self.redis_cache.invalidate_pattern(
            self.namespaces["communities"], f"workspace:{workspace_id}*"
        )

        logger.info(f"Invalidated {total_invalidated} cache entries for workspace {workspace_id}")
        return total_invalidated


# Global Redis cache instance
_redis_cache: RedisDistributedCache | None = None
_graphrag_cache: GraphRAGRedisCache | None = None


async def get_redis_cache() -> RedisDistributedCache | None:
    """Get the global Redis cache instance.

    Returns:
        Redis cache instance or None if not configured
    """
    return _redis_cache


async def initialize_redis_cache(config: RedisCacheConfig) -> RedisDistributedCache:
    """Initialize Redis cache.

    Args:
        config: Redis configuration

    Returns:
        Redis cache instance
    """
    global _redis_cache, _graphrag_cache

    _redis_cache = RedisDistributedCache(config)
    await _redis_cache.connect()

    _graphrag_cache = GraphRAGRedisCache(_redis_cache)

    return _redis_cache


async def get_graphrag_cache() -> GraphRAGRedisCache | None:
    """Get the GraphRAG-specific cache instance.

    Returns:
        GraphRAG cache instance or None if not initialized
    """
    return _graphrag_cache
