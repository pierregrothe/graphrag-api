# src/graphrag_api_service/performance/monitoring.py
# Performance Monitoring and Metrics Collection
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Performance monitoring system with metrics collection and alerting."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import psutil
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PerformanceMetrics(BaseModel):
    """Performance metrics data structure."""

    timestamp: float
    cpu_usage_percent: float
    memory_usage_mb: float
    memory_usage_percent: float
    disk_usage_percent: float
    active_connections: int
    request_count: int
    average_response_time: float
    error_rate: float


class RequestMetrics(BaseModel):
    """Individual request metrics."""

    endpoint: str
    method: str
    status_code: int
    response_time: float
    timestamp: float
    user_agent: str | None = None
    ip_address: str | None = None


class AlertConfig(BaseModel):
    """Configuration for performance alerts."""

    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    response_time_threshold: float = 5.0
    error_rate_threshold: float = 0.05
    enabled: bool = True


class MetricsStore:
    """Manages storage and retrieval of performance and request metrics."""

    def __init__(self):
        """Initialize the MetricsStore."""
        self._metrics_history: list[PerformanceMetrics] = []
        self._request_history: list[RequestMetrics] = []
        self._response_times: list[float] = []
        self._request_count = 0
        self._error_count = 0

    def add_performance_metrics(self, metrics: PerformanceMetrics) -> None:
        """Add performance metrics to history."""
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]

    def add_request_metrics(self, metrics: RequestMetrics) -> None:
        """Add request metrics to history."""
        self._request_history.append(metrics)
        if len(self._request_history) > 10000:
            self._request_history = self._request_history[-10000:]

    def add_response_time(self, response_time: float) -> None:
        """Add response time to history."""
        self._response_times.append(response_time)
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

    def increment_request_count(self) -> None:
        """Increment total request count."""
        self._request_count += 1

    def increment_error_count(self) -> None:
        """Increment total error count."""
        self._error_count += 1

    def get_current_metrics(self) -> PerformanceMetrics | None:
        """Get the most recent performance metrics."""
        if self._metrics_history:
            return self._metrics_history[-1]
        return None

    def get_metrics_history(self, limit: int = 100) -> list[PerformanceMetrics]:
        """Get historical performance metrics."""
        return self._metrics_history[-limit:].copy()

    def get_request_metrics(self, limit: int = 100) -> list[RequestMetrics]:
        """Get recent request metrics."""
        return self._request_history[-limit:].copy()

    def get_response_times(self) -> list[float]:
        """Get historical response times."""
        return self._response_times.copy()

    def get_request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def get_error_count(self) -> int:
        """Get total error count."""
        return self._error_count

    def update_request_status_code(self, request_id: str, status_code: int) -> None:
        """Update status code for a specific request."""
        for request_metric in reversed(self._request_history):
            if request_metric.endpoint in request_id:
                request_metric.status_code = status_code
                break


class PerformanceMonitor:
    """Performance monitoring system with real-time metrics collection."""

    def __init__(self, alert_config: AlertConfig | None = None):
        """Initialize the performance monitor.

        Args:
            alert_config: Alert configuration
        """
        self.alert_config = alert_config or AlertConfig()
        self._monitoring_task: asyncio.Task | None = None
        self._active_requests: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._metrics_store = MetricsStore()  # Use the new MetricsStore class

    async def start_monitoring(self, interval: float = 30.0) -> None:
        """Start the performance monitoring task.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
            logger.info("Performance monitoring started with %ss interval", interval)

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring task."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Performance monitoring stopped")

    @asynccontextmanager
    async def track_request(
        self,
        endpoint: str,
        method: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Track a request's performance.

        Args:
            endpoint: API endpoint
            method: HTTP method
            user_agent: User agent string
            ip_address: Client IP address

        Yields:
            Request ID for tracking
        """
        request_id = f"{endpoint}_{method}_{time.time()}"
        start_time = time.time()

        async with self._lock:
            self._active_requests[request_id] = start_time
            self._metrics_store.increment_request_count()

        try:
            yield request_id
        except Exception:
            async with self._lock:
                self._metrics_store.increment_error_count()
            raise
        finally:
            end_time = time.time()
            response_time = end_time - start_time

            async with self._lock:
                if request_id in self._active_requests:
                    del self._active_requests[request_id]

                self._metrics_store.add_response_time(response_time)

                # Record request metrics
                request_metric = RequestMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=200,  # Default, should be updated by caller
                    response_time=response_time,
                    timestamp=end_time,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )

                self._metrics_store.add_request_metrics(request_metric)

    async def record_error(self, request_id: str, status_code: int) -> None:
        """Record an error for a request.

        Args:
            request_id: Request ID
            status_code: HTTP status code
        """
        async with self._lock:
            self._metrics_store.increment_error_count()

            # Update request metrics if found
            self._metrics_store.update_request_status_code(request_id, status_code)

    async def _monitoring_loop(self, interval: float) -> None:
        """Run main monitoring loop.

        Args:
            interval: Monitoring interval in seconds
        """
        while True:
            try:
                await self._collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Catching a general Exception here to prevent the background monitoring loop
                # from crashing due to unforeseen errors, ensuring its continuous operation.
                # Specific exceptions should be handled if known.
                logger.error("Monitoring loop error: %s", e)
                await asyncio.sleep(interval)

    async def _collect_metrics(self) -> None:
        """Collect system and application metrics."""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # Get disk usage for the current working directory (cross-platform)
            import os

            current_path = os.getcwd()
            disk = psutil.disk_usage(current_path)

            # Application metrics
            async with self._lock:
                active_connections = len(self._active_requests)
                request_count = self._metrics_store.get_request_count()
                error_count = self._metrics_store.get_error_count()

                # Calculate average response time
                avg_response_time = 0.0
                response_times = self._metrics_store.get_response_times()
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)

                # Calculate error rate
                error_rate = 0.0
                if request_count > 0:
                    error_rate = error_count / request_count

            # Create metrics entry
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory.used / (1024 * 1024),
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
                active_connections=active_connections,
                request_count=request_count,
                average_response_time=avg_response_time,
                error_rate=error_rate,
            )

            # Store metrics
            async with self._lock:
                self._metrics_store.add_performance_metrics(metrics)

            # Check alerts
            await self._check_alerts(metrics)

            logger.debug(
                "Metrics collected - CPU: %.1f%%, Memory: %.1f%%, Requests: %s, Avg Response: %.3fs",
                cpu_usage,
                memory.percent,
                request_count,
                avg_response_time,
            )

        except psutil.Error as e:
            # Pylint might incorrectly flag psutil.Error as too general, but it is a specific exception
            # provided by the psutil library for its own errors.
            logger.error("Failed to collect metrics: %s", e)

    async def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for alert conditions.

        Args:
            metrics: Current performance metrics
        """
        if not self.alert_config.enabled:
            return

        alerts = []

        if metrics.cpu_usage_percent > self.alert_config.cpu_threshold:
            alerts.append(f"High CPU usage: {metrics.cpu_usage_percent:.1f}%")

        if metrics.memory_usage_percent > self.alert_config.memory_threshold:
            alerts.append(f"High memory usage: {metrics.memory_usage_percent:.1f}%")

        if metrics.average_response_time > self.alert_config.response_time_threshold:
            alerts.append(f"High response time: {metrics.average_response_time:.3f}s")

        if metrics.error_rate > self.alert_config.error_rate_threshold:
            alerts.append(f"High error rate: {metrics.error_rate:.1%}")

        for alert in alerts:
            logger.warning("PERFORMANCE ALERT: %s", alert)

    async def get_current_metrics(self) -> PerformanceMetrics | None:
        """Get the most recent performance metrics.

        Returns:
            Latest performance metrics
        """
        async with self._lock:
            return self._metrics_store.get_current_metrics()

    async def get_metrics_history(self, limit: int = 100) -> list[PerformanceMetrics]:
        """Get historical performance metrics.

        Args:
            limit: Maximum number of metrics to return

        Returns:
            List of performance metrics
        """
        async with self._lock:
            return self._metrics_store.get_metrics_history(limit)

    async def get_request_metrics(self, limit: int = 100) -> list[RequestMetrics]:
        """Get recent request metrics.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of request metrics
        """
        async with self._lock:
            return self._metrics_store.get_request_metrics(limit)

    async def get_performance_summary(self) -> dict[str, Any]:
        """Get a summary of performance metrics.

        Returns:
            Performance summary
        """
        current_metrics = await self.get_current_metrics()
        if not current_metrics:
            return {}

        async with self._lock:
            # Calculate percentiles for response times
            response_times = sorted(self._metrics_store.get_response_times())
            percentiles = {}

            if response_times:
                percentiles = {
                    "p50": response_times[int(len(response_times) * 0.5)],
                    "p90": response_times[int(len(response_times) * 0.9)],
                    "p95": response_times[int(len(response_times) * 0.95)],
                    "p99": response_times[int(len(response_times) * 0.99)],
                }

            # Endpoint statistics
            endpoint_stats = {}
            for request in self._metrics_store.get_request_metrics(limit=1000):
                endpoint = request.endpoint
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {
                        "count": 0,
                        "total_time": 0.0,
                        "errors": 0,
                    }

                endpoint_stats[endpoint]["count"] += 1
                endpoint_stats[endpoint]["total_time"] += request.response_time
                if request.status_code >= 400:
                    endpoint_stats[endpoint]["errors"] += 1

            # Calculate average response times per endpoint
            for stats in endpoint_stats.values():
                if stats["count"] > 0:
                    stats["avg_response_time"] = stats["total_time"] / stats["count"]
                    stats["error_rate"] = stats["errors"] / stats["count"]

        return {
            "current_metrics": current_metrics.model_dump(),
            "response_time_percentiles": percentiles,
            "endpoint_statistics": endpoint_stats,
            "total_requests": self._metrics_store.get_request_count(),
            "total_errors": self._metrics_store.get_error_count(),
            "active_requests": len(self._active_requests),
        }


# Global performance monitor instance
# Rationale: Using a global instance for the performance monitor simplifies access
# throughout the application and ensures a single, consistent state for monitoring
# metrics. While 'global' is generally discouraged, it's a common and acceptable pattern
# for managing singletons like this in Python applications.
_performance_monitor: PerformanceMonitor | None = None


async def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance.

    Returns:
        Performance monitor instance
    """
    global _performance_monitor

    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        await _performance_monitor.start_monitoring()

    return _performance_monitor


async def cleanup_performance_monitor() -> None:
    """Clean up the global performance monitor."""
    global _performance_monitor

    if _performance_monitor is not None:
        await _performance_monitor.stop_monitoring()
        _performance_monitor = None
