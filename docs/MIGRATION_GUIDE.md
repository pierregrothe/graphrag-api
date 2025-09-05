# Migration Guide: Complex to Simple Architecture

## Overview

This guide helps you migrate from the enterprise PostgreSQL-based architecture to the simplified SQLite-based architecture optimized for small-scale deployments.

## Architecture Changes

### Before (Complex)

- PostgreSQL database with async SQLAlchemy
- Redis for distributed caching
- Kubernetes deployment manifests
- Complex authentication with RBAC
- Multiple service dependencies

### After (Simple)

- SQLite database (zero configuration)
- In-memory caching
- Docker Compose for local, Cloud Run for production
- Simple JWT authentication
- Self-contained deployment

## Migration Steps

### 1. Backup Existing Data

If you have existing data in PostgreSQL:

```bash
# Export workspaces
pg_dump -h localhost -U graphrag -d graphrag -t workspaces > workspaces_backup.sql

# Export queries (optional)
pg_dump -h localhost -U graphrag -d graphrag -t queries > queries_backup.sql
```

### 2. Update Environment Variables

#### Old `.env` (PostgreSQL)

```env
DATABASE_URL=postgresql://user:pass@localhost/graphrag
DATABASE_POOL_SIZE=10
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true
```

#### New `.env` (SQLite)

```env
DATABASE_TYPE=sqlite
DATABASE_PATH=data/graphrag.db
CACHE_TYPE=memory
CACHE_TTL=3600
```

### 3. Update Docker Compose

Replace `docker-compose.yml` with `docker-compose.simple.yml`:

```bash
# Stop old services
docker-compose down

# Start new simplified services
docker-compose -f docker-compose.simple.yml up -d
```

### 4. Update Application Code

#### Database Connection

**Before:**

```python
from src.graphrag_api_service.database.connection import DatabaseManager
from src.graphrag_api_service.workspace.database_manager import DatabaseWorkspaceManager

db_manager = DatabaseManager(settings)
await db_manager.initialize()
workspace_manager = DatabaseWorkspaceManager(settings, db_manager.async_session_factory)
```

**After:**

```python
from src.graphrag_api_service.database.simple_connection import get_simple_database_manager

db_manager = get_simple_database_manager(settings)
workspace_manager = db_manager.get_workspace_manager()
```

#### Cache Usage

**Before:**

```python
from src.graphrag_api_service.cache.redis_cache import RedisCache

cache = RedisCache(redis_url=settings.redis_url)
await cache.set("key", "value", ttl=300)
```

**After:**

```python
from src.graphrag_api_service.cache.simple_cache import get_cache_manager

cache = get_cache_manager()
cache.set("key", "value", ttl=300)
```

### 5. Data Migration Script

If you need to migrate data from PostgreSQL to SQLite:

```python
# scripts/migrate_to_sqlite.py
import json
import sqlite3
import psycopg2
from pathlib import Path

def migrate_workspaces():
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host="localhost",
        database="graphrag",
        user="graphrag",
        password="password"
    )
    pg_cursor = pg_conn.cursor()

    # Connect to SQLite
    sqlite_path = Path("data/graphrag.db")
    sqlite_path.parent.mkdir(exist_ok=True)
    sqlite_conn = sqlite3.connect(sqlite_path)

    # Create SQLite tables
    from src.graphrag_api_service.database.sqlite_models import SQLiteManager
    db = SQLiteManager(str(sqlite_path))

    # Migrate workspaces
    pg_cursor.execute("SELECT * FROM workspaces")
    workspaces = pg_cursor.fetchall()

    for workspace in workspaces:
        db.create_workspace(
            name=workspace['name'],
            description=workspace['description'],
            config=workspace['config']
        )

    print(f"Migrated {len(workspaces)} workspaces")

    pg_conn.close()
    sqlite_conn.close()

if __name__ == "__main__":
    migrate_workspaces()
```

### 6. Update Deployment

#### For Docker Users

```bash
# Use new simplified Dockerfile
docker build -f Dockerfile.cloudrun -t graphrag-api:simple .
docker run -p 8001:8001 graphrag-api:simple
```

#### For Cloud Run Users

```bash
# Deploy with new configuration
gcloud run deploy graphrag-api \
    --source . \
    --region us-central1 \
    --set-env-vars DATABASE_TYPE=sqlite \
    --set-env-vars DATABASE_PATH=/tmp/graphrag.db \
    --set-env-vars CACHE_TYPE=memory
```

### 7. Remove Unused Dependencies

Update `pyproject.toml`:

```toml
# Remove these dependencies
# - asyncpg
# - psycopg2-binary
# - redis
# - alembic
# - kubernetes

# Keep only essential dependencies
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
graphrag = "^0.1.0"
ollama = "^0.1.0"
google-generativeai = "^0.3.0"
```

Run:

```bash
poetry lock --no-update
poetry install
```

## Feature Comparison

| Feature | Complex | Simple |
|---------|---------|--------|
| Database | PostgreSQL | SQLite |
| Cache | Redis | In-memory |
| Deployment | Kubernetes | Docker/Cloud Run |
| Authentication | RBAC + JWT | Simple JWT |
| Scaling | Horizontal | Vertical (1-5 users) |
| Configuration | 50+ env vars | ~10 env vars |
| Dependencies | 40+ packages | ~20 packages |
| Setup Time | 30+ minutes | 5 minutes |
| Resource Usage | 4GB+ RAM | 2GB RAM |

## Benefits of Simple Architecture

1. **Faster Development**: No database setup required
2. **Lower Costs**: Reduced infrastructure needs
3. **Easier Maintenance**: Fewer moving parts
4. **Quick Deployment**: Single container deployment
5. **Serverless Ready**: Works with Cloud Run scale-to-zero

## When to Use Each Architecture

### Use Simple Architecture When

- 1-5 concurrent users
- Quick prototyping needed
- Limited resources
- Serverless deployment preferred
- Minimal ops overhead desired

### Keep Complex Architecture When

- 10+ concurrent users
- High availability required
- Complex RBAC needed
- Distributed caching required
- Horizontal scaling needed

## Rollback Plan

If you need to rollback to the complex architecture:

1. Keep PostgreSQL backup
2. Restore old `.env` file
3. Use original `docker-compose.yml`
4. Redeploy with original Dockerfile

## Common Issues

### SQLite Limitations

**Issue**: "database is locked" errors

**Solution**: SQLite has limited write concurrency. For high-write scenarios, consider:

- Batching writes
- Using WAL mode (already enabled)
- Limiting to 1-2 concurrent writers

### Memory Cache Limitations

**Issue**: Cache lost on restart

**Solution**: This is expected behavior. For persistent cache:

- Increase cache TTL
- Implement cache warming on startup
- Store critical data in SQLite

### Cloud Run Limitations

**Issue**: SQLite data lost when scaling to zero

**Solution**:

- Use Cloud SQL for persistent data
- Or accept ephemeral nature for demo/dev
- Or set minimum instances to 1

## Support

For migration assistance:

1. Check [Deployment Guide](DEPLOYMENT_GUIDE.md)
2. Review [README-SIMPLE.md](../README-SIMPLE.md)
3. Open GitHub issue for specific problems
