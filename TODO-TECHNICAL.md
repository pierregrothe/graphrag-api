# GraphRAG API Service - Technical TODO List

## Code Quality Issues (Immediate Fix Required)

### Black Formatting Issues
```bash
# Run to auto-fix all formatting issues:
poetry run black src/ tests/
```

**Files needing formatting:**
- All Python files in src/ and tests/ directories
- Approximately 50+ files with formatting inconsistencies

### Ruff Linting Issues (125 total)

#### Import Organization (I001)
**Files affected:** Multiple files across the project
**Fix:** Reorganize imports - stdlib first, third-party second, local last
```python
# Correct order:
import os  # stdlib
import pytest  # third-party
from src.graphrag_api_service.config import Settings  # local
```

#### Unused Imports (F401)
**Files with unused imports:**
- `src/graphrag_api_service/api/graphql/schema.py`
- `src/graphrag_api_service/api/graphql/resolvers.py`
- `src/graphrag_api_service/core/security.py`
- `tests/test_graphql.py`

#### Line Length (E501)
**Files with long lines:**
- Various files with lines exceeding 100 characters
- Use Black to auto-fix

### MyPy Type Checking Issues

#### Missing Type Hints
**Priority files:**
```python
# Add type hints to these modules:
src/graphrag_api_service/api/graphql/resolvers.py
src/graphrag_api_service/core/cache.py
src/graphrag_api_service/services/analytics.py
```

#### Type Mismatches
**Common issues:**
1. Return type annotations not matching actual returns
2. Optional types not properly annotated
3. Generic types missing parameters

**Example fixes:**
```python
# Before:
def get_workspace(workspace_id: str):
    return workspace or None

# After:
def get_workspace(workspace_id: str) -> Optional[Workspace]:
    return workspace or None
```

---

## Test Failures (6 Critical)

### GraphQL Endpoint Tests
**File:** `tests/test_graphql.py`
**Issue:** Endpoint routing mismatch

**Current (Failing):**
```python
response = client.post("/api/graphql", json={"query": query})
```

**Should be:**
```python
response = client.post("/graphql", json={"query": query})
```

### Workspace API Tests
**File:** `tests/test_workspace_api.py`
**Issues:**
1. Missing database session fixtures
2. Incorrect endpoint paths
3. Response format mismatches

**Fixes needed:**
```python
# Add proper fixtures
@pytest.fixture
def db_session():
    # Create test database session
    pass

# Update endpoint paths
# From: /api/workspaces
# To: /workspaces (or verify actual implementation)
```

### Provider Tests
**File:** `tests/test_providers.py`
**Issues:**
1. Mock configuration not matching actual provider interface
2. Missing environment variable mocks

---

## Database & Migration Issues

### Alembic Migrations
**Location:** `alembic/versions/`
**Status:** Migrations exist but may not be up-to-date

**Required actions:**
```bash
# Check current migration status
alembic current

# Generate new migration if needed
alembic revision --autogenerate -m "Update schema"

# Apply migrations
alembic upgrade head
```

### SQLAlchemy Models
**Issues to fix:**
1. Relationship definitions may have circular dependencies
2. Index definitions might be missing
3. Cascade delete rules need verification

**Priority models:**
- `Workspace` model relationships
- `Query` model indexes for performance
- `User` model authentication fields

---

## Configuration Issues

### Environment Variables
**File:** `.env.example`
**Missing or incorrect:**
```bash
# Add these missing variables:
DATABASE_URL=postgresql://user:pass@localhost/graphrag
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600
```

### Settings Validation
**File:** `src/graphrag_api_service/config.py`
**Issues:**
1. Some settings have incorrect validators
2. Default values might not work in all environments
3. Settings inheritance chain needs review

---

## API Endpoint Issues

### REST API
**Incorrect routes found:**
1. `/api/query` should validate input format
2. `/api/index` missing progress tracking
3. `/api/status` returning incomplete information

### GraphQL API
**Schema issues:**
1. Resolver functions not all async
2. Missing error handling in resolvers
3. Pagination not properly implemented

**Required fixes:**
```python
# Make resolvers async
@strawberry.field
async def get_workspace(self, workspace_id: str) -> Workspace:
    # Implementation
    pass

# Add proper pagination
@strawberry.field
async def list_workspaces(
    self,
    limit: int = 10,
    offset: int = 0
) -> List[Workspace]:
    # Implementation
    pass
```

---

## Security Vulnerabilities

### Critical
1. **SQL Injection Risk:** Raw SQL queries in analytics module
2. **JWT Secret:** Hardcoded in some test files
3. **CORS:** Too permissive in current configuration

### Important
1. **Rate Limiting:** Not implemented for all endpoints
2. **Input Validation:** Missing for some GraphQL mutations
3. **File Upload:** No size or type restrictions

**Fixes:**
```python
# Use parameterized queries
# Before:
query = f"SELECT * FROM users WHERE id = {user_id}"

# After:
query = select(User).where(User.id == user_id)

# Implement rate limiting
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.get("/api/query")
@limiter.limit("10/minute")
async def query_endpoint():
    pass
```

---

## Performance Issues

### Database Queries
**N+1 Query Problems:**
- Workspace listings with related entities
- Query history with user information

**Fix with eager loading:**
```python
# Add joinedload for relationships
workspaces = db.query(Workspace)\
    .options(joinedload(Workspace.queries))\
    .all()
```

### Caching Implementation
**Issues:**
1. Cache keys not properly namespaced
2. TTL values too high/low
3. Cache invalidation missing

**Improvements needed:**
```python
# Better cache key structure
cache_key = f"graphrag:workspace:{workspace_id}:v1"

# Implement cache invalidation
async def invalidate_workspace_cache(workspace_id: str):
    await redis.delete(f"graphrag:workspace:{workspace_id}:*")
```

---

## Docker & Deployment Issues

### Dockerfile
**Issues:**
1. Multi-stage build not optimized
2. Poetry installation could be cached better
3. Health check not properly configured

**Optimizations:**
```dockerfile
# Better layer caching
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

# Then copy source
COPY src/ ./src/
```

### Docker Compose
**Issues:**
1. Service dependencies not properly ordered
2. Volume mounts might conflict
3. Network configuration needs review

---

## Documentation Gaps

### Missing Documentation
1. API endpoint request/response examples
2. Authentication flow diagram
3. Deployment guide for production
4. Troubleshooting guide
5. Performance tuning guide

### Incorrect Documentation
1. README GraphQL endpoint URLs
2. Environment variable descriptions
3. Test running instructions
4. Docker deployment steps

---

## Monitoring & Logging Gaps

### Logging Issues
1. Inconsistent log levels
2. Missing correlation IDs
3. Sensitive data in logs

### Monitoring Gaps
1. No health check endpoint details
2. Missing metrics collection
3. No distributed tracing setup

---

## Priority Fix Order

### Day 1 (Stabilization)
1. Run Black formatter
2. Fix critical test failures
3. Update .env.example
4. Fix GraphQL endpoint routing

### Day 2 (Quality)
1. Fix Ruff linting errors
2. Add missing type hints
3. Update documentation
4. Fix security vulnerabilities

### Day 3 (Optimization)
1. Optimize database queries
2. Implement proper caching
3. Add monitoring
4. Performance testing

### Day 4 (Production Prep)
1. Docker optimization
2. Add deployment scripts
3. Security audit
4. Load testing

---

## Testing Strategy

### Unit Tests
- Cover all business logic
- Mock external dependencies
- Test error conditions

### Integration Tests
- Test database operations
- Test cache operations
- Test external API calls

### End-to-End Tests
- Test complete workflows
- Test authentication flow
- Test GraphQL subscriptions

### Performance Tests
- Load testing with Locust
- Database query profiling
- Memory leak detection

---

## Commands for Fixes

```bash
# Full quality fix pipeline
poetry run black src/ tests/ && \
poetry run ruff check --fix src/ tests/ && \
poetry run mypy src/graphrag_api_service --show-error-codes && \
poetry run pytest tests/ -v

# Check what needs fixing
poetry run ruff check src/ tests/ --statistics
poetry run mypy src/graphrag_api_service --show-error-codes

# Run specific test categories
poetry run pytest tests/ -m "not integration" -v  # Skip integration tests
poetry run pytest tests/test_graphql.py -v  # Run only GraphQL tests

# Database management
alembic upgrade head  # Apply migrations
alembic downgrade -1  # Rollback one migration
alembic history  # Show migration history

# Docker operations
docker-compose up -d --build  # Rebuild and start
docker-compose logs -f api  # Follow API logs
docker-compose exec api bash  # Shell into container
```

---

Last Updated: 2025-09-02
Technical Debt Level: MEDIUM
Estimated Fix Time: 2-3 days for critical issues
