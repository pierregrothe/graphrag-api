# GraphRAG API Service - TODO and Fix Plan V3

**Generated Date:** 2025-09-02
**Project Status:** Phase 2 70% Complete - Significant Progress Made

This document reflects the CURRENT state after recent code improvements. Several critical issues from V2 have been addressed.

## 🎉 Recent Improvements Completed

### ✅ FIXED Issues (No longer blockers)

1. **Graph v2 Settings** - `get_settings()` now properly imported and used
2. **JWT Auth Structure** - Now accepts optional DatabaseManager parameter
3. **GraphQL Async** - Properly using `await` for async operations
4. **Connection Pool** - Enhanced with real database support structure

### ⚠️ PARTIALLY FIXED (Needs completion)

1. **JWT Auth Database** - Code exists but DatabaseManager not wired in at startup
2. **Connection Pool** - Still creates mock connections as fallback
3. **Cache Implementation** - Structure exists but returns None

## Phase 0: REMAINING CRITICAL FIXES

### Task 0.1: Wire DatabaseManager to AuthenticationService ⚡

**Priority: CRITICAL - Without this, database auth doesn't work**

```python
# Current in dependencies.py or main.py:
auth_service = AuthenticationService(jwt_config)  # Missing database_manager!

# Should be:
auth_service = AuthenticationService(jwt_config, database_manager)
```

**Location:** Find where AuthenticationService is instantiated

- [ ] Locate AuthenticationService instantiation
- [ ] Pass DatabaseManager instance
- [ ] Verify database connection on startup
- [ ] Test user persistence

### Task 0.2: Complete API Key Admin Check

**Priority: HIGH - Security vulnerability**

- [ ] Implement admin check at line 212 in `api_keys.py`
- [ ] Query user role from database
- [ ] Verify role is ADMIN before allowing revocation

## Phase 1: Complete Database Integration

### Task 1.1: Ensure DatabaseManager is Available Globally

- [ ] Create singleton DatabaseManager instance
- [ ] Initialize in application startup
- [ ] Make available via dependency injection
- [ ] Pass to all services that need it

### Task 1.2: Remove In-Memory Fallbacks

- [ ] Remove conditional logic in JWT auth
- [ ] Make database required, not optional
- [ ] Update error handling for database failures
- [ ] Add database health checks

### Task 1.3: Complete Cache Implementation

**Location:** `connection_pool.py` line 361

```python
# Current:
async def _get_cached_result(...) -> pd.DataFrame | None:
    return None  # No cache implementation

# Should integrate with Redis or use in-memory cache
```

- [ ] Implement actual cache storage
- [ ] Add TTL management
- [ ] Implement cache invalidation
- [ ] Add cache metrics

## Phase 2: Complete v2 Routes Implementation

### Task 2.1: Implement Visualization Endpoint

**Location:** `graph_v2.py` lines 274-279

- [ ] Replace mock response with actual visualization logic
- [ ] Generate real node and edge data
- [ ] Implement layout algorithms
- [ ] Return actual graph structure

### Task 2.2: Implement Export Endpoint

**Location:** `graph_v2.py` lines 302-309

- [ ] Implement actual export functionality
- [ ] Generate real files
- [ ] Support multiple formats (JSON, CSV, GraphML)
- [ ] Implement download URLs

## Phase 3: Testing and Validation

### Task 3.1: Fix Test Infrastructure

- [ ] Update test fixtures for database
- [ ] Mock DatabaseManager properly in tests
- [ ] Fix dependency injection in test setup
- [ ] Ensure all graph endpoint tests pass

### Task 3.2: Add Integration Tests

- [ ] Test database persistence across restarts
- [ ] Test cache hit/miss scenarios
- [ ] Test authentication flow with database
- [ ] Test workspace CRUD with database

## Phase 4: Production Readiness

### Task 4.1: Remove All Mock Code

- [ ] Remove `_create_mock_connection` from connection pool
- [ ] Remove mock responses from all endpoints
- [ ] Remove in-memory user storage option
- [ ] Ensure all operations use real implementations

### Task 4.2: Add Monitoring and Health Checks

- [ ] Add database connection health check
- [ ] Add cache health check
- [ ] Add metrics for all operations
- [ ] Implement proper error tracking

## Updated Priority Matrix

| Priority | Issue | Status | Effort | Impact |
|----------|-------|--------|--------|--------|
| P0 | Wire DatabaseManager to Auth | 🔴 TODO | Low | CRITICAL |
| P0 | API Key Admin Check | 🔴 TODO | Low | HIGH |
| P1 | Remove in-memory fallbacks | 🟡 Partial | Medium | HIGH |
| P1 | Complete cache implementation | 🔴 TODO | Medium | MEDIUM |
| P2 | Visualization endpoint | 🔴 TODO | Medium | LOW |
| P2 | Export endpoint | 🔴 TODO | Medium | LOW |
| ~~P0~~ | ~~Undefined settings~~ | ✅ FIXED | - | - |
| ~~P0~~ | ~~JWT structure~~ | ✅ FIXED | - | - |

## Code Quality Checklist

### Already Fixed ✅

- [x] Settings properly imported in graph_v2.py
- [x] JWT auth accepts DatabaseManager parameter
- [x] GraphQL uses proper async/await
- [x] Connection pool has database support

### Still Needed ❌

- [ ] DatabaseManager wired to AuthenticationService
- [ ] Admin authorization check implemented
- [ ] Cache returns real data
- [ ] Visualization returns real data
- [ ] Export functionality works
- [ ] All tests pass

## Simplified Action Plan

### Day 1 (2-3 hours)

1. Find and fix AuthenticationService instantiation
2. Wire DatabaseManager properly
3. Implement admin check

### Day 2-3 (1-2 days)

1. Complete cache implementation
2. Remove in-memory fallbacks
3. Fix failing tests

### Day 4-5 (2 days)

1. Implement visualization endpoint
2. Implement export endpoint
3. Add integration tests

### Day 6 (1 day)

1. Clean up all mock code
2. Update documentation
3. Final validation

## Total Estimated Time: 5-6 days

Down from 8-13 days in V2, thanks to recent fixes!

## Key Remaining Issues

### CRITICAL (Blocks Production)

1. **DatabaseManager not wired** - Database code exists but not connected
2. **Admin check missing** - Security vulnerability

### IMPORTANT (Affects Functionality)

1. **Cache always misses** - Performance impact
2. **Mock responses** - Features appear broken

### NICE TO HAVE

1. **Visualization** - Currently returns empty
2. **Export** - Currently returns mock URL

## Success Criteria

The project will be production-ready when:

1. ✅ All authentication uses database (not memory)
2. ✅ All tests pass
3. ✅ No mock responses in production endpoints
4. ✅ Cache actually caches data
5. ✅ Admin authorization works
6. ✅ Documentation matches reality

## Notes on Progress

Significant progress has been made since V2:

- Settings import issue completely resolved
- JWT auth has database support (just needs wiring)
- GraphQL properly async
- Connection pool ready for database

The main remaining issue is that the DatabaseManager exists but isn't being passed to the services that need it. This is a simple wiring issue that should take less than an hour to fix once the instantiation point is located.
