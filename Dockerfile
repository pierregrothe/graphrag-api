# Dockerfile for GraphRAG API Production Deployment
# Multi-stage build for optimized production image
# Author: Pierre Grothé
# Creation Date: 2025-08-29

# Build stage
FROM python:3.12-slim as builder

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

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    HOST=0.0.0.0 \
    PORT=8001

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
