# Dockerfile for GraphRAG API Production Deployment
# Multi-stage build for optimized production image
# Author: Pierre Grothé
# Creation Date: 2025-08-29

# Build stage
FROM python:3.12-slim as builder

# Build argument for version (passed from CI/CD)
ARG VERSION=dev

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Poetry
RUN pip install --upgrade pip setuptools wheel && \
    pip install poetry==1.8.5

# Copy dependency files
COPY pyproject.toml poetry.lock /tmp/

# Export requirements from Poetry and install
RUN cd /tmp && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install -r requirements.txt

# Production stage
FROM python:3.12-slim as production

# Build argument for version
ARG VERSION=dev

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production

# Application Configuration
ENV APP_NAME="GraphRAG API Service" \
    APP_VERSION=${VERSION} \
    DEBUG=false \
    HOST=0.0.0.0 \
    PORT=8001

# GraphRAG Configuration
ENV GRAPHRAG_CONFIG_PATH="" \
    GRAPHRAG_DATA_PATH="/app/data"

# LLM Provider Configuration
ENV LLM_PROVIDER="ollama" \
    OLLAMA_BASE_URL="http://localhost:11434" \
    OLLAMA_LLM_MODEL="gemma:4b" \
    OLLAMA_EMBEDDING_MODEL="nomic-embed-text"

# Google Gemini Configuration (optional)
ENV GOOGLE_API_KEY="" \
    GOOGLE_PROJECT_ID="" \
    GOOGLE_LOCATION="us-central1" \
    GEMINI_MODEL="gemini-2.5-flash" \
    GEMINI_EMBEDDING_MODEL="text-embedding-004" \
    GOOGLE_CLOUD_USE_VERTEX_AI=false \
    VERTEX_AI_LOCATION="us-central1"

# Logging Configuration
ENV LOG_LEVEL="INFO" \
    LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Database Configuration
ENV DATABASE_URL="" \
    REDIS_URL=""

# Authentication & Security
ENV AUTH_MODE="api_key" \
    AUTH_ENABLED=true \
    DEFAULT_ADMIN_API_KEY="grag_ak_default_admin_change_this_immediately" \
    DEFAULT_ADMIN_USERNAME="admin" \
    DEFAULT_ADMIN_EMAIL="admin@localhost" \
    DEFAULT_ADMIN_PASSWORD="admin123" \
    AUTO_CREATE_ADMIN=true

# API Key Configuration
ENV API_KEY_PREFIX="grag_ak_" \
    API_KEY_LENGTH=32 \
    API_KEY_EXPIRY_DAYS=365 \
    API_KEY_ALLOW_QUERY_PARAM=false \
    API_KEY_RATE_LIMIT=100

# JWT Configuration (Advanced)
ENV JWT_SECRET_KEY="" \
    JWT_ALGORITHM="HS256" \
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30 \
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=7 \
    JWT_ISSUER="graphrag-api" \
    JWT_AUDIENCE="graphrag-users"

# Performance Settings
ENV CONNECTION_POOL_SIZE=10 \
    CONNECTION_POOL_MAX_OVERFLOW=20 \
    CACHE_TTL=3600 \
    MAX_WORKERS=4

# Monitoring & Observability
ENV ENABLE_METRICS=true \
    ENABLE_TRACING=false \
    PROMETHEUS_PORT=9090

# Rate Limiting
ENV RATE_LIMIT_ENABLED=true \
    RATE_LIMIT_REQUESTS=100 \
    RATE_LIMIT_PERIOD=60

# CORS Settings (JSON format)
ENV CORS_ORIGINS='["http://localhost:3000", "http://localhost:8001"]' \
    CORS_ALLOW_CREDENTIALS=true \
    CORS_ALLOW_METHODS='["GET", "POST", "PUT", "DELETE", "OPTIONS"]' \
    CORS_ALLOW_HEADERS='["*"]'

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r graphrag && useradd -r -g graphrag graphrag

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directories
RUN mkdir -p /app/data /app/workspaces /app/logs && \
    chown -R graphrag:graphrag /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=graphrag:graphrag src/ /app/src/
COPY --chown=graphrag:graphrag pyproject.toml /app/
COPY --chown=graphrag:graphrag README.md /app/

# Install the application
RUN pip install -e .

# Copy startup scripts
COPY --chown=graphrag:graphrag scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
COPY --chown=graphrag:graphrag scripts/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/docker-entrypoint.sh /app/healthcheck.sh

# Switch to non-root user
USER graphrag

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["uvicorn", "src.graphrag_api_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
