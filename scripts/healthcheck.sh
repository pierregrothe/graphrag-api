#!/bin/bash
# Health check script for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

set -e

# Configuration
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"
MAX_RETRIES="${HEALTH_CHECK_RETRIES:-3}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] HEALTHCHECK: $1"
}

# Check if service is responding
check_service() {
    local url="http://${HOST}:${PORT}/health"

    if curl -f -s --max-time "$TIMEOUT" "$url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check detailed health endpoint
check_detailed_health() {
    local url="http://${HOST}:${PORT}/health/detailed"
    local response

    response=$(curl -f -s --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "")

    if [ -n "$response" ]; then
        # Parse JSON response to check status
        local status
        status=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('error')
" 2>/dev/null || echo "error")

        if [ "$status" = "healthy" ]; then
            return 0
        else
            log "Service status: $status"
            return 1
        fi
    else
        return 1
    fi
}

# Check database connectivity
check_database() {
    local url="http://${HOST}:${PORT}/health/database"

    if curl -f -s --max-time "$TIMEOUT" "$url" > /dev/null 2>&1; then
        return 0
    else
        log "Database health check failed"
        return 1
    fi
}

# Check memory usage
check_memory() {
    local url="http://${HOST}:${PORT}/health/memory"
    local response

    response=$(curl -f -s --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "")

    if [ -n "$response" ]; then
        local memory_usage
        memory_usage=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('memory_usage_percent', 0))
except:
    print(100)
" 2>/dev/null || echo "100")

        # Check if memory usage is below 90%
        if [ "$(echo "$memory_usage < 90" | bc -l 2>/dev/null || echo "0")" = "1" ]; then
            return 0
        else
            log "High memory usage: ${memory_usage}%"
            return 1
        fi
    else
        return 1
    fi
}

# Comprehensive health check
comprehensive_check() {
    local checks_passed=0
    local total_checks=4

    # Basic service check
    if check_service; then
        checks_passed=$((checks_passed + 1))
        log "✓ Service responding"
    else
        log "✗ Service not responding"
    fi

    # Detailed health check
    if check_detailed_health; then
        checks_passed=$((checks_passed + 1))
        log "✓ Detailed health check passed"
    else
        log "✗ Detailed health check failed"
    fi

    # Database check
    if check_database; then
        checks_passed=$((checks_passed + 1))
        log "✓ Database connectivity OK"
    else
        log "✗ Database connectivity failed"
    fi

    # Memory check
    if check_memory; then
        checks_passed=$((checks_passed + 1))
        log "✓ Memory usage OK"
    else
        log "✗ Memory usage high"
    fi

    # Determine overall health
    local health_percentage=$((checks_passed * 100 / total_checks))

    if [ $health_percentage -ge 75 ]; then
        log "Overall health: HEALTHY ($checks_passed/$total_checks checks passed)"
        return 0
    else
        log "Overall health: UNHEALTHY ($checks_passed/$total_checks checks passed)"
        return 1
    fi
}

# Main health check with retries
main() {
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        log "Health check attempt $attempt/$MAX_RETRIES"

        if [ "$HEALTH_CHECK_MODE" = "comprehensive" ]; then
            if comprehensive_check; then
                log "Health check PASSED"
                exit 0
            fi
        else
            # Simple health check (default)
            if check_service; then
                log "Health check PASSED"
                exit 0
            fi
        fi

        if [ $attempt -lt $MAX_RETRIES ]; then
            log "Health check failed, retrying in 2 seconds..."
            sleep 2
        fi

        attempt=$((attempt + 1))
    done

    log "Health check FAILED after $MAX_RETRIES attempts"
    exit 1
}

# Execute main function
main "$@"
