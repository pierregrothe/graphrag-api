# ADR-005: Simplified Architecture for Small-Scale Deployment

## Status

Accepted

## Date

2025-09-02

## Context

The original architecture was designed for enterprise-scale deployment with:

- Complex async patterns
- Multiple external services (PostgreSQL, Redis, etc.)
- Kubernetes orchestration
- Comprehensive monitoring and observability
- RBAC and advanced security features

The actual requirements are much simpler:

- 1-5 concurrent users
- Quick deployment (< 5 minutes)
- Minimal configuration
- Low operational overhead
- Cost optimization

## Decision

Adopt a radically simplified architecture optimized for small-scale deployment.

## Consequences

### Positive

- **Faster Time to Market**: Deploy in minutes, not hours
- **Lower Total Cost**: Minimal infrastructure requirements
- **Easier Maintenance**: Fewer components to monitor and update
- **Better Developer Experience**: Simple local development setup
- **Reduced Complexity**: Easier to understand and modify
- **Self-Contained**: All dependencies included or optional

### Negative

- **Limited Scalability**: Not suitable for > 10 concurrent users
- **Fewer Features**: Removed advanced monitoring, RBAC, etc.
- **Less Resilient**: Single points of failure
- **Migration Required**: Need to migrate if scaling up

### Mitigation

- Document clear scaling path
- Keep provider abstractions for easy extension
- Maintain clean architecture for future growth
- Create migration guides for moving to enterprise setup

## Implementation Changes

### Removed

- PostgreSQL database server
- Redis cache server
- Kubernetes deployment
- Alembic migrations
- Complex authentication/RBAC
- Distributed tracing
- Prometheus metrics export

### Simplified

- SQLite for database (single file)
- In-memory cache
- Docker Compose for local dev
- Cloud Run for production
- Simple JWT authentication
- Basic logging
- Health check endpoints

### Retained

- Clean architecture patterns
- Provider abstraction
- Workspace management
- GraphRAG integration
- API documentation
- Testing framework
