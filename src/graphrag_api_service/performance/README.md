# 📊 Performance Module

The performance module provides comprehensive monitoring, optimization, and analytics capabilities for enterprise-grade performance management.

## 📁 Module Structure

```
performance/
├── __init__.py              # Module exports
├── connection_pool.py      # Database connection pooling
├── monitoring.py           # Performance monitoring
└── README.md               # This documentation
```

## 🔧 Core Components

### Performance Monitoring (`monitoring.py`)

```python
from graphrag_api_service.performance.monitoring import PerformanceMonitor

# Initialize performance monitor
monitor = PerformanceMonitor()

# Track request performance
@monitor.track_performance
async def expensive_operation():
    """Track performance of expensive operations."""
    # Expensive computation
    return result

# Get performance metrics
metrics = await monitor.get_metrics()
print(f"Average response time: {metrics['avg_response_time']:.3f}s")
print(f"Request rate: {metrics['requests_per_second']:.1f} req/s")
print(f"Error rate: {metrics['error_rate']:.2%}")
```

### Connection Pooling (`connection_pool.py`)

```python
from graphrag_api_service.performance.connection_pool import get_connection_pool

# Get optimized connection pool
pool = get_connection_pool(
    database_url="sqlite:///./data/graphrag.db",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)

# Use connection from pool
async with pool.get_connection() as conn:
    result = await conn.execute("SELECT * FROM workspaces")
```

## 📈 Monitoring Features

### Real-time Metrics

```python
# System metrics
system_metrics = {
    "cpu_usage": 45.2,
    "memory_usage": 68.5,
    "disk_usage": 23.1,
    "network_io": {"in": 1024, "out": 2048}
}

# Application metrics
app_metrics = {
    "active_connections": 15,
    "request_queue_size": 3,
    "cache_hit_rate": 0.85,
    "database_connections": 8
}

# Performance metrics
perf_metrics = {
    "avg_response_time": 0.125,
    "p95_response_time": 0.450,
    "requests_per_second": 150.5,
    "error_rate": 0.02
}
```

### Health Checks

```python
async def comprehensive_health_check():
    """Perform comprehensive system health check."""
    health_status = {
        "status": "healthy",
        "checks": {
            "database": await check_database_health(),
            "cache": await check_cache_health(),
            "disk_space": await check_disk_space(),
            "memory": await check_memory_usage(),
            "external_services": await check_external_services()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    # Determine overall status
    if any(check["status"] != "healthy" for check in health_status["checks"].values()):
        health_status["status"] = "degraded"

    return health_status
```

## 🚀 Optimization Features

### Query Optimization

```python
# Optimized database queries
@monitor.track_query_performance
async def get_entities_optimized(workspace_id: str, limit: int):
    """Optimized entity retrieval with caching."""
    # Check cache first
    cache_key = f"entities:{workspace_id}:{limit}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result

    # Database query with optimizations
    query = """
        SELECT id, name, type, degree
        FROM entities
        WHERE workspace_id = ?
        ORDER BY degree DESC
        LIMIT ?
    """

    result = await db.fetch_all(query, [workspace_id, limit])

    # Cache result
    await cache.set(cache_key, result, ttl=300)

    return result
```

### Memory Management

```python
import psutil
import gc

class MemoryManager:
    def __init__(self, max_memory_mb: int = 1024):
        self.max_memory_mb = max_memory_mb

    async def check_memory_usage(self):
        """Monitor memory usage and trigger cleanup if needed."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.max_memory_mb:
            # Trigger garbage collection
            gc.collect()

            # Clear caches if still high
            if memory_mb > self.max_memory_mb * 0.9:
                await self.clear_caches()

        return memory_mb

    async def clear_caches(self):
        """Clear application caches to free memory."""
        await cache.clear_expired()
        # Clear other caches as needed
```

## 🔍 Analytics & Reporting

### Performance Analytics

```python
class PerformanceAnalytics:
    def __init__(self):
        self.metrics_history = []

    async def analyze_performance_trends(self, time_window: str = "1h"):
        """Analyze performance trends over time."""
        metrics = await self.get_metrics_history(time_window)

        analysis = {
            "response_time_trend": self.calculate_trend(metrics, "response_time"),
            "throughput_trend": self.calculate_trend(metrics, "requests_per_second"),
            "error_rate_trend": self.calculate_trend(metrics, "error_rate"),
            "bottlenecks": await self.identify_bottlenecks(metrics),
            "recommendations": await self.generate_recommendations(metrics)
        }

        return analysis

    def identify_bottlenecks(self, metrics):
        """Identify performance bottlenecks."""
        bottlenecks = []

        # Check database performance
        if metrics["db_query_time"] > 0.5:
            bottlenecks.append({
                "type": "database",
                "severity": "high",
                "description": "Database queries are slow",
                "recommendation": "Optimize queries or add indexes"
            })

        # Check memory usage
        if metrics["memory_usage"] > 0.8:
            bottlenecks.append({
                "type": "memory",
                "severity": "medium",
                "description": "High memory usage",
                "recommendation": "Increase memory or optimize memory usage"
            })

        return bottlenecks
```

## 🧪 Testing

### Performance Testing

```python
import pytest
import asyncio
import time

@pytest.mark.asyncio
async def test_response_time():
    """Test API response times."""
    start_time = time.time()

    response = await client.get("/api/workspaces")

    duration = time.time() - start_time
    assert duration < 1.0  # Should respond within 1 second
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test performance under concurrent load."""
    async def make_request():
        return await client.get("/api/graph/entities?limit=10")

    # Make 50 concurrent requests
    tasks = [make_request() for _ in range(50)]
    responses = await asyncio.gather(*tasks)

    # All requests should succeed
    assert all(r.status_code == 200 for r in responses)

    # Average response time should be reasonable
    avg_time = sum(r.elapsed.total_seconds() for r in responses) / len(responses)
    assert avg_time < 2.0

def test_memory_usage():
    """Test memory usage stays within bounds."""
    import psutil

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    # Perform memory-intensive operations
    for _ in range(100):
        # Simulate heavy operations
        pass

    final_memory = process.memory_info().rss
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

    # Memory increase should be reasonable
    assert memory_increase < 100  # Less than 100MB increase
```

## 📊 Metrics Collection

### Prometheus Integration

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Number of active connections')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')

class PrometheusMetrics:
    def __init__(self):
        self.setup_metrics()

    def record_request(self, method: str, endpoint: str, duration: float):
        """Record request metrics."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
        REQUEST_DURATION.observe(duration)

    def update_system_metrics(self):
        """Update system metrics."""
        import psutil

        # Memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)

        # Active connections (example)
        ACTIVE_CONNECTIONS.set(self.get_active_connections())

    def get_metrics(self):
        """Get metrics in Prometheus format."""
        return generate_latest()
```

## 🔧 Configuration

### Performance Settings

```bash
# Performance Configuration
PERFORMANCE_MONITORING_ENABLED=true
METRICS_COLLECTION_INTERVAL=60
MAX_MEMORY_USAGE_MB=1024
MAX_CPU_USAGE_PERCENT=80

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Cache Settings
CACHE_MAX_SIZE=1000
CACHE_TTL=300
CACHE_CLEANUP_INTERVAL=600

# Monitoring Endpoints
METRICS_ENDPOINT=/metrics
HEALTH_ENDPOINT=/health
STATUS_ENDPOINT=/status
```

### Advanced Configuration

```python
from graphrag_api_service.performance.monitoring import PerformanceConfig

config = PerformanceConfig(
    # Monitoring settings
    enable_monitoring=True,
    metrics_interval=60,
    retention_days=30,

    # Performance thresholds
    max_response_time=2.0,
    max_memory_usage_mb=1024,
    max_cpu_usage_percent=80,

    # Connection pool settings
    db_pool_size=10,
    db_max_overflow=20,
    db_pool_timeout=30,

    # Cache optimization
    cache_max_size=1000,
    cache_ttl=300,
    enable_compression=True,

    # Alerting
    enable_alerts=True,
    alert_thresholds={
        "response_time": 1.0,
        "error_rate": 0.05,
        "memory_usage": 0.8
    }
)
```

## 🚨 Alerting & Notifications

### Performance Alerts

```python
class PerformanceAlerting:
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.alert_handlers = []

    async def check_thresholds(self, metrics: dict):
        """Check metrics against thresholds and trigger alerts."""
        alerts = []

        # Response time alert
        if metrics["avg_response_time"] > self.config.alert_thresholds["response_time"]:
            alerts.append({
                "type": "response_time",
                "severity": "warning",
                "message": f"High response time: {metrics['avg_response_time']:.3f}s",
                "threshold": self.config.alert_thresholds["response_time"],
                "current_value": metrics["avg_response_time"]
            })

        # Error rate alert
        if metrics["error_rate"] > self.config.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "error_rate",
                "severity": "critical",
                "message": f"High error rate: {metrics['error_rate']:.2%}",
                "threshold": self.config.alert_thresholds["error_rate"],
                "current_value": metrics["error_rate"]
            })

        # Memory usage alert
        if metrics["memory_usage"] > self.config.alert_thresholds["memory_usage"]:
            alerts.append({
                "type": "memory_usage",
                "severity": "warning",
                "message": f"High memory usage: {metrics['memory_usage']:.1%}",
                "threshold": self.config.alert_thresholds["memory_usage"],
                "current_value": metrics["memory_usage"]
            })

        # Send alerts
        for alert in alerts:
            await self.send_alert(alert)

        return alerts

    async def send_alert(self, alert: dict):
        """Send alert to configured handlers."""
        for handler in self.alert_handlers:
            await handler.send_alert(alert)
```

### Alert Handlers

```python
class EmailAlertHandler:
    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config

    async def send_alert(self, alert: dict):
        """Send alert via email."""
        subject = f"GraphRAG API Alert: {alert['type']}"
        body = f"""
        Alert: {alert['message']}
        Severity: {alert['severity']}
        Threshold: {alert['threshold']}
        Current Value: {alert['current_value']}
        Timestamp: {datetime.utcnow().isoformat()}
        """

        await self.send_email(subject, body)

class SlackAlertHandler:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(self, alert: dict):
        """Send alert to Slack."""
        color = "danger" if alert["severity"] == "critical" else "warning"

        payload = {
            "attachments": [{
                "color": color,
                "title": f"GraphRAG API Alert: {alert['type']}",
                "text": alert["message"],
                "fields": [
                    {"title": "Severity", "value": alert["severity"], "short": True},
                    {"title": "Threshold", "value": str(alert["threshold"]), "short": True},
                    {"title": "Current", "value": str(alert["current_value"]), "short": True}
                ],
                "timestamp": int(time.time())
            }]
        }

        await self.send_webhook(payload)
```

## 🔧 Performance Tuning

### Database Optimization

```python
class DatabaseOptimizer:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def optimize_queries(self):
        """Analyze and optimize slow queries."""
        slow_queries = await self.identify_slow_queries()

        for query in slow_queries:
            # Analyze query execution plan
            plan = await self.analyze_query_plan(query)

            # Suggest optimizations
            suggestions = self.suggest_optimizations(plan)

            logger.info(f"Query optimization suggestions for {query['sql']}: {suggestions}")

    async def update_statistics(self):
        """Update database statistics for better query planning."""
        await self.db_manager.execute("ANALYZE")

    def suggest_optimizations(self, plan: dict) -> list[str]:
        """Suggest query optimizations based on execution plan."""
        suggestions = []

        if "table_scan" in plan:
            suggestions.append("Consider adding indexes for frequently queried columns")

        if plan.get("rows_examined", 0) > 1000:
            suggestions.append("Query examines many rows - consider adding WHERE clauses")

        if "temp_table" in plan:
            suggestions.append("Query uses temporary tables - consider query restructuring")

        return suggestions
```

### Cache Optimization

```python
class CacheOptimizer:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager

    async def optimize_cache_strategy(self):
        """Analyze cache performance and optimize strategy."""
        stats = await self.cache_manager.get_stats()

        # Analyze hit rates
        if stats["hit_rate"] < 0.7:
            await self.increase_cache_ttl()

        # Analyze memory usage
        if stats["memory_usage"] > 0.8:
            await self.implement_cache_eviction()

        # Analyze access patterns
        hot_keys = await self.identify_hot_keys()
        await self.optimize_hot_keys(hot_keys)

    async def implement_cache_eviction(self):
        """Implement intelligent cache eviction."""
        # Remove least recently used items
        await self.cache_manager.evict_lru(count=100)

        # Remove expired items
        await self.cache_manager.clear_expired()

    async def optimize_hot_keys(self, hot_keys: list):
        """Optimize frequently accessed keys."""
        for key in hot_keys:
            # Increase TTL for hot keys
            await self.cache_manager.extend_ttl(key, multiplier=2)

            # Pre-warm related data
            await self.pre_warm_related_data(key)
```

## 📈 Capacity Planning

### Resource Forecasting

```python
class CapacityPlanner:
    def __init__(self, metrics_history):
        self.metrics_history = metrics_history

    def forecast_resource_needs(self, days_ahead: int = 30) -> dict:
        """Forecast resource needs based on historical data."""
        # Analyze growth trends
        cpu_trend = self.calculate_growth_trend("cpu_usage")
        memory_trend = self.calculate_growth_trend("memory_usage")
        request_trend = self.calculate_growth_trend("requests_per_second")

        # Project future needs
        forecast = {
            "cpu_usage": {
                "current": self.get_current_average("cpu_usage"),
                "projected": self.project_value("cpu_usage", days_ahead),
                "recommendation": self.get_cpu_recommendation(cpu_trend)
            },
            "memory_usage": {
                "current": self.get_current_average("memory_usage"),
                "projected": self.project_value("memory_usage", days_ahead),
                "recommendation": self.get_memory_recommendation(memory_trend)
            },
            "request_volume": {
                "current": self.get_current_average("requests_per_second"),
                "projected": self.project_value("requests_per_second", days_ahead),
                "recommendation": self.get_scaling_recommendation(request_trend)
            }
        }

        return forecast

    def get_scaling_recommendation(self, trend: float) -> str:
        """Get scaling recommendations based on trends."""
        if trend > 0.1:  # 10% growth
            return "Consider horizontal scaling - add more instances"
        elif trend > 0.05:  # 5% growth
            return "Monitor closely - scaling may be needed soon"
        else:
            return "Current capacity appears sufficient"
```

## 🛠️ Troubleshooting Guide

### Common Performance Issues

1. **High Response Times**

   ```python
   # Diagnosis
   async def diagnose_slow_responses():
       metrics = await monitor.get_detailed_metrics()

       if metrics["db_query_time"] > 0.5:
           return "Database queries are slow - check indexes and query optimization"
       elif metrics["cache_miss_rate"] > 0.5:
           return "High cache miss rate - review caching strategy"
       elif metrics["cpu_usage"] > 0.8:
           return "High CPU usage - consider scaling or optimization"
       else:
           return "Check network latency and external service dependencies"
   ```

2. **Memory Leaks**

   ```python
   # Memory leak detection
   async def detect_memory_leaks():
       baseline = await get_memory_baseline()

       # Monitor over time
       for i in range(10):
           await asyncio.sleep(60)  # Wait 1 minute
           current_memory = await get_current_memory()

           if current_memory > baseline * 1.5:  # 50% increase
               logger.warning(f"Potential memory leak detected: {current_memory}MB")
               await trigger_memory_analysis()
   ```

3. **Database Connection Issues**

   ```python
   # Connection pool monitoring
   async def monitor_connection_pool():
       pool_stats = await db_pool.get_stats()

       if pool_stats["active_connections"] >= pool_stats["pool_size"]:
           logger.warning("Connection pool exhausted")
           await increase_pool_size()

       if pool_stats["wait_time"] > 5.0:
           logger.warning("Long connection wait times")
           await optimize_connection_usage()
   ```

### Performance Debugging

```python
class PerformanceDebugger:
    def __init__(self):
        self.profiler = cProfile.Profile()

    async def profile_request(self, request_handler):
        """Profile a specific request handler."""
        self.profiler.enable()

        try:
            result = await request_handler()
        finally:
            self.profiler.disable()

        # Generate profile report
        stats = pstats.Stats(self.profiler)
        stats.sort_stats('cumulative')

        # Save profile data
        profile_data = self.format_profile_data(stats)
        await self.save_profile_report(profile_data)

        return result

    def format_profile_data(self, stats) -> dict:
        """Format profile data for analysis."""
        # Extract top functions by time
        top_functions = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            top_functions.append({
                "function": f"{func[0]}:{func[1]}({func[2]})",
                "calls": nc,
                "total_time": tt,
                "cumulative_time": ct,
                "per_call": tt / nc if nc > 0 else 0
            })

        # Sort by cumulative time
        top_functions.sort(key=lambda x: x["cumulative_time"], reverse=True)

        return {
            "top_functions": top_functions[:20],
            "total_calls": stats.total_calls,
            "total_time": stats.total_tt
        }
```

## 📋 Best Practices Summary

1. **Monitoring**: Implement comprehensive monitoring from day one
2. **Alerting**: Set up proactive alerts for key metrics
3. **Caching**: Use intelligent caching strategies
4. **Connection Pooling**: Optimize database connection usage
5. **Resource Management**: Monitor and manage system resources
6. **Capacity Planning**: Plan for growth based on trends
7. **Performance Testing**: Regular performance testing and benchmarking
8. **Optimization**: Continuous optimization based on metrics
9. **Documentation**: Document performance characteristics and optimizations
10. **Incident Response**: Have procedures for performance incidents

---

For more information, see the [main documentation](../../../README.md) or other module documentation.
