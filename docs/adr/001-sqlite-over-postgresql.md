# ADR-001: Use SQLite Instead of PostgreSQL

## Status
Accepted

## Date
2025-09-02

## Context
The initial design used PostgreSQL as the primary database with async SQLAlchemy, connection pooling, and Alembic migrations. This was designed for enterprise-scale deployments with high concurrency requirements.

However, the actual deployment requirements are:
- Small scale: 1-5 concurrent users maximum
- Serverless deployment on Google Cloud Run preferred
- Quick local development on Windows with Docker
- Minimal operational complexity
- Fast deployment time (< 5 minutes)

## Decision
Replace PostgreSQL with SQLite as the primary database.

## Consequences

### Positive
- **Zero Configuration**: SQLite requires no database server setup
- **Simplified Deployment**: Single file database, no connection strings
- **Faster Development**: No database container needed for local development
- **Serverless Ready**: Works perfectly with Cloud Run's ephemeral storage for demos
- **Lower Costs**: No database server costs
- **Reduced Complexity**: No connection pooling, async drivers, or migrations needed
- **Portable**: Database can be easily copied/backed up as a single file

### Negative
- **Limited Concurrency**: SQLite has write lock limitations (acceptable for 1-5 users)
- **No Network Access**: Database must be on same machine as application
- **Ephemeral on Cloud Run**: Data lost when instance scales to zero (can use Cloud SQL if needed)
- **Limited Features**: No advanced PostgreSQL features like JSON operators, full-text search

### Mitigation
- Use WAL mode for better concurrency (already implemented)
- For production persistence, can migrate to Cloud SQL later if needed
- Document clear upgrade path to PostgreSQL if scale increases

## Implementation
- Created `SQLiteManager` class in `database/sqlite_models.py`
- Created `SQLiteWorkspaceManager` in `workspace/sqlite_manager.py`
- Updated configuration to use `DATABASE_TYPE=sqlite`
- Removed all PostgreSQL dependencies and Alembic migrations
