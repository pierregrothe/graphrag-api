# GraphRAG API Quickstart Guide

## Zero to GraphRAG in 30 Minutes

This guide will get you from zero to a fully functional GraphRAG API deployment in under 30 minutes, complete with sample data and working examples.

## Prerequisites Checklist

- [ ] **Docker & Docker Compose** installed
- [ ] **Git** installed
- [ ] **8GB+ RAM** available
- [ ] **10GB+ disk space** free
- [ ] **Internet connection** for downloads

## Step 1: Quick Installation (5 minutes)

### **Clone and Start**
```bash
# Clone repository
git clone https://github.com/pierregrothe/graphrag-api.git
cd graphrag-api

# Start all services with one command
docker-compose up -d

# Verify services are running
docker-compose ps
```

### **Expected Output**
```
NAME COMMAND SERVICE STATUS
graphrag-api "python -m uvicorn s…" graphrag-api Up 2 minutes
redis "docker-entrypoint.s…" redis Up 2 minutes
prometheus "/bin/prometheus --c…" prometheus Up 2 minutes
grafana "/run.sh" grafana Up 2 minutes
```

### **Health Check**
```bash
# Test API is running
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":1640995200.0,"uptime":120.5}
```

## Step 2: First API Call (2 minutes)

### **Get JWT Token**
```bash
# Login to get authentication token
curl -X POST "http://localhost:8000/auth/login" \
-H "Content-Type: application/json" \
-d '{
"username": "admin",
"password": "admin123"
}'

# Save the access_token from response
export JWT_TOKEN="your_access_token_here"
```

### **Test API Access**
```bash
# Test authenticated endpoint
curl -X GET "http://localhost:8000/api/entities" \
-H "Authorization: Bearer $JWT_TOKEN"

# Should return empty entities list initially
# {"entities":[],"total_count":0,"has_next_page":false}
```

## Step 3: Load Sample Data (10 minutes)

### **Create Sample Workspace**
```bash
# Create workspace for sample data
curl -X POST "http://localhost:8000/api/workspaces" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"name": "quickstart-demo",
"description": "Quickstart demonstration workspace"
}'

# Save workspace_id from response
export WORKSPACE_ID="your_workspace_id_here"
```

### **Upload Sample Documents**
```bash
# Create sample data directory
mkdir -p data/sample

# Create sample documents
cat > data/sample/ai_overview.txt << 'EOF'
Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines.
Machine Learning is a subset of AI that enables computers to learn without being explicitly programmed.
Deep Learning is a subset of Machine Learning that uses neural networks with multiple layers.
Natural Language Processing (NLP) allows computers to understand and process human language.
Computer Vision enables machines to interpret and understand visual information from the world.
EOF

cat > data/sample/tech_companies.txt << 'EOF'
Google is a technology company that develops AI and machine learning technologies.
OpenAI is an AI research company that created GPT models for natural language processing.
Microsoft has invested heavily in AI and owns GitHub, a platform for software development.
Tesla uses AI for autonomous driving and manufacturing automation.
NVIDIA produces GPUs that are essential for deep learning and AI training.
EOF

cat > data/sample/research_papers.txt << 'EOF'
The Transformer architecture revolutionized natural language processing in 2017.
BERT (Bidirectional Encoder Representations from Transformers) improved language understanding.
GPT (Generative Pre-trained Transformer) models excel at text generation tasks.
ResNet (Residual Networks) solved the vanishing gradient problem in deep learning.
YOLO (You Only Look Once) is a real-time object detection algorithm.
EOF
```

### **Start Indexing**
```bash
# Start indexing the sample documents
curl -X POST "http://localhost:8000/api/indexing/start" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"workspace_id": "'$WORKSPACE_ID'",
"data_path": "./data/sample",
"config": {
"chunk_size": 500,
"overlap": 100,
"enable_community_detection": true
}
}'

# Save job_id from response
export JOB_ID="your_job_id_here"
```

### **Monitor Progress**
```bash
# Check indexing status (repeat until completed)
curl -X GET "http://localhost:8000/api/indexing/status/$JOB_ID" \
-H "Authorization: Bearer $JWT_TOKEN"

# Wait for status: "completed"
```

## Step 4: Explore Your Knowledge Graph (5 minutes)

### **View Extracted Entities**
```bash
# Get all entities
curl -X GET "http://localhost:8000/api/entities?limit=20" \
-H "Authorization: Bearer $JWT_TOKEN"

# Get entities by type
curl -X GET "http://localhost:8000/api/entities?type=TECHNOLOGY&limit=10" \
-H "Authorization: Bearer $JWT_TOKEN"
```

### **Explore Relationships**
```bash
# Get all relationships
curl -X GET "http://localhost:8000/api/relationships?limit=20" \
-H "Authorization: Bearer $JWT_TOKEN"

# Get relationships for specific entity
curl -X GET "http://localhost:8000/api/relationships?source=artificial_intelligence" \
-H "Authorization: Bearer $JWT_TOKEN"
```

### **Semantic Search**
```bash
# Search for AI-related content
curl -X POST "http://localhost:8000/api/graph/query" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"query": "machine learning algorithms",
"limit": 5
}'

# Search for companies
curl -X POST "http://localhost:8000/api/graph/query" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"query": "technology companies AI",
"limit": 5
}'
```

### **Community Detection**
```bash
# Get detected communities
curl -X GET "http://localhost:8000/api/communities" \
-H "Authorization: Bearer $JWT_TOKEN"
```

## Step 5: GraphQL Exploration (5 minutes)

### **Open GraphQL Playground**
1. Open browser to: http://localhost:8000/graphql
2. Add authentication header:
```json
{
"Authorization": "Bearer YOUR_JWT_TOKEN"
}
```

### **Try Sample Queries**

#### **Basic Entity Query**
```graphql
query GetEntities {
entities(first: 10) {
edges {
node {
id
title
type
description
degree
}
}
totalCount
}
}
```

#### **Entity with Relationships**
```graphql
query EntityWithRelationships($entityId: String!) {
entity(id: $entityId) {
id
title
type
description
relationships {
id
source
target
type
weight
}
}
}
```

#### **Semantic Search**
```graphql
query SemanticSearch($query: String!) {
search(query: $query, limit: 5) {
entities {
id
title
type
description
}
relationships {
id
source
target
type
}
score
}
}
```

#### **Community Analysis**
```graphql
query Communities {
communities(first: 5) {
id
title
level
entityIds
relationshipIds
}
}
```

## Step 6: Real-time Subscriptions (3 minutes)

### **WebSocket Connection**
```javascript
// Connect to GraphQL subscriptions
const ws = new WebSocket('ws://localhost:8000/graphql', 'graphql-ws');

// Initialize connection
ws.send(JSON.stringify({
type: 'connection_init',
payload: {
Authorization: 'Bearer YOUR_JWT_TOKEN'
}
}));

// Subscribe to entity updates
ws.send(JSON.stringify({
id: '1',
type: 'start',
payload: {
query: `
subscription {
entityUpdates {
id
title
action
}
}
`
}
}));

// Handle real-time updates
ws.onmessage = function(event) {
const message = JSON.parse(event.data);
if (message.type === 'data') {
console.log('Entity update:', message.payload.data.entityUpdates);
}
};
```

### **Performance Monitoring Subscription**
```javascript
// Subscribe to performance metrics
ws.send(JSON.stringify({
id: '2',
type: 'start',
payload: {
query: `
subscription {
performanceUpdates {
timestamp
cpuUsagePercent
memoryUsageMb
requestsPerSecond
cacheHitRate
}
}
`
}
}));
```

## Step 7: Monitoring Dashboard (2 minutes)

### **Access Monitoring Tools**
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **API Metrics**: http://localhost:8000/metrics

### **Key Metrics to Watch**
```bash
# API performance metrics
curl http://localhost:8000/metrics/performance

# Cache performance
curl http://localhost:8000/metrics/cache

# System health
curl http://localhost:8000/health/detailed
```

## Next Steps: Advanced Features

### **1. API Key Management**
```bash
# Create API key for programmatic access
curl -X POST "http://localhost:8000/auth/api-keys" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"name": "quickstart-api-key",
"permissions": ["read:entities", "read:relationships"],
"rate_limit": 1000
}'

# Use API key instead of JWT
export API_KEY="your_api_key_here"
curl -X GET "http://localhost:8000/api/entities" \
-H "X-API-Key: $API_KEY"
```

### **2. Postman Collection**
```bash
# Import Postman collection for easy testing
# File: postman/GraphRAG-API-Collection.json
# Environment: postman/environments/Local-Development.postman_environment.json
```

### **3. Custom Document Processing**
```python
# Python example for custom document processing
import requests

def process_custom_documents(documents):
for doc in documents:
# Custom preprocessing
processed_content = preprocess_document(doc)

# Upload to GraphRAG
response = requests.post(
"http://localhost:8000/api/documents/upload",
headers={"Authorization": f"Bearer {jwt_token}"},
json={
"workspace_id": workspace_id,
"content": processed_content,
"metadata": doc.metadata
}
)
```

### **4. Advanced Graph Analysis**
```bash
# Centrality analysis
curl -X POST "http://localhost:8000/api/graph/centrality" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"algorithm": "betweenness",
"limit": 20
}'

# Multi-hop queries
curl -X POST "http://localhost:8000/api/graph/multi-hop" \
-H "Authorization: Bearer $JWT_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"start_entity": "artificial_intelligence",
"hops": 3,
"relation_types": ["RELATED_TO", "PART_OF"]
}'
```

## Troubleshooting

### **Common Issues**

#### **Services Not Starting**
```bash
# Check Docker status
docker --version
docker-compose --version

# Check logs
docker-compose logs graphrag-api
docker-compose logs redis

# Restart services
docker-compose down
docker-compose up -d
```

#### **Authentication Errors**
```bash
# Verify login credentials
curl -X POST "http://localhost:8000/auth/login" \
-H "Content-Type: application/json" \
-d '{"username": "admin", "password": "admin123"}' -v

# Check token format
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d
```

#### **Indexing Issues**
```bash
# Check indexing logs
curl -X GET "http://localhost:8000/api/indexing/logs/$JOB_ID" \
-H "Authorization: Bearer $JWT_TOKEN"

# Verify data path
ls -la data/sample/
```

#### **Performance Issues**
```bash
# Check system resources
docker stats

# Monitor API performance
curl http://localhost:8000/metrics/performance

# Check Redis connection
docker exec -it graphrag-redis redis-cli ping
```

### **Getting Help**
- **Documentation**: [docs/](../README.md)
- **GitHub Issues**: https://github.com/pierregrothe/graphrag-api/issues
- **API Reference**: http://localhost:8000/docs
- **GraphQL Schema**: http://localhost:8000/graphql

## Success Checklist

- [ ] Services running (docker-compose ps)
- [ ] API responding (curl health check)
- [ ] Authentication working (JWT token obtained)
- [ ] Sample data indexed (entities and relationships created)
- [ ] Semantic search working (relevant results returned)
- [ ] GraphQL queries working (playground accessible)
- [ ] Monitoring accessible (Grafana dashboard)
- [ ] Real-time subscriptions working (WebSocket connection)

** Congratulations! You now have a fully functional GraphRAG API with sample data and working examples.**

## What's Next?

1. **Explore the API**: Try different queries and endpoints
2. **Add Your Data**: Replace sample data with your documents
3. **Customize Configuration**: Adjust processing parameters
4. **Build Applications**: Use the API in your applications
5. **Scale Up**: Deploy to production with proper configuration
6. **Monitor Performance**: Set up alerts and optimization
7. **Join Community**: Contribute and get support

**Ready to build intelligent knowledge graphs? Start exploring!**
