# GraphRAG API Service - Complete API Documentation

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [REST API Endpoints](#rest-api-endpoints)
- [GraphQL API](#graphql-api)
- [WebSocket Support](#websocket-support)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Security](#security)
- [Monitoring](#monitoring)

## Overview

The GraphRAG API Service provides a comprehensive interface for graph-based retrieval-augmented generation, supporting both REST and GraphQL APIs with enterprise-grade features.

### Base URLs
- **Production**: `https://api.graphrag.example.com`
- **Staging**: `https://staging.graphrag-api.example.com`
- **Local Development**: `http://localhost:8001`

### API Versions
- **Current Version**: v1
- **Supported Versions**: v1
- **Deprecation Policy**: 6-month notice before deprecation

## Getting Started

### Quick Start
```bash
# Using curl
curl -X GET http://localhost:8001/health

# Using httpie
http GET localhost:8001/health

# Using Python requests
import requests
response = requests.get("http://localhost:8001/health")
```

### Authentication Setup
```bash
# Get authentication token
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token in requests
curl -X GET http://localhost:8001/api/workspaces \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Authentication

### JWT Authentication
The API uses JWT (JSON Web Tokens) for authentication.

#### Login Endpoint
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Using the Token
Include the token in the Authorization header:
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### API Key Authentication
For service-to-service communication:
```http
X-API-Key: YOUR_API_KEY
```

## REST API Endpoints

### Health & Monitoring

#### Health Check
```http
GET /health
```
Returns basic health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-02T12:00:00Z",
  "uptime": 3600.5,
  "version": "0.1.0",
  "environment": "production"
}
```

#### Detailed Health
```http
GET /health/detailed
```
Returns comprehensive health information including system metrics.

#### Liveness Probe
```http
GET /health/live
```
Kubernetes liveness probe endpoint.

#### Readiness Probe
```http
GET /health/ready
```
Kubernetes readiness probe endpoint.

#### Metrics (Prometheus Format)
```http
GET /health/metrics
```
Returns Prometheus-compatible metrics.

### Workspace Management

#### List Workspaces
```http
GET /api/workspaces
```

**Query Parameters:**
- `limit` (int): Maximum number of results (default: 10)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
{
  "workspaces": [
    {
      "id": "uuid",
      "name": "My Workspace",
      "description": "Workspace description",
      "status": "active",
      "created_at": "2025-09-02T12:00:00Z",
      "updated_at": "2025-09-02T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### Create Workspace
```http
POST /api/workspaces
Content-Type: application/json

{
  "name": "New Workspace",
  "description": "Description",
  "data_path": "/path/to/data",
  "chunk_size": 1200,
  "max_entities": 1000
}
```

#### Get Workspace
```http
GET /api/workspaces/{workspace_id}
```

#### Update Workspace
```http
PUT /api/workspaces/{workspace_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

#### Delete Workspace
```http
DELETE /api/workspaces/{workspace_id}?remove_files=false
```

### GraphRAG Operations

#### Query
```http
POST /api/query
Content-Type: application/json

{
  "workspace_id": "uuid",
  "query": "What is the main topic?",
  "query_type": "global",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

**Response:**
```json
{
  "response": "The main topic is...",
  "sources": [
    {
      "document": "doc1.txt",
      "relevance": 0.95
    }
  ],
  "metadata": {
    "processing_time": 1.23,
    "tokens_used": 450
  }
}
```

#### Index Documents
```http
POST /api/index
Content-Type: application/json

{
  "workspace_id": "uuid",
  "documents": [
    {
      "path": "/path/to/document.txt",
      "content": "Document content...",
      "metadata": {}
    }
  ],
  "options": {
    "chunk_size": 1200,
    "overlap": 100
  }
}
```

#### Get Indexing Status
```http
GET /api/index/status/{job_id}
```

## GraphQL API

### Endpoint
```
POST /graphql
```

### Schema Overview
```graphql
type Query {
  workspace(id: ID!): Workspace
  workspaces(limit: Int, offset: Int): WorkspaceList
  queryGraph(input: QueryInput!): QueryResponse
  systemInfo: SystemInfo
  healthCheck: HealthStatus
}

type Mutation {
  createWorkspace(input: CreateWorkspaceInput!): Workspace
  updateWorkspace(id: ID!, input: UpdateWorkspaceInput!): Workspace
  deleteWorkspace(id: ID!): DeleteResponse
  indexDocuments(input: IndexInput!): IndexResponse
  clearCache(namespace: String): ClearCacheResponse
}

type Subscription {
  indexingProgress(jobId: ID!): IndexingProgress
  queryProgress(queryId: ID!): QueryProgress
}
```

### Example Queries

#### Get Workspace
```graphql
query GetWorkspace($id: ID!) {
  workspace(id: $id) {
    id
    name
    description
    status
    statistics {
      documentCount
      entityCount
      relationshipCount
    }
  }
}
```

#### Create Workspace
```graphql
mutation CreateWorkspace($input: CreateWorkspaceInput!) {
  createWorkspace(input: $input) {
    id
    name
    status
  }
}
```

#### Subscribe to Indexing Progress
```graphql
subscription IndexingProgress($jobId: ID!) {
  indexingProgress(jobId: $jobId) {
    progress
    currentStep
    totalSteps
    message
  }
}
```

## WebSocket Support

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'indexing',
    jobId: 'job-123'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress);
};
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "workspace_id",
      "reason": "Workspace not found"
    },
    "timestamp": "2025-09-02T12:00:00Z",
    "request_id": "req-123"
  }
}
```

### HTTP Status Codes
- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success with no response body
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Codes
- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_ERROR`: Authentication failed
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Internal server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

## Rate Limiting

### Limits
- **Anonymous**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **API Key**: 5000 requests per minute

### Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1693584000
Retry-After: 60
```

### Rate Limit Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

## Security

### Headers
The API includes the following security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`

### CORS
CORS is configured for specific origins:
```http
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 3600
```

### Data Protection
- All data is encrypted in transit (TLS 1.3)
- Sensitive data is encrypted at rest
- PII is automatically redacted from logs
- SQL injection protection enabled
- Input validation on all endpoints

## Monitoring

### Metrics Endpoint
```http
GET /health/metrics
```

### Available Metrics
- `graphrag_up`: Application status (1=up, 0=down)
- `graphrag_uptime_seconds`: Application uptime
- `graphrag_request_duration_seconds`: Request duration histogram
- `graphrag_request_total`: Total requests counter
- `graphrag_active_connections`: Active connection gauge
- `graphrag_memory_usage_bytes`: Memory usage
- `graphrag_cpu_percent`: CPU usage percentage

### Logging
All requests are logged with:
- Request ID
- User ID (if authenticated)
- IP Address
- Response time
- Status code
- Error details (if applicable)

### Tracing
Distributed tracing is available with OpenTelemetry:
```http
X-Trace-ID: 1-5e1b3c4d-6f7a8b9c0d1e2f3a4b5c6d7e
X-Span-ID: a1b2c3d4e5f6g7h8
```

## SDK Examples

### Python
```python
from graphrag_client import GraphRAGClient

client = GraphRAGClient(
    base_url="http://localhost:8001",
    api_key="your-api-key"
)

# Create workspace
workspace = client.create_workspace(
    name="My Workspace",
    description="Test workspace"
)

# Query
response = client.query(
    workspace_id=workspace.id,
    query="What is the main topic?",
    query_type="global"
)
print(response.text)
```

### JavaScript/TypeScript
```typescript
import { GraphRAGClient } from '@graphrag/client';

const client = new GraphRAGClient({
  baseUrl: 'http://localhost:8001',
  apiKey: 'your-api-key'
});

// Create workspace
const workspace = await client.createWorkspace({
  name: 'My Workspace',
  description: 'Test workspace'
});

// Query
const response = await client.query({
  workspaceId: workspace.id,
  query: 'What is the main topic?',
  queryType: 'global'
});
console.log(response.text);
```

## Testing

### Test Endpoints
Use the following endpoints for testing:
- `/api/test/echo`: Echoes back the request
- `/api/test/delay/{seconds}`: Delays response by specified seconds
- `/api/test/error/{code}`: Returns specified error code

### Postman Collection
Import the Postman collection from:
```
/docs/postman/graphrag-api.postman_collection.json
```

### OpenAPI Specification
Access the OpenAPI spec at:
```
http://localhost:8001/openapi.json
```

## Support

- **Documentation**: https://docs.graphrag-api.example.com
- **GitHub Issues**: https://github.com/pierregrothe/graphrag-api/issues
- **Email Support**: support@graphrag-api.example.com
- **Status Page**: https://status.graphrag-api.example.com

---

Last Updated: 2025-09-02
API Version: 1.0.0