# Authentication Quick Start Guide

## 🚀 Get Started in 2 Minutes

This guide will get you authenticated and making API calls to GraphRAG in under 2 minutes.

## Option 1: Instant Access (Development)

### Step 1: Copy the Example Environment File

```bash
cp .env.example .env
```

### Step 2: Start the Server

```bash
poetry run uvicorn src.graphrag_api_service.main:app --reload
```

### Step 3: Use the Default Admin API Key

The system comes with a pre-configured admin API key for immediate access:

```bash
# List all workspaces
curl -H "X-API-Key: grag_ak_default_admin_change_this_immediately" \
     http://localhost:8001/api/workspaces

# Create a new workspace
curl -X POST \
     -H "X-API-Key: grag_ak_default_admin_change_this_immediately" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-workspace", "data_path": "/path/to/data"}' \
     http://localhost:8001/api/workspaces
```

**⚠️ IMPORTANT**: Change the default API key before deploying to production!

## Option 2: No Authentication (Local Development Only)

For the simplest local development experience, disable authentication entirely:

### Step 1: Update .env

```env
AUTH_MODE=none
AUTH_ENABLED=false
```

### Step 2: Make Requests Without Authentication

```bash
curl http://localhost:8001/api/workspaces
```

**⚠️ WARNING**: Never use this configuration in production!

## Option 3: Generate Your Own API Key (Recommended)

### Step 1: Keep Default Authentication Enabled

```env
AUTH_MODE=api_key
AUTH_ENABLED=true
DEFAULT_ADMIN_API_KEY=grag_ak_default_admin_change_this_immediately
```

### Step 2: Create a New API Key

```bash
# Using the default admin key to create a new key
curl -X POST \
     -H "X-API-Key: grag_ak_default_admin_change_this_immediately" \
     -H "Content-Type: application/json" \
     -d '{"name": "My Application", "permissions": ["read", "write"]}' \
     http://localhost:8001/api/auth/keys

# Response:
{
  "api_key": "grag_ak_abc123xyz789...",
  "key_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Application",
  "created_at": "2025-01-03T10:00:00Z",
  "expires_at": "2026-01-03T10:00:00Z"
}
```

### Step 3: Use Your New API Key

```bash
curl -H "X-API-Key: grag_ak_abc123xyz789..." \
     http://localhost:8001/api/workspaces
```

## Authentication Methods

### Method 1: Header (Recommended)

```bash
curl -H "X-API-Key: your_api_key_here" \
     http://localhost:8001/api/endpoint
```

### Method 2: Authorization Header

```bash
curl -H "Authorization: Bearer your_api_key_here" \
     http://localhost:8001/api/endpoint
```

### Method 3: Query Parameter (If Enabled)

```bash
curl "http://localhost:8001/api/endpoint?api_key=your_api_key_here"
```

**Note**: Query parameter method must be enabled in .env:
```env
API_KEY_ALLOW_QUERY_PARAM=true
```

## Python Client Example

```python
import requests

# Configure your API key
API_KEY = "grag_ak_default_admin_change_this_immediately"
BASE_URL = "http://localhost:8001"

# Create session with default headers
session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
})

# List workspaces
response = session.get(f"{BASE_URL}/api/workspaces")
workspaces = response.json()
print(f"Found {len(workspaces)} workspaces")

# Create a new workspace
workspace_data = {
    "name": "my-project",
    "description": "My GraphRAG project",
    "data_path": "/path/to/documents",
    "chunk_size": 1500
}
response = session.post(f"{BASE_URL}/api/workspaces", json=workspace_data)
workspace = response.json()
print(f"Created workspace: {workspace['id']}")

# Query the workspace
query_data = {
    "query": "What is GraphRAG?",
    "mode": "global"
}
response = session.post(
    f"{BASE_URL}/api/workspaces/{workspace['id']}/query",
    json=query_data
)
results = response.json()
print(f"Query results: {results}")
```

## JavaScript/TypeScript Example

```typescript
const API_KEY = 'grag_ak_default_admin_change_this_immediately';
const BASE_URL = 'http://localhost:8001';

// Create a reusable fetch wrapper
async function graphragAPI(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  
  return response.json();
}

// List workspaces
const workspaces = await graphragAPI('/api/workspaces');
console.log(`Found ${workspaces.length} workspaces`);

// Create a workspace
const workspace = await graphragAPI('/api/workspaces', {
  method: 'POST',
  body: JSON.stringify({
    name: 'my-project',
    description: 'My GraphRAG project',
    data_path: '/path/to/documents',
    chunk_size: 1500,
  }),
});
console.log(`Created workspace: ${workspace.id}`);

// Query the workspace
const results = await graphragAPI(`/api/workspaces/${workspace.id}/query`, {
  method: 'POST',
  body: JSON.stringify({
    query: 'What is GraphRAG?',
    mode: 'global',
  }),
});
console.log('Query results:', results);
```

## Environment Configuration Reference

### Minimal Configuration (Development)

```env
# Just these 4 lines to get started!
AUTH_MODE=api_key
AUTH_ENABLED=true
DEFAULT_ADMIN_API_KEY=grag_ak_default_admin_change_this_immediately
AUTO_CREATE_ADMIN=true
```

### Recommended Configuration (Staging/Production)

```env
# Authentication settings
AUTH_MODE=api_key
AUTH_ENABLED=true

# Use environment variable for the admin key
DEFAULT_ADMIN_API_KEY=${GRAPHRAG_ADMIN_KEY}

# Don't auto-create admin in production
AUTO_CREATE_ADMIN=false

# API key settings
API_KEY_PREFIX=grag_prod_
API_KEY_EXPIRY_DAYS=90
API_KEY_ALLOW_QUERY_PARAM=false
API_KEY_RATE_LIMIT=60

# Security headers
CORS_ORIGINS=["https://your-domain.com"]
CORS_ALLOW_CREDENTIALS=true
```

## Common Use Cases

### 1. CI/CD Pipeline

```yaml
# GitHub Actions example
env:
  GRAPHRAG_API_KEY: ${{ secrets.GRAPHRAG_API_KEY }}

steps:
  - name: Test GraphRAG API
    run: |
      curl -f -H "X-API-Key: ${GRAPHRAG_API_KEY}" \
           http://your-server:8001/api/health
```

### 2. Docker Deployment

```dockerfile
# Dockerfile
ENV AUTH_MODE=api_key
ENV AUTH_ENABLED=true
ENV DEFAULT_ADMIN_API_KEY=${GRAPHRAG_ADMIN_KEY}
```

```bash
# Run with API key from environment
docker run -e GRAPHRAG_ADMIN_KEY=your_secure_key graphrag-api
```

### 3. Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: graphrag-auth
type: Opaque
data:
  api-key: Z3JhZ19ha19zZWN1cmVfa2V5XzEyMzQ1Ng==  # base64 encoded

---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: graphrag-api
        env:
        - name: DEFAULT_ADMIN_API_KEY
          valueFrom:
            secretKeyRef:
              name: graphrag-auth
              key: api-key
```

## Troubleshooting

### Problem: 401 Unauthorized

**Solution**: Check that:
1. Authentication is enabled in .env
2. API key is correct (check for typos)
3. API key hasn't expired

```bash
# Test your API key
curl -I -H "X-API-Key: your_key_here" http://localhost:8001/api/health
```

### Problem: API Key Not Working

**Solution**: Verify the configuration:

```bash
# Check current auth mode
grep AUTH_MODE .env

# Check if key is enabled
grep AUTH_ENABLED .env

# Check the default key
grep DEFAULT_ADMIN_API_KEY .env
```

### Problem: Can't Generate New Keys

**Solution**: This feature requires the authentication endpoints to be implemented. For now, use the default admin key or environment variables.

## Security Best Practices

### 1. Never Commit API Keys

```bash
# Add to .gitignore
.env
*.key
*_api_key.txt
```

### 2. Use Environment Variables in Production

```bash
# Set via environment
export DEFAULT_ADMIN_API_KEY=$(openssl rand -hex 32)
```

### 3. Rotate Keys Regularly

```bash
# Generate a secure key
openssl rand -hex 32 | sed 's/^/grag_ak_/'
```

### 4. Use HTTPS in Production

```nginx
# Nginx configuration
location /api {
    proxy_pass http://localhost:8001;
    proxy_set_header X-API-Key $http_x_api_key;
}
```

## Next Steps

1. **Change the default API key** before any deployment
2. **Set up proper key management** for production
3. **Enable HTTPS** for secure API key transmission
4. **Configure rate limiting** to prevent abuse
5. **Set up monitoring** for authentication failures

## Need Help?

- Check the [full authentication documentation](./authentication-improvement-plan.md)
- Review the [API reference](./API_REFERENCE.md)
- Open an issue on [GitHub](https://github.com/your-org/graphrag-api)

---

**Remember**: The default API key is for development only. Always use secure, unique keys in production!