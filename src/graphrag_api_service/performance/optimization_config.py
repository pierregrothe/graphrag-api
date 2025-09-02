# src/graphrag_api_service/performance/optimization_config.py
# Performance optimization configuration
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Performance optimization configuration and settings."""

from typing import Any

from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Cache configuration settings."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(default=3600, description="Cache TTL in seconds")
    max_size: int = Field(default=1000, description="Maximum cache entries")
    namespace_prefix: str = Field(default="graphrag", description="Cache namespace prefix")
    compression_enabled: bool = Field(default=True, description="Enable cache compression")
    compression_threshold: int = Field(
        default=1024, description="Minimum size for compression (bytes)"
    )


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    min_size: int = Field(default=5, description="Minimum pool size")
    max_size: int = Field(default=20, description="Maximum pool size")
    max_overflow: int = Field(default=10, description="Maximum overflow connections")
    pool_timeout: float = Field(default=30.0, description="Pool timeout in seconds")
    idle_timeout: int = Field(default=600, description="Idle connection timeout")
    recycle_time: int = Field(default=3600, description="Connection recycle time")


class QueryOptimizationConfig(BaseModel):
    """Query optimization settings."""

    enable_query_cache: bool = Field(default=True, description="Enable query result caching")
    enable_prepared_statements: bool = Field(
        default=True, description="Use prepared statements"
    )
    batch_size: int = Field(default=100, description="Default batch size for bulk operations")
    enable_connection_pooling: bool = Field(default=True, description="Enable connection pooling")
    enable_async_queries: bool = Field(default=True, description="Enable async query execution")


class MemoryOptimizationConfig(BaseModel):
    """Memory optimization settings."""

    gc_threshold: float = Field(
        default=0.75, description="Memory usage threshold for GC trigger"
    )
    gc_interval: int = Field(default=300, description="GC interval in seconds")
    cache_memory_limit: int = Field(
        default=500 * 1024 * 1024, description="Cache memory limit in bytes"
    )
    enable_memory_profiling: bool = Field(default=False, description="Enable memory profiling")
    enable_auto_cleanup: bool = Field(default=True, description="Enable automatic memory cleanup")


class CompressionConfig(BaseModel):
    """Response compression settings."""

    enabled: bool = Field(default=True, description="Enable response compression")
    algorithms: list[str] = Field(
        default=["gzip", "br"], description="Supported compression algorithms"
    )
    minimum_size: int = Field(
        default=1024, description="Minimum response size for compression"
    )
    compression_level: int = Field(default=6, description="Compression level (1-9)")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = Field(default=True, description="Enable rate limiting")
    requests_per_minute: int = Field(default=100, description="Requests per minute")
    burst_size: int = Field(default=20, description="Burst size for rate limiting")
    by_ip: bool = Field(default=True, description="Rate limit by IP address")
    by_user: bool = Field(default=True, description="Rate limit by authenticated user")


class PerformanceConfig(BaseModel):
    """Main performance configuration."""

    cache: CacheConfig = Field(default_factory=CacheConfig)
    connection_pool: ConnectionPoolConfig = Field(default_factory=ConnectionPoolConfig)
    query_optimization: QueryOptimizationConfig = Field(default_factory=QueryOptimizationConfig)
    memory_optimization: MemoryOptimizationConfig = Field(
        default_factory=MemoryOptimizationConfig
    )
    compression: CompressionConfig = Field(default_factory=CompressionConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Global settings
    enable_performance_monitoring: bool = Field(
        default=True, description="Enable performance monitoring"
    )
    enable_request_profiling: bool = Field(
        default=False, description="Enable request profiling"
    )
    slow_query_threshold: float = Field(
        default=1.0, description="Slow query threshold in seconds"
    )
    enable_optimizations: bool = Field(
        default=True, description="Enable all performance optimizations"
    )

    def get_optimization_settings(self) -> dict[str, Any]:
        """Get optimization settings as dictionary."""
        if not self.enable_optimizations:
            return {
                "cache_enabled": False,
                "pooling_enabled": False,
                "compression_enabled": False,
                "rate_limiting_enabled": False,
            }

        return {
            "cache_enabled": self.cache.enabled,
            "cache_ttl": self.cache.ttl,
            "cache_max_size": self.cache.max_size,
            "pooling_enabled": self.query_optimization.enable_connection_pooling,
            "pool_size": self.connection_pool.max_size,
            "compression_enabled": self.compression.enabled,
            "compression_algorithms": self.compression.algorithms,
            "rate_limiting_enabled": self.rate_limit.enabled,
            "rate_limit": self.rate_limit.requests_per_minute,
            "memory_auto_cleanup": self.memory_optimization.enable_auto_cleanup,
        }


# Default configuration instance
default_performance_config = PerformanceConfig()


def get_performance_config() -> PerformanceConfig:
    """Get the current performance configuration."""
    return default_performance_config