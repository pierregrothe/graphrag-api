#!/bin/bash
# Docker entrypoint script for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

set -e

# Default values
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_WORKERS="4"
DEFAULT_ENVIRONMENT="production"

# Environment variables with defaults
export HOST="${HOST:-$DEFAULT_HOST}"
export PORT="${PORT:-$DEFAULT_PORT}"
export WORKERS="${WORKERS:-$DEFAULT_WORKERS}"
export ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Wait for database to be ready
wait_for_db() {
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        log "Waiting for database at $DB_HOST:$DB_PORT..."
        
        timeout=60
        while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
            timeout=$((timeout - 1))
            if [ $timeout -le 0 ]; then
                log "ERROR: Database connection timeout"
                exit 1
            fi
            sleep 1
        done
        
        log "Database is ready"
    fi
}

# Wait for Redis to be ready
wait_for_redis() {
    if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
        log "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
        
        timeout=30
        while ! nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; do
            timeout=$((timeout - 1))
            if [ $timeout -le 0 ]; then
                log "ERROR: Redis connection timeout"
                exit 1
            fi
            sleep 1
        done
        
        log "Redis is ready"
    fi
}

# Validate environment variables
validate_environment() {
    log "Validating environment configuration..."
    
    # Required environment variables for production
    if [ "$ENVIRONMENT" = "production" ]; then
        required_vars=("SECRET_KEY")
        
        for var in "${required_vars[@]}"; do
            if [ -z "${!var}" ]; then
                log "ERROR: Required environment variable $var is not set"
                exit 1
            fi
        done
        
        # Validate SECRET_KEY is not default
        if [ "$SECRET_KEY" = "your-secret-key-here" ]; then
            log "ERROR: SECRET_KEY must be changed from default value in production"
            exit 1
        fi
    fi
    
    log "Environment validation passed"
}

# Create necessary directories
create_directories() {
    log "Creating application directories..."
    
    mkdir -p /app/data /app/workspaces /app/logs
    
    # Set permissions
    chmod 755 /app/data /app/workspaces /app/logs
    
    log "Directories created successfully"
}

# Initialize application
initialize_app() {
    log "Initializing GraphRAG API application..."
    
    # Run any initialization scripts here
    # For example: database migrations, cache warming, etc.
    
    log "Application initialization completed"
}

# Generate Gunicorn configuration
generate_gunicorn_config() {
    log "Generating Gunicorn configuration..."
    
    cat > /app/gunicorn.conf.py << EOF
# Gunicorn configuration for GraphRAG API
import multiprocessing
import os

# Server socket
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 300
keepalive = 2

# Restart workers
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'graphrag-api'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if certificates are provided)
keyfile = os.getenv('SSL_KEYFILE')
certfile = os.getenv('SSL_CERTFILE')

# Worker tuning
worker_tmp_dir = '/dev/shm'
EOF

    log "Gunicorn configuration generated"
}

# Health check function
health_check() {
    log "Performing health check..."
    
    # Check if the application is responding
    if curl -f -s "http://localhost:$PORT/health" > /dev/null; then
        log "Health check passed"
        return 0
    else
        log "Health check failed"
        return 1
    fi
}

# Signal handlers for graceful shutdown
shutdown_handler() {
    log "Received shutdown signal, stopping application..."
    
    # Send SIGTERM to all child processes
    if [ -n "$APP_PID" ]; then
        kill -TERM "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    
    log "Application stopped gracefully"
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Main execution
main() {
    log "Starting GraphRAG API container..."
    log "Environment: $ENVIRONMENT"
    log "Host: $HOST"
    log "Port: $PORT"
    log "Workers: $WORKERS"
    
    # Validate environment
    validate_environment
    
    # Create directories
    create_directories
    
    # Wait for dependencies
    wait_for_db
    wait_for_redis
    
    # Initialize application
    initialize_app
    
    # Generate configuration
    generate_gunicorn_config
    
    # Start the application
    log "Starting GraphRAG API server..."
    
    if [ "$1" = "gunicorn" ]; then
        # Production mode with Gunicorn
        exec gunicorn --config gunicorn.conf.py src.graphrag_api_service.main:app &
        APP_PID=$!
        
        # Wait for application to start
        sleep 5
        
        # Perform initial health check
        if ! health_check; then
            log "ERROR: Application failed to start properly"
            exit 1
        fi
        
        log "GraphRAG API started successfully"
        
        # Wait for the application process
        wait "$APP_PID"
        
    elif [ "$1" = "dev" ]; then
        # Development mode with uvicorn
        log "Starting in development mode..."
        exec uvicorn src.graphrag_api_service.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --log-level debug
            
    elif [ "$1" = "test" ]; then
        # Test mode
        log "Running tests..."
        exec python -m pytest tests/ -v
        
    else
        # Custom command
        log "Executing custom command: $*"
        exec "$@"
    fi
}

# Execute main function with all arguments
main "$@"
