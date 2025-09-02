# ADR-002: Use In-Memory Cache Instead of Redis

## Status
Accepted

## Date
2025-09-02

## Context
The original architecture included Redis for distributed caching, session management, and rate limiting across multiple application instances.

Given the revised requirements:
- Single instance deployment (Cloud Run or single Docker container)
- 1-5 concurrent users
- Serverless architecture preference
- Minimal infrastructure complexity

## Decision
Use in-memory caching instead of Redis.

## Consequences

### Positive
- **No External Dependencies**: No Redis server to manage
- **Zero Configuration**: Works out of the box
- **Lower Latency**: No network overhead for cache operations
- **Cost Savings**: No Redis instance costs
- **Simplified Deployment**: One less service to deploy and monitor
- **Perfect for Serverless**: No persistent connections to manage

### Negative
- **Cache Lost on Restart**: Cache is not persistent
- **No Distributed Cache**: Cannot share cache between instances
- **Limited Cache Size**: Constrained by application memory
- **No Advanced Features**: No Redis pub/sub, sorted sets, etc.

### Mitigation
- Implement cache warming on startup for critical data
- Use longer TTLs for stable data
- Store critical data in SQLite instead of cache
- Document Redis as an optional upgrade path

## Implementation
- Created `SimpleMemoryCache` class with TTL support
- Implemented cache statistics and cleanup
- Made Redis optional via `CACHE_TYPE` configuration
- Defaulted to memory cache for all deployments
