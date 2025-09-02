# GraphRAG API Service - Quick Start TODO

## Immediate Actions (Do These First!)

### Step 1: Fix Code Quality (5 minutes)
```bash
# Run these commands in order:
poetry run black src/ tests/
poetry run ruff check --fix src/ tests/
poetry run mypy src/graphrag_api_service --show-error-codes
npm run fix:md
```

### Step 2: Verify Configuration (2 minutes)
Create/update `.env` file with:
```bash
# Core
GRAPHRAG_LLM_PROVIDER=ollama
DEBUG=true
LOG_LEVEL=INFO
PORT=8001

# Database
DATABASE_URL=postgresql://user:password@localhost/graphrag
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600

# Ollama (if using)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=gemma:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Gemini (if using)
GOOGLE_API_KEY=your-api-key
GOOGLE_PROJECT_ID=your-project-id
GEMINI_MODEL=gemini-2.0-flash
```

### Step 3: Start Services (3 minutes)
```bash
# Option A: Docker (Recommended)
docker-compose up -d

# Option B: Local Development
# Terminal 1: Start PostgreSQL and Redis (if not running)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres
docker run -d -p 6379:6379 redis

# Terminal 2: Run migrations
alembic upgrade head

# Terminal 3: Start API
poetry run uvicorn src.graphrag_api_service.main:app --reload --port 8001
```

### Step 4: Verify It's Working (1 minute)
```bash
# Check health
curl http://localhost:8001/health

# Check API docs
open http://localhost:8001/docs

# Check GraphQL playground
open http://localhost:8001/graphql
```

---

## If Things Go Wrong (Troubleshooting)

### Tests Failing?
```bash
# Run only passing tests first
poetry run pytest tests/test_config.py -v
poetry run pytest tests/test_main.py::test_health_endpoint -v

# Skip integration tests if no database
poetry run pytest tests/ -m "not integration" -v
```

### Import Errors?
```bash
# Reinstall dependencies
poetry install
poetry update
```

### Database Connection Failed?
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql postgresql://user:password@localhost/graphrag

# Reset database
alembic downgrade base
alembic upgrade head
```

### Port Already in Use?
```bash
# Change port in .env to 8002, 8003, etc.
PORT=8002

# Or kill the process using port 8001
lsof -i :8001  # Find PID
kill -9 <PID>  # Kill process
```

---

## Quick Wins (Under 30 Minutes)

### 1. Get Basic API Working
- [ ] Fix code formatting with Black
- [ ] Start the API server
- [ ] Test `/health` endpoint
- [ ] Access API documentation at `/docs`

### 2. Fix Critical Tests
- [ ] Update GraphQL endpoint paths in tests
- [ ] Run `pytest tests/test_main.py -v`
- [ ] Fix any simple assertion errors
- [ ] Mark complex tests as skip for now

### 3. Test Core Features
- [ ] Create a workspace via API
- [ ] List workspaces
- [ ] Test GraphQL query
- [ ] Verify caching works

### 4. Quick Documentation Update
- [ ] Update README with correct endpoints
- [ ] Fix any obvious typos
- [ ] Add your test results

---

## One-Hour Sprint Plan

### Minutes 0-10: Environment Setup
```bash
poetry install
poetry run black src/ tests/
poetry run ruff check --fix src/ tests/
```

### Minutes 10-20: Configuration
- Create proper `.env` file
- Verify all services are installed
- Start PostgreSQL and Redis

### Minutes 20-30: Database Setup
```bash
alembic upgrade head
poetry run python -c "from src.graphrag_api_service.database import create_tables; create_tables()"
```

### Minutes 30-40: Start & Test API
```bash
poetry run uvicorn src.graphrag_api_service.main:app --reload
# In another terminal:
curl http://localhost:8001/health
curl http://localhost:8001/docs
```

### Minutes 40-50: Fix Critical Issues
- Fix failing tests (at least 3)
- Update documentation
- Test one complete workflow

### Minutes 50-60: Validate & Document
- Run test suite
- Document what works/doesn't work
- Commit changes

---

## Today's Checklist

### Morning (Fix Critical Issues)
- [ ] Run code formatters
- [ ] Fix import errors
- [ ] Update configuration
- [ ] Start all services
- [ ] Verify API is responding

### Afternoon (Stabilize)
- [ ] Fix 5+ failing tests
- [ ] Test all endpoints manually
- [ ] Update documentation
- [ ] Test with both Ollama and Gemini
- [ ] Run full test suite

### Evening (Polish)
- [ ] Review code quality reports
- [ ] Fix any remaining linting issues
- [ ] Update TODO lists with progress
- [ ] Commit all changes
- [ ] Plan tomorrow's work

---

## Success Metrics

### Minimum Viable (Today)
- [x] API starts without errors
- [x] Health endpoint returns 200
- [x] Can access API documentation
- [ ] 5+ tests passing
- [ ] One complete workflow works

### Good Progress (This Week)
- [ ] All code quality checks pass
- [ ] 50%+ tests passing
- [ ] Both providers working
- [ ] Database operations work
- [ ] Caching operational

### Excellent (This Month)
- [ ] 95%+ tests passing
- [ ] Production Docker image ready
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Deployed to staging

---

## Quick Reference Commands

```bash
# Most Used Commands
poetry run uvicorn src.graphrag_api_service.main:app --reload  # Start API
poetry run pytest tests/ -v  # Run tests
poetry run black src/ tests/  # Format code
poetry run ruff check --fix src/ tests/  # Fix linting

# Database Commands
alembic upgrade head  # Apply migrations
alembic downgrade -1  # Rollback one migration

# Docker Commands
docker-compose up -d  # Start all services
docker-compose logs -f  # View logs
docker-compose down  # Stop all services

# Testing Endpoints
curl http://localhost:8001/health  # Check health
curl http://localhost:8001/docs  # API docs (open in browser)
curl http://localhost:8001/graphql  # GraphQL playground (open in browser)
```

---

## Notes for Quick Success

1. **Don't aim for perfection** - Get it running first
2. **Skip complex issues** - Mark as TODO and move on
3. **Test manually first** - Automated tests can wait
4. **Use Docker** - Avoids local setup issues
5. **Ask for help** - If stuck for >15 minutes

---

Last Updated: 2025-09-02
Time to Basic Functionality: ~30 minutes
Time to Stable System: ~2 hours
