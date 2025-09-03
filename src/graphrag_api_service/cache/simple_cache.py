# src/graphrag_api_service/cache/simple_cache.py
# Simple in-memory cache for small-scale deployment
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Simple cache implementation for GraphRAG API."""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SimpleMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize memory cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache: dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                # Expired - remove from cache
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")

        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
        logger.debug(f"Cached key: {key} with TTL: {ttl}s")

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Deleted cache key: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cached values."""
        self.cache.clear()
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [key for key, (_, expiry) in self.cache.items() if current_time >= expiry]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
        }


class SimpleCacheManager:
    """Simple cache manager supporting memory and Redis (optional)."""

    def __init__(
        self, cache_type: str = "memory", cache_ttl: int = 3600, redis_url: str | None = None
    ):
        """Initialize cache manager.

        Args:
            cache_type: Type of cache ("memory" or "redis")
            cache_ttl: Default TTL in seconds
            redis_url: Redis URL (required if cache_type is "redis")
        """
        self.cache_type = cache_type
        self.cache_ttl = cache_ttl

        if cache_type == "memory":
            self.backend = SimpleMemoryCache(default_ttl=cache_ttl)
            logger.info("Using in-memory cache")
        elif cache_type == "redis":
            # Redis support can be added later if needed
            raise NotImplementedError(
                "Redis cache not implemented in simple mode. Use 'memory' instead."
            )
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        self.backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return self.backend.delete(key)

    def clear(self) -> None:
        """Clear all cached values."""
        self.backend.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self.backend, "get_stats"):
            return self.backend.get_stats()
        return {}


# Global cache manager
_cache_manager: SimpleCacheManager | None = None


def get_cache_manager(
    cache_type: str | None = None,
    cache_ttl: int | None = None,
    redis_url: str | None = None,
) -> SimpleCacheManager:
    """Get the global cache manager.

    Args:
        cache_type: Cache type (uses environment if not specified)
        cache_ttl: Cache TTL (uses environment if not specified)
        redis_url: Redis URL (uses environment if not specified)

    Returns:
        SimpleCacheManager instance
    """
    global _cache_manager

    if _cache_manager is None:
        from ..config import Settings

        settings = Settings()

        cache_type = cache_type or settings.cache_type
        cache_ttl = cache_ttl or settings.cache_ttl
        redis_url = redis_url or (settings.redis_url if settings.redis_enabled else None)

        _cache_manager = SimpleCacheManager(
            cache_type=cache_type, cache_ttl=cache_ttl, redis_url=redis_url
        )

    return _cache_manager
