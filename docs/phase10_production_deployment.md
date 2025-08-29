# Phase 10: Production Deployment Guide

## Overview

Phase 10 delivers a production-ready GraphRAG API with comprehensive performance optimizations, security framework, and deployment infrastructure. This guide covers all aspects of deploying and managing the GraphRAG API in production environments.

## Key Features Implemented

### Performance & Scalability

- **Connection Pooling**: Efficient database connection management with configurable pool sizes
- **Advanced Caching**: Multi-level caching with TTL, LRU eviction, and compression
- **Response Compression**: Automatic gzip/deflate compression for large responses
- **Memory Optimization**: DataFrame optimization and memory usage monitoring
- **Performance Monitoring**: Real-time metrics collection and alerting
- **Load Testing Framework**: Comprehensive benchmarking and stress testing tools

### Security Framework

- **Rate Limiting**: Configurable request throttling per client IP
- **CORS Configuration**: Flexible cross-origin resource sharing settings
- **Request Validation**: Input sanitization and size limits
- **Audit Logging**: Comprehensive security event tracking
- **Security Headers**: Automatic security header injection

### Deployment Infrastructure

- **Docker Support**: Multi-stage builds with optimized production images
- **Configuration Management**: Environment-based configuration with validation
- **Health Monitoring**: Detailed health checks for all components
- **Nginx Integration**: Production-ready reverse proxy configuration
- **Docker Compose**: Complete orchestration setup

## Performance Optimizations

### Connection Pooling

```python
# Configuration
pool_config = ConnectionPoolConfig(
max_connections=10,
min_connections=2,
connection_timeout=30.0,
idle_timeout=300.0
)

# Usage
async with connection_pool.get_connection() as conn:
result = await connection_pool.execute_query(
query_type="entities",
data_path="entities.parquet",
use_cache=True
)
```

### Caching System

```python
# Cache configuration
cache_config = CacheConfig(
max_memory_mb=512,
default_ttl=3600,
max_entries=1000,
compression_enabled=True
)

# Cache operations
await cache_manager.set("entities", "key1", data, ttl=1800)
result = await cache_manager.get("entities", "key1")
```

### Memory Optimization

```python
# Optimize DataFrames
optimized_df = memory_optimizer.optimize_dataframe(df)

# Process large datasets in chunks
result = memory_optimizer.process_large_dataset(
large_df,
processor_func,
chunk_size=10000
)
```

## Security Configuration

### Rate Limiting

```python
security_config = SecurityConfig(
rate_limiting_enabled=True,
requests_per_minute=100,
burst_limit=20,
max_request_size_mb=10
)
```

### CORS Settings

```python
cors_config = {
"allowed_origins": ["https://yourdomain.com"],
"allowed_methods": ["GET", "POST", "PUT", "DELETE"],
"allowed_headers": ["*"],
"allow_credentials": False
}
```

## Docker Deployment

### Building the Image

```bash
# Build production image
docker build -t graphrag-api:latest .

# Build with specific tag
docker build -t graphrag-api:v1.0.0 .
```

### Running with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f graphrag-api

# Scale the API
docker-compose up -d --scale graphrag-api=3
```

### Environment Variables

```bash
# Required
ENVIRONMENT=production
SECRET_KEY=your-secure-secret-key
DB_PASSWORD=your-database-password

# Optional
HOST=0.0.0.0
PORT=8000
DEBUG=false
DATA_PATH=/app/data
WORKSPACE_PATH=/app/workspaces
```

## Monitoring & Observability

### Health Endpoints

- `GET /health` - Basic health check
- `GET /health/detailed` - Component-level health status
- `GET /health/database` - Database connectivity check
- `GET /health/memory` - Memory usage status

### Performance Metrics

- `GET /metrics/performance` - System performance metrics
- `GET /metrics/cache` - Cache performance statistics
- `GET /metrics/security` - Security audit summary

### Example Health Check Response

```json
{
"status": "healthy",
"timestamp": 1640995200.0,
"components": {
"performance_monitor": {
"status": "healthy",
"metrics": {
"cpu_usage_percent": 45.2,
"memory_usage_percent": 67.8,
"active_connections": 5
}
},
"cache_manager": {
"status": "healthy",
"metrics": {
"hit_rate": 0.85,
"memory_usage_mb": 128.5
}
}
}
}
```

## Configuration Management

### Production Configuration

```python
# deployment/config.py
settings = DeploymentSettings(
environment="production",
debug=False,
host="0.0.0.0",
port=8000,

# Database
database=DatabaseConfig(
host="prod-db-host",
port=5432,
pool_size=20
),

# Security
security=SecurityConfig(
cors_origins=["https://yourdomain.com"],
rate_limit_per_minute=200
),

# Performance
performance=PerformanceConfig(
max_workers=8,
max_memory_usage_percent=80.0,
cache_size_mb=1024
)
)
```

### Environment-Specific Settings

```bash
# Development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

## Load Testing

### Running Load Tests

```python
from src.graphrag_api_service.performance.load_testing import BenchmarkSuite, LoadTestConfig

# Configure load test
config = LoadTestConfig(
base_url="http://localhost:8000",
concurrent_users=50,
test_duration_seconds=300,
ramp_up_seconds=30
)

# Run benchmark
suite = BenchmarkSuite(config)
results = await suite.run_load_test()

# Generate report
report = suite.generate_report(results)
print(report)
```

### Custom Test Scenarios

```python
# Add custom scenario
custom_scenario = TestScenario(
name="custom_query",
method="POST",
endpoint="/api/graph/query",
payload={"query": "test query"},
weight=0.3
)

suite.add_scenario(custom_scenario)
```

## Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] SSL certificates installed
- [ ] Security settings reviewed
- [ ] Performance limits configured
- [ ] Monitoring alerts set up

### Production Deployment

- [ ] Docker images built and tagged
- [ ] Database migrations applied
- [ ] Load balancer configured
- [ ] Health checks enabled
- [ ] Logging configured
- [ ] Backup procedures in place

### Post-Deployment

- [ ] Health endpoints responding
- [ ] Performance metrics collected
- [ ] Security logs monitored
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] Team training completed

## Performance Benchmarks

### Typical Performance Metrics

- **Response Time**: P95 < 500ms for standard queries
- **Throughput**: 1000+ requests/second with proper caching
- **Memory Usage**: < 80% of allocated memory
- **Cache Hit Rate**: > 85% for frequently accessed data
- **Error Rate**: < 0.1% under normal load

### Scaling Recommendations

- **Small Deployment**: 2-4 workers, 512MB cache
- **Medium Deployment**: 4-8 workers, 1GB cache
- **Large Deployment**: 8-16 workers, 2GB+ cache

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Increase cache limits or enable compression
2. **Slow Response Times**: Check database connections and cache hit rates
3. **Rate Limiting**: Adjust limits or implement API key authentication
4. **Connection Errors**: Verify database connectivity and pool settings

### Debug Commands

```bash
# Check container logs
docker logs graphrag-api

# Monitor resource usage
docker stats graphrag-api

# Test health endpoints
curl http://localhost:8000/health/detailed

# Check performance metrics
curl http://localhost:8000/metrics/performance
```

## Future Enhancements

### Planned Security Features

- JWT Authentication System
- API Key Management
- Role-Based Access Control (RBAC)
- OAuth2/OpenID Connect Integration
- Advanced Rate Limiting with Quotas

### Performance Improvements

- Redis Integration for Distributed Caching
- Database Query Optimization
- CDN Integration for Static Assets
- Advanced Load Balancing Strategies

## Additional Resources

- [Docker Documentation](./docker_deployment.md)
- [Security Best Practices](./security_guide.md)
- [Performance Tuning Guide](./performance_tuning.md)
- [Monitoring Setup](./monitoring_setup.md)

---

**Phase 10 Status**: **COMPLETED**

- Performance optimizations implemented
- Security framework established
- Production deployment ready
- Comprehensive documentation provided
