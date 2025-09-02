# GraphRAG API Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the GraphRAG API Service in various environments, optimized for small-scale deployments (1-5 users).

## Table of Contents

1. [Local Development (Windows with Docker)](#local-development)
2. [Google Cloud Run (Serverless Production)](#google-cloud-run)
3. [Configuration](#configuration)
4. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Windows 11 with Docker Desktop
- Git
- Python 3.12+
- Poetry

### Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/graphrag-api.git
cd graphrag-api
```

2. **Set up environment variables:**

Create a `.env` file in the project root:

```env
# Core Settings
APP_NAME=GraphRAG API Service
DEBUG=true
PORT=8001

# LLM Configuration - Ollama for local
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_LLM_MODEL=gemma2:2b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Database - SQLite (lightweight)
DATABASE_TYPE=sqlite
DATABASE_PATH=/app/data/graphrag.db

# Cache - In-memory
CACHE_TYPE=memory
CACHE_TTL=3600

# Security (development)
JWT_SECRET_KEY=dev-secret-key-change-in-production
AUTH_ENABLED=false
```

3. **Start the services:**

```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.simple.yml up -d

# Wait for Ollama models to download (first time only)
docker-compose -f docker-compose.simple.yml logs -f model-loader

# Check health
curl http://localhost:8001/health
```

4. **Access the API:**

- API Documentation: http://localhost:8001/docs
- GraphQL Playground: http://localhost:8001/graphql
- Health Check: http://localhost:8001/health

### Development without Docker

If you prefer to run the API locally without Docker:

```bash
# Install dependencies
poetry install

# Run with SQLite (no external database needed!)
poetry run uvicorn src.graphrag_api_service.main:app --reload --port 8001
```

## Google Cloud Run

### Prerequisites

- Google Cloud Account with billing enabled
- Google Cloud CLI (`gcloud`) installed
- Docker installed locally (for building images)

### Setup Steps

1. **Install Google Cloud CLI:**

Download from: https://cloud.google.com/sdk/docs/install

2. **Authenticate and set project:**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

3. **Enable required APIs:**

```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com
```

### Deployment Methods

#### Method 1: Automated Deployment Script

```bash
# Set your project ID
export PROJECT_ID=your-project-id
export REGION=us-central1

# Run deployment script
chmod +x scripts/deploy-cloudrun.sh
./scripts/deploy-cloudrun.sh
```

#### Method 2: Cloud Build

```bash
# Submit build to Cloud Build
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=_DEPLOY_REGION=us-central1
```

#### Method 3: Manual Deployment

1. **Build and push Docker image:**

```bash
# Build the image
docker build -f Dockerfile.cloudrun -t gcr.io/YOUR_PROJECT_ID/graphrag-api .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/graphrag-api
```

2. **Deploy to Cloud Run:**

```bash
gcloud run deploy graphrag-api \
    --image=gcr.io/YOUR_PROJECT_ID/graphrag-api \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --port=8001 \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=0 \
    --max-instances=5 \
    --set-env-vars=LLM_PROVIDER=google_gemini \
    --set-env-vars=GEMINI_MODEL=gemini-1.5-flash \
    --set-env-vars=DATABASE_TYPE=sqlite \
    --set-env-vars=DATABASE_PATH=/tmp/graphrag.db \
    --set-env-vars=CACHE_TYPE=memory \
    --set-secrets=GOOGLE_API_KEY=graphrag-api-key:latest
```

### Post-Deployment

1. **Get service URL:**

```bash
gcloud run services describe graphrag-api \
    --region=us-central1 \
    --format="value(status.url)"
```

2. **Test the deployment:**

```bash
curl https://your-service-url.run.app/health
```

3. **View logs:**

```bash
gcloud run services logs read graphrag-api --region=us-central1
```

## Configuration

### Environment Variables

| Variable | Description | Default | Environment |
|----------|-------------|---------|-------------|
| `LLM_PROVIDER` | LLM provider (ollama/google_gemini) | ollama | Both |
| `DATABASE_TYPE` | Database type (sqlite/postgresql) | sqlite | Both |
| `DATABASE_PATH` | SQLite database path | data/graphrag.db | Both |
| `CACHE_TYPE` | Cache type (memory/redis) | memory | Both |
| `AUTH_ENABLED` | Enable authentication | false | Development |
| `JWT_SECRET_KEY` | JWT signing key | (required) | Production |
| `GOOGLE_API_KEY` | Google Cloud API key | (required for Gemini) | Production |
| `OLLAMA_BASE_URL` | Ollama server URL | http://localhost:11434 | Development |

### Provider-Specific Settings

#### Ollama (Local Development)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=gemma2:2b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

#### Google Gemini (Production)

```env
LLM_PROVIDER=google_gemini
GOOGLE_API_KEY=your-api-key
GOOGLE_PROJECT_ID=your-project-id
GEMINI_MODEL=gemini-1.5-flash
```

### Security Considerations

1. **Authentication:**
   - Enable `AUTH_ENABLED=true` in production
   - Use strong JWT secrets (minimum 32 characters)
   - Rotate API keys regularly

2. **Network Security:**
   - Use HTTPS in production (automatic with Cloud Run)
   - Configure CORS appropriately
   - Implement rate limiting

3. **Data Security:**
   - SQLite database is stored in `/tmp` on Cloud Run (ephemeral)
   - For persistent data, consider Cloud SQL or Firestore
   - Encrypt sensitive data at rest

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed (Local)

**Error:** "Cannot connect to Ollama at http://localhost:11434"

**Solution:**
```bash
# Check if Ollama is running
docker ps | grep ollama

# Check Ollama logs
docker logs ollama

# Restart Ollama
docker-compose -f docker-compose.simple.yml restart ollama
```

#### 2. Cloud Run Memory Issues

**Error:** "Memory limit exceeded"

**Solution:**
```bash
# Increase memory allocation
gcloud run services update graphrag-api \
    --memory=4Gi \
    --region=us-central1
```

#### 3. SQLite Database Errors

**Error:** "Database is locked"

**Solution:**
- SQLite has limited concurrency
- For production with multiple users, consider PostgreSQL
- Ensure only one process writes to the database

#### 4. Authentication Issues

**Error:** "JWT signature verification failed"

**Solution:**
```bash
# Update JWT secret in Cloud Run
echo -n "new-secret-key" | gcloud secrets versions add graphrag-jwt-secret --data-file=-

# Redeploy service
gcloud run services update graphrag-api --region=us-central1
```

### Performance Optimization

1. **Cold Starts (Cloud Run):**
   - Set minimum instances to 1: `--min-instances=1`
   - Use lighter models for faster startup

2. **Response Times:**
   - Use smaller LLM models (gemma2:2b for dev, gemini-1.5-flash for prod)
   - Enable caching: `CACHE_TYPE=memory`
   - Optimize chunk sizes in workspace configuration

3. **Cost Optimization:**
   - Set `--min-instances=0` to scale to zero
   - Use `--max-instances=5` to limit scaling
   - Monitor usage with Cloud Monitoring

## Monitoring

### Cloud Run Metrics

```bash
# View metrics in Cloud Console
gcloud run services describe graphrag-api \
    --region=us-central1 \
    --format=json | jq '.status'
```

### Application Logs

```bash
# Stream logs
gcloud run services logs tail graphrag-api --region=us-central1

# Filter by severity
gcloud run services logs read graphrag-api \
    --region=us-central1 \
    --filter="severity>=ERROR"
```

### Health Checks

```bash
# Check service health
curl https://your-service-url.run.app/health

# Check metrics endpoint
curl https://your-service-url.run.app/metrics
```

## Backup and Recovery

### SQLite Backup (Local)

```bash
# Backup database
docker exec graphrag-api sqlite3 /app/data/graphrag.db ".backup /app/data/backup.db"

# Copy to host
docker cp graphrag-api:/app/data/backup.db ./backup.db
```

### Cloud Run Considerations

- SQLite on Cloud Run uses `/tmp` (ephemeral storage)
- Data is lost when instance scales to zero
- For persistence, use:
  - Cloud SQL for relational data
  - Firestore for NoSQL data
  - Cloud Storage for file-based data

## Support

For issues or questions:
1. Check the [documentation](../README.md)
2. Review [common issues](#troubleshooting)
3. Open an issue on GitHub
4. Contact the development team

## Next Steps

1. Set up monitoring and alerting
2. Configure custom domain
3. Implement backup strategy
4. Set up CI/CD pipeline
5. Configure autoscaling policies
