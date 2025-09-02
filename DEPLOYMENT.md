# GraphRAG API - Production Deployment Guide

## Overview

This guide covers production deployment of the GraphRAG API with PostgreSQL database integration, Redis caching, and comprehensive monitoring.

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+ with pgvector extension
- Redis 7+ for caching
- SSL certificates for HTTPS
- Load balancer (nginx/traefik)

## Production Environment Setup

### 1. Database Configuration

#### PostgreSQL with pgvector

```bash
# Install PostgreSQL with pgvector extension
docker run --name graphrag-postgres-prod \
  -e POSTGRES_DB=graphrag_prod \
  -e POSTGRES_USER=graphrag_user \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  -d postgres:15

# Install pgvector extension
docker exec -it graphrag-postgres-prod psql -U graphrag_user -d graphrag_prod -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Database Migration

```bash
# Set production database URL
export DATABASE_URL="postgresql://graphrag_user:${POSTGRES_PASSWORD}@postgres:5432/graphrag_prod"

# Run migrations
python -m alembic upgrade head

# Verify database setup
python -c "
from src.graphrag_api_service.database.manager import DatabaseManager
import asyncio
async def test():
    db = DatabaseManager('${DATABASE_URL}')
    await db.initialize()
    print('✅ Database connection successful')
asyncio.run(test())
"
```

### 2. Redis Cluster Setup

```bash
# Redis Cluster for distributed caching
docker run --name redis-cluster-prod \
  -v redis_data:/data \
  -p 6379:6379 \
  -d redis:7-alpine redis-server --appendonly yes

# Configure Redis for production
echo "maxmemory 2gb" >> redis.conf
echo "maxmemory-policy allkeys-lru" >> redis.conf
```

### 3. Environment Configuration

Create production `.env` file:

```env
# =============================================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# =============================================================================

# Server Configuration
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://graphrag_user:${POSTGRES_PASSWORD}@postgres:5432/graphrag_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=10
REDIS_TIMEOUT=5

# Security Configuration
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
API_KEY_EXPIRATION_DAYS=365

# LLM Provider Configuration
OLLAMA_BASE_URL=http://ollama:11434
GOOGLE_GEMINI_API_KEY=${GOOGLE_GEMINI_API_KEY}
GOOGLE_GEMINI_PROJECT_ID=${GOOGLE_GEMINI_PROJECT_ID}

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Performance Configuration
CACHE_TTL=3600
CONNECTION_POOL_SIZE=20
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300
```

### 4. Docker Production Deployment

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  graphrag-api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://graphrag_user:${POSTGRES_PASSWORD}@postgres:5432/graphrag_prod
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=graphrag_prod
      - POSTGRES_USER=graphrag_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - graphrag-api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 5. Load Balancer Configuration

#### Nginx Configuration

```nginx
# nginx.conf
upstream graphrag_api {
    server graphrag-api:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/certs/your-domain.key;

    location / {
        proxy_pass http://graphrag_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /health {
        proxy_pass http://graphrag_api/health;
        access_log off;
    }
}
```

### 6. Monitoring Setup

#### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'graphrag-api'
    static_configs:
      - targets: ['graphrag-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 7. Deployment Commands

```bash
# Build and deploy production environment
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
curl -f https://your-domain.com/health
curl -f https://your-domain.com/metrics

# Check logs
docker-compose -f docker-compose.prod.yml logs -f graphrag-api

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale graphrag-api=3
```

### 8. Security Hardening

```bash
# Setup firewall rules
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 5432/tcp  # Block direct database access
ufw deny 6379/tcp  # Block direct Redis access
ufw enable

# Setup SSL certificates (Let's Encrypt)
certbot --nginx -d your-domain.com

# Configure database security
psql -U postgres -c "ALTER USER graphrag_user WITH PASSWORD '${NEW_SECURE_PASSWORD}';"
```

### 9. Backup and Recovery

```bash
# Database backup
pg_dump -h localhost -U graphrag_user graphrag_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Redis backup
redis-cli --rdb backup_redis_$(date +%Y%m%d_%H%M%S).rdb

# Automated backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
pg_dump -h postgres -U graphrag_user graphrag_prod > $BACKUP_DIR/database.sql
redis-cli --rdb $BACKUP_DIR/redis.rdb
tar -czf $BACKUP_DIR/workspace_files.tar.gz /app/workspaces/
EOF
chmod +x backup.sh
```

### 10. Health Checks and Monitoring

```bash
# Health check endpoints
curl https://your-domain.com/health
curl https://your-domain.com/metrics
curl https://your-domain.com/info

# Database health check
curl https://your-domain.com/api/system/health

# Performance monitoring
curl https://your-domain.com/api/system/metrics
```

## Troubleshooting

### Common Production Issues

1. **Database Connection Pool Exhaustion**
   - Increase `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`
   - Monitor connection usage in metrics

2. **Redis Memory Issues**
   - Configure `maxmemory` and `maxmemory-policy`
   - Monitor Redis memory usage

3. **High CPU Usage**
   - Scale horizontally with more API instances
   - Optimize database queries
   - Enable query caching

4. **SSL Certificate Issues**
   - Verify certificate validity and renewal
   - Check nginx configuration
   - Monitor certificate expiration

## Maintenance

### Regular Maintenance Tasks

- **Daily**: Monitor logs and metrics
- **Weekly**: Database performance analysis
- **Monthly**: Security updates and patches
- **Quarterly**: Capacity planning and scaling review

### Update Procedures

```bash
# Rolling update procedure
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps graphrag-api

# Database migration during updates
python -m alembic upgrade head

# Verify update success
curl -f https://your-domain.com/health
```
