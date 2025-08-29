# src/graphrag_api_service/monitoring/prometheus.py
# Prometheus Metrics Integration for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Prometheus metrics collection and export for comprehensive monitoring."""

import logging
import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """Prometheus metrics collector for GraphRAG API."""

    def __init__(self, registry: CollectorRegistry | None = None):
        """Initialize Prometheus metrics.

        Args:
            registry: Optional custom registry
        """
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Set up all Prometheus metrics."""

        # Request metrics
        self.request_count = Counter(
            "graphrag_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            "graphrag_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        # GraphQL metrics
        self.graphql_query_count = Counter(
            "graphrag_graphql_queries_total",
            "Total number of GraphQL queries",
            ["operation_type", "operation_name"],
            registry=self.registry,
        )

        self.graphql_query_duration = Histogram(
            "graphrag_graphql_query_duration_seconds",
            "GraphQL query duration in seconds",
            ["operation_type", "operation_name"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        self.graphql_query_complexity = Histogram(
            "graphrag_graphql_query_complexity",
            "GraphQL query complexity score",
            ["operation_type"],
            buckets=[10, 50, 100, 250, 500, 1000, 2500],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_hits = Counter(
            "graphrag_cache_hits_total",
            "Total number of cache hits",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_misses = Counter(
            "graphrag_cache_misses_total",
            "Total number of cache misses",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_size = Gauge(
            "graphrag_cache_size_bytes",
            "Current cache size in bytes",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_entries = Gauge(
            "graphrag_cache_entries_total",
            "Current number of cache entries",
            ["cache_type"],
            registry=self.registry,
        )

        # Database metrics
        self.db_connections_active = Gauge(
            "graphrag_db_connections_active",
            "Number of active database connections",
            registry=self.registry,
        )

        self.db_connections_idle = Gauge(
            "graphrag_db_connections_idle",
            "Number of idle database connections",
            registry=self.registry,
        )

        self.db_query_duration = Histogram(
            "graphrag_db_query_duration_seconds",
            "Database query duration in seconds",
            ["query_type"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
            registry=self.registry,
        )

        # System metrics
        self.memory_usage = Gauge(
            "graphrag_memory_usage_bytes",
            "Current memory usage in bytes",
            ["type"],
            registry=self.registry,
        )

        self.cpu_usage = Gauge(
            "graphrag_cpu_usage_percent", "Current CPU usage percentage", registry=self.registry
        )

        self.active_sessions = Gauge(
            "graphrag_active_sessions", "Number of active user sessions", registry=self.registry
        )

        # GraphRAG specific metrics
        self.entities_total = Gauge(
            "graphrag_entities_total",
            "Total number of entities in the graph",
            ["workspace"],
            registry=self.registry,
        )

        self.relationships_total = Gauge(
            "graphrag_relationships_total",
            "Total number of relationships in the graph",
            ["workspace"],
            registry=self.registry,
        )

        self.communities_total = Gauge(
            "graphrag_communities_total",
            "Total number of communities in the graph",
            ["workspace"],
            registry=self.registry,
        )

        self.indexing_jobs_active = Gauge(
            "graphrag_indexing_jobs_active",
            "Number of active indexing jobs",
            registry=self.registry,
        )

        self.indexing_duration = Histogram(
            "graphrag_indexing_duration_seconds",
            "Indexing job duration in seconds",
            ["workspace", "status"],
            buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "graphrag_errors_total",
            "Total number of errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # Security metrics
        self.rate_limit_hits = Counter(
            "graphrag_rate_limit_hits_total",
            "Total number of rate limit hits",
            ["client_ip"],
            registry=self.registry,
        )

        self.authentication_attempts = Counter(
            "graphrag_authentication_attempts_total",
            "Total number of authentication attempts",
            ["status"],
            registry=self.registry,
        )

        # Application info
        self.app_info = Info("graphrag_app_info", "Application information", registry=self.registry)

    def record_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Record HTTP request metrics.

        Args:
            method: HTTP method
            endpoint: Request endpoint
            status: HTTP status code
            duration: Request duration in seconds
        """
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def record_graphql_query(
        self, operation_type: str, operation_name: str, duration: float, complexity: int
    ) -> None:
        """Record GraphQL query metrics.

        Args:
            operation_type: Type of GraphQL operation (query, mutation, subscription)
            operation_name: Name of the operation
            duration: Query duration in seconds
            complexity: Query complexity score
        """
        self.graphql_query_count.labels(
            operation_type=operation_type, operation_name=operation_name
        ).inc()

        self.graphql_query_duration.labels(
            operation_type=operation_type, operation_name=operation_name
        ).observe(duration)

        self.graphql_query_complexity.labels(operation_type=operation_type).observe(complexity)

    def record_cache_hit(self, cache_type: str) -> None:
        """Record cache hit.

        Args:
            cache_type: Type of cache
        """
        self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str) -> None:
        """Record cache miss.

        Args:
            cache_type: Type of cache
        """
        self.cache_misses.labels(cache_type=cache_type).inc()

    def update_cache_metrics(self, cache_type: str, size_bytes: int, entries: int) -> None:
        """Update cache size metrics.

        Args:
            cache_type: Type of cache
            size_bytes: Cache size in bytes
            entries: Number of cache entries
        """
        self.cache_size.labels(cache_type=cache_type).set(size_bytes)
        self.cache_entries.labels(cache_type=cache_type).set(entries)

    def update_db_connections(self, active: int, idle: int) -> None:
        """Update database connection metrics.

        Args:
            active: Number of active connections
            idle: Number of idle connections
        """
        self.db_connections_active.set(active)
        self.db_connections_idle.set(idle)

    def record_db_query(self, query_type: str, duration: float) -> None:
        """Record database query metrics.

        Args:
            query_type: Type of database query
            duration: Query duration in seconds
        """
        self.db_query_duration.labels(query_type=query_type).observe(duration)

    def update_system_metrics(
        self, memory_bytes: int, cpu_percent: float, active_sessions: int
    ) -> None:
        """Update system metrics.

        Args:
            memory_bytes: Memory usage in bytes
            cpu_percent: CPU usage percentage
            active_sessions: Number of active sessions
        """
        self.memory_usage.labels(type="total").set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
        self.active_sessions.set(active_sessions)

    def update_graph_metrics(
        self, workspace: str, entities: int, relationships: int, communities: int
    ) -> None:
        """Update graph-specific metrics.

        Args:
            workspace: Workspace identifier
            entities: Number of entities
            relationships: Number of relationships
            communities: Number of communities
        """
        self.entities_total.labels(workspace=workspace).set(entities)
        self.relationships_total.labels(workspace=workspace).set(relationships)
        self.communities_total.labels(workspace=workspace).set(communities)

    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics.

        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def record_rate_limit_hit(self, client_ip: str) -> None:
        """Record rate limit hit.

        Args:
            client_ip: Client IP address
        """
        self.rate_limit_hits.labels(client_ip=client_ip).inc()

    def set_app_info(self, version: str, environment: str, build_date: str) -> None:
        """Set application information.

        Args:
            version: Application version
            environment: Environment (dev, staging, prod)
            build_date: Build date
        """
        self.app_info.info(
            {
                "version": version,
                "environment": environment,
                "build_date": build_date,
            }
        )

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry).decode("utf-8")

    def get_content_type(self) -> str:
        """Get the content type for metrics endpoint.

        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics:
    """Get the global metrics instance.

    Returns:
        PrometheusMetrics instance
    """
    global _metrics

    if _metrics is None:
        _metrics = PrometheusMetrics()

        # Set application info
        _metrics.set_app_info(
            version="1.0.0", environment="production", build_date=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    return _metrics
