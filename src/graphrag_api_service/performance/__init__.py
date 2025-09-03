# src/graphrag_api_service/performance/__init__.py
# Performance module initialization
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Performance optimization module for GraphRAG API Service.

This module provides comprehensive performance optimization features including:
- Advanced caching with TTL and LRU eviction
- Response compression and pagination
- Connection pooling for database operations
- Memory optimization for large datasets
- Performance monitoring and metrics collection
- Load testing framework
"""

from .cache_manager import CacheConfig, CacheManager, get_cache_manager
from .compression import (
    CompressionConfig,
    PaginatedResponse,
    PaginationParams,
    PerformanceMiddleware,
    get_performance_middleware,
)
from .connection_pool import (
    ConnectionPool,
    ConnectionPoolConfig,
    cleanup_connection_pool,
    get_connection_pool,
)
from .load_testing import BenchmarkSuite, LoadTestConfig, LoadTestScenario
from .memory_optimizer import MemoryConfig, MemoryOptimizer, get_memory_optimizer
from .monitoring import (
    AlertConfig,
    PerformanceMetrics,
    PerformanceMonitor,
    RequestMetrics,
    get_performance_monitor,
)
from .optimization_config import QueryOptimizationConfig

__all__ = [
    # Cache Manager
    "CacheConfig",
    "CacheManager",
    "get_cache_manager",
    # Compression and Pagination
    "CompressionConfig",
    "PaginatedResponse",
    "PaginationParams",
    "PerformanceMiddleware",
    "get_performance_middleware",
    # Connection Pool
    "ConnectionPool",
    "ConnectionPoolConfig",
    "get_connection_pool",
    "cleanup_connection_pool",
    # Load Testing
    "BenchmarkSuite",
    "LoadTestConfig",
    "LoadTestScenario",
    # Memory Optimizer
    "MemoryConfig",
    "MemoryOptimizer",
    "get_memory_optimizer",
    # Monitoring
    "AlertConfig",
    "PerformanceMetrics",
    "PerformanceMonitor",
    "RequestMetrics",
    "get_performance_monitor",
    # Configuration
    "QueryOptimizationConfig",
]
