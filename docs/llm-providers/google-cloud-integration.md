# Google Cloud AI Integration Guide

## Overview

Google Cloud AI provides enterprise-grade LLM services for GraphRAG API through Vertex AI and Gemini models. This guide covers setup, configuration, and optimization for production deployments with Google's latest AI models.

## Prerequisites

- Google Cloud Platform account
- Billing enabled on your GCP project
- Vertex AI API enabled
- Service account with appropriate permissions

## Setup & Configuration

### 1. Google Cloud Project Setup

#### **Create Project**

```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login and create project
gcloud auth login
gcloud projects create your-graphrag-project --name="GraphRAG API"
gcloud config set project your-graphrag-project

# Enable billing (required for Vertex AI)
gcloud billing accounts list
gcloud billing projects link your-graphrag-project --billing-account=BILLING_ACCOUNT_ID
```

#### **Enable Required APIs**

```bash
# Enable Vertex AI and related APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable ml.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

### 2. Service Account Setup

#### **Create Service Account**

```bash
# Create service account
gcloud iam service-accounts create graphrag-service \
--description="Service account for GraphRAG API" \
--display-name="GraphRAG Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding your-graphrag-project \
--member="serviceAccount:graphrag-service@your-graphrag-project.iam.gserviceaccount.com" \
--role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding your-graphrag-project \
--member="serviceAccount:graphrag-service@your-graphrag-project.iam.gserviceaccount.com" \
--role="roles/ml.developer"

# Create and download service account key
gcloud iam service-accounts keys create ~/graphrag-service-key.json \
--iam-account=graphrag-service@your-graphrag-project.iam.gserviceaccount.com
```

#### **Security Best Practices**

```bash
# Set restrictive permissions on key file
chmod 600 ~/graphrag-service-key.json

# Store key securely (production)
# - Use Google Secret Manager
# - Use Kubernetes secrets
# - Use environment-specific key management
```

### 3. Environment Configuration

#### **Basic Configuration**

```env
# Google Cloud AI Configuration
LLM_PROVIDER=google
GOOGLE_CLOUD_PROJECT=your-graphrag-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/graphrag-service-key.json

# Vertex AI Configuration
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=text-bison
VERTEX_AI_EMBEDDING_MODEL=textembedding-gecko
VERTEX_AI_ENDPOINT=us-central1-aiplatform.googleapis.com

# Model Parameters
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_OUTPUT_TOKENS=1024
VERTEX_AI_TOP_K=40
VERTEX_AI_TOP_P=0.8
```

#### **Advanced Configuration**

```env
# Performance Tuning
VERTEX_AI_TIMEOUT=60
VERTEX_AI_MAX_RETRIES=3
VERTEX_AI_RETRY_DELAY=1
VERTEX_AI_CONCURRENT_REQUESTS=10

# Cost Management
VERTEX_AI_QUOTA_PROJECT=your-graphrag-project
VERTEX_AI_BUDGET_ALERT_THRESHOLD=1000
VERTEX_AI_DAILY_QUOTA_LIMIT=10000

# Monitoring
VERTEX_AI_ENABLE_LOGGING=true
VERTEX_AI_LOG_LEVEL=INFO
VERTEX_AI_METRICS_ENABLED=true
```

## Model Selection Guide

### **Text Generation Models**

| Model | Capabilities | Input Tokens | Output Tokens | Cost (per 1K tokens) |
|-------|-------------|--------------|---------------|---------------------|
| **text-bison** | General text | 8,192 | 1,024 | $0.0005 |
| **text-bison-32k** | Long context | 32,768 | 8,192 | $0.0010 |
| **gemini-pro** | Advanced reasoning | 32,768 | 8,192 | $0.0005 |
| **gemini-pro-vision** | Multimodal | 16,384 | 2,048 | $0.0025 |
| **chat-bison** | Conversational | 8,192 | 1,024 | $0.0005 |

### **Embedding Models**

| Model | Dimensions | Max Input | Cost (per 1K tokens) | Use Case |
|-------|------------|-----------|---------------------|----------|
| **textembedding-gecko** | 768 | 3,072 | $0.0001 | General embeddings |
| **textembedding-gecko-multilingual** | 768 | 3,072 | $0.0001 | Multilingual text |
| **textembedding-gecko-003** | 768 | 3,072 | $0.0001 | Latest version |

### **Recommended Configurations**

#### **Development Environment**

```env
VERTEX_AI_MODEL=text-bison
VERTEX_AI_EMBEDDING_MODEL=textembedding-gecko
VERTEX_AI_MAX_OUTPUT_TOKENS=512
VERTEX_AI_CONCURRENT_REQUESTS=5
```

#### **Production Environment**

```env
VERTEX_AI_MODEL=gemini-pro
VERTEX_AI_EMBEDDING_MODEL=textembedding-gecko-003
VERTEX_AI_MAX_OUTPUT_TOKENS=1024
VERTEX_AI_CONCURRENT_REQUESTS=20
```

#### **High-Volume Environment**

```env
VERTEX_AI_MODEL=text-bison-32k
VERTEX_AI_EMBEDDING_MODEL=textembedding-gecko-003
VERTEX_AI_MAX_OUTPUT_TOKENS=2048
VERTEX_AI_CONCURRENT_REQUESTS=50
```

## Integration Examples

### **Python Client Example**

```python
from google.cloud import aiplatform
from google.oauth2 import service_account
import json

class VertexAIClient:
def __init__(self, project_id, location, credentials_path):
# Initialize credentials
credentials = service_account.Credentials.from_service_account_file(
credentials_path
)

# Initialize Vertex AI
aiplatform.init(
project=project_id,
location=location,
credentials=credentials
)

self.project_id = project_id
self.location = location

def generate_text(self, prompt, model="text-bison"):
"""Generate text using Vertex AI"""
from vertexai.language_models import TextGenerationModel

model = TextGenerationModel.from_pretrained(model)
response = model.predict(
prompt,
temperature=0.7,
max_output_tokens=1024,
top_k=40,
top_p=0.8
)

return response.text

def get_embeddings(self, texts, model="textembedding-gecko"):
"""Get text embeddings"""
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained(model)
embeddings = model.get_embeddings(texts)

return [embedding.values for embedding in embeddings]

def chat_completion(self, messages, model="chat-bison"):
"""Chat completion with conversation context"""
from vertexai.language_models import ChatModel

chat_model = ChatModel.from_pretrained(model)
chat = chat_model.start_chat()

response = chat.send_message(
messages[-1]["content"],
temperature=0.7,
max_output_tokens=1024
)

return response.text

# Usage example
client = VertexAIClient(
project_id="your-graphrag-project",
location="us-central1",
credentials_path="/path/to/service-key.json"
)

# Generate text
result = client.generate_text("Explain quantum computing")
print(result)

# Get embeddings
embeddings = client.get_embeddings(["machine learning", "artificial intelligence"])
print(f"Embedding dimensions: {len(embeddings[0])}")
```

### **GraphRAG Integration**

```python
from src.graphrag_api_service.providers.google_provider import GoogleProvider

# Initialize provider
provider = GoogleProvider(
project_id="your-graphrag-project",
location="us-central1",
credentials_path="/path/to/service-key.json",
model="gemini-pro",
embedding_model="textembedding-gecko-003"
)

# Use in GraphRAG operations
async def process_documents_with_vertex_ai(documents):
"""Process documents with Vertex AI"""
for doc in documents:
try:
# Generate embeddings
embedding = await provider.get_embeddings(doc.content)

# Extract entities using advanced prompting
entities_prompt = f"""
Extract named entities from the following text.
Return as JSON with entity name, type, and description.

Text: {doc.content}
"""
entities_response = await provider.generate_text(entities_prompt)
entities = json.loads(entities_response)

# Extract relationships
relationships_prompt = f"""
Identify relationships between entities in the text.
Return as JSON with source, target, relationship type, and confidence.

Text: {doc.content}
Entities: {entities}
"""
relationships_response = await provider.generate_text(relationships_prompt)
relationships = json.loads(relationships_response)

# Store in knowledge graph
await store_in_graph(doc, embedding, entities, relationships)

except Exception as e:
logger.error(f"Error processing document {doc.id}: {e}")
continue
```

## Cost Management

### **Cost Optimization Strategies**

#### **Model Selection**

```python
# Cost-effective model selection based on use case
def select_optimal_model(task_type, content_length, quality_requirement):
"""Select most cost-effective model for task"""

if task_type == "embedding":
return "textembedding-gecko" # Lowest cost for embeddings

elif task_type == "entity_extraction":
if content_length < 2000:
return "text-bison" # Cheaper for short content
else:
return "text-bison-32k" # Better for long content

elif task_type == "relationship_extraction":
if quality_requirement == "high":
return "gemini-pro" # Best quality
else:
return "text-bison" # Good balance

return "text-bison" # Default fallback
```

#### **Batch Processing**

```python
async def batch_process_embeddings(texts, batch_size=100):
"""Process embeddings in batches to optimize costs"""
embeddings = []

for i in range(0, len(texts), batch_size):
batch = texts[i:i + batch_size]
batch_embeddings = await provider.get_embeddings(batch)
embeddings.extend(batch_embeddings)

# Add delay to respect rate limits
await asyncio.sleep(0.1)

return embeddings
```

#### **Caching Strategy**

```python
import hashlib
from functools import wraps

def cache_expensive_calls(cache_duration=3600):
"""Cache expensive API calls to reduce costs"""
def decorator(func):
@wraps(func)
async def wrapper(*args, **kwargs):
# Create cache key from function arguments
cache_key = hashlib.md5(
f"{func.__name__}:{str(args)}:{str(kwargs)}".encode()
).hexdigest()

# Check cache first
cached_result = await redis_client.get(cache_key)
if cached_result:
return json.loads(cached_result)

# Call API if not cached
result = await func(*args, **kwargs)

# Cache result
await redis_client.setex(
cache_key,
cache_duration,
json.dumps(result)
)

return result
return wrapper
return decorator

@cache_expensive_calls(cache_duration=7200) # 2 hours
async def get_cached_embeddings(text):
return await provider.get_embeddings([text])
```

### **Budget Monitoring**

```python
from google.cloud import billing

def setup_budget_alerts(project_id, budget_amount):
"""Setup budget alerts for cost control"""
client = billing.CloudBillingClient()

# Create budget
budget = {
"display_name": "GraphRAG API Budget",
"budget_filter": {
"projects": [f"projects/{project_id}"],
"services": ["services/aiplatform.googleapis.com"]
},
"amount": {
"specified_amount": {
"currency_code": "USD",
"units": str(budget_amount)
}
},
"threshold_rules": [
{
"threshold_percent": 0.5, # 50% alert
"spend_basis": "CURRENT_SPEND"
},
{
"threshold_percent": 0.9, # 90% alert
"spend_basis": "CURRENT_SPEND"
}
]
}

# Create budget (requires billing admin permissions)
# This is typically done through the console or terraform
return budget
```

## Performance Optimization

### **Request Optimization**

```python
import asyncio
import aiohttp
from typing import List

class OptimizedVertexAIClient:
def __init__(self, max_concurrent_requests=10):
self.semaphore = asyncio.Semaphore(max_concurrent_requests)
self.session = None

async def __aenter__(self):
self.session = aiohttp.ClientSession()
return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
await self.session.close()

async def batch_generate_text(self, prompts: List[str]) -> List[str]:
"""Generate text for multiple prompts concurrently"""
tasks = []

for prompt in prompts:
task = self._generate_text_with_semaphore(prompt)
tasks.append(task)

results = await asyncio.gather(*tasks, return_exceptions=True)

# Handle exceptions
successful_results = []
for result in results:
if isinstance(result, Exception):
logger.error(f"Text generation failed: {result}")
successful_results.append("")
else:
successful_results.append(result)

return successful_results

async def _generate_text_with_semaphore(self, prompt: str) -> str:
"""Generate text with concurrency control"""
async with self.semaphore:
return await self._generate_text(prompt)

async def _generate_text(self, prompt: str) -> str:
"""Internal text generation method"""
# Implementation depends on your preferred client library
# This is a simplified example
pass
```

### **Rate Limiting**

```python
import time
from collections import deque

class RateLimiter:
def __init__(self, max_requests_per_minute=60):
self.max_requests = max_requests_per_minute
self.requests = deque()

async def acquire(self):
"""Acquire permission to make a request"""
now = time.time()

# Remove requests older than 1 minute
while self.requests and self.requests[0] < now - 60:
self.requests.popleft()

# Check if we can make a request
if len(self.requests) >= self.max_requests:
# Calculate wait time
wait_time = 60 - (now - self.requests[0])
await asyncio.sleep(wait_time)
return await self.acquire()

# Record this request
self.requests.append(now)
return True

# Usage
rate_limiter = RateLimiter(max_requests_per_minute=100)

async def rate_limited_api_call():
await rate_limiter.acquire()
return await provider.generate_text("Your prompt here")
```

## Monitoring & Troubleshooting

### **Logging Configuration**

```python
import logging
from google.cloud import logging as cloud_logging

def setup_cloud_logging(project_id):
"""Setup Google Cloud Logging"""
client = cloud_logging.Client(project=project_id)
client.setup_logging()

# Create custom logger for Vertex AI operations
logger = logging.getLogger("vertex_ai_operations")
logger.setLevel(logging.INFO)

return logger

# Usage
logger = setup_cloud_logging("your-graphrag-project")

async def logged_api_call(prompt):
"""API call with comprehensive logging"""
start_time = time.time()

try:
logger.info(f"Starting text generation for prompt: {prompt[:100]}...")

result = await provider.generate_text(prompt)

duration = time.time() - start_time
logger.info(f"Text generation completed in {duration:.2f}s")

return result

except Exception as e:
logger.error(f"Text generation failed: {e}", exc_info=True)
raise
```

### **Health Monitoring**

```python
async def health_check_vertex_ai():
"""Comprehensive health check for Vertex AI"""
health_status = {
"service": "vertex_ai",
"status": "healthy",
"checks": {}
}

try:
# Test text generation
start_time = time.time()
test_result = await provider.generate_text("Test prompt")
generation_time = time.time() - start_time

health_status["checks"]["text_generation"] = {
"status": "healthy",
"response_time": generation_time,
"details": "Text generation working"
}

# Test embeddings
start_time = time.time()
test_embedding = await provider.get_embeddings(["test"])
embedding_time = time.time() - start_time

health_status["checks"]["embeddings"] = {
"status": "healthy",
"response_time": embedding_time,
"details": f"Embeddings working, dimension: {len(test_embedding[0])}"
}

except Exception as e:
health_status["status"] = "unhealthy"
health_status["error"] = str(e)

return health_status
```

## Production Deployment

### **Kubernetes Configuration**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
name: graphrag-api-google
spec:
replicas: 3
selector:
matchLabels:
app: graphrag-api-google
template:
metadata:
labels:
app: graphrag-api-google
spec:
serviceAccountName: graphrag-service-account
containers:
- name: graphrag-api
image: graphrag-api:latest
env:
- name: LLM_PROVIDER
value: "google"
- name: GOOGLE_CLOUD_PROJECT
value: "your-graphrag-project"
- name: VERTEX_AI_LOCATION
value: "us-central1"
- name: GOOGLE_APPLICATION_CREDENTIALS
value: "/var/secrets/google/key.json"
volumeMounts:
- name: google-service-account
mountPath: /var/secrets/google
readOnly: true
resources:
requests:
memory: "2Gi"
cpu: "1"
limits:
memory: "4Gi"
cpu: "2"
volumes:
- name: google-service-account
secret:
secretName: google-service-account-key
---
apiVersion: v1
kind: Secret
metadata:
name: google-service-account-key
type: Opaque
data:
key.json: <base64-encoded-service-account-key>
```

### **Terraform Configuration**

```hcl
# terraform/vertex_ai.tf
resource "google_project_service" "vertex_ai" {
project = var.project_id
service = "aiplatform.googleapis.com"
}

resource "google_service_account" "graphrag_service" {
account_id = "graphrag-service"
display_name = "GraphRAG Service Account"
project = var.project_id
}

resource "google_project_iam_member" "vertex_ai_user" {
project = var.project_id
role = "roles/aiplatform.user"
member = "serviceAccount:${google_service_account.graphrag_service.email}"
}

resource "google_service_account_key" "graphrag_key" {
service_account_id = google_service_account.graphrag_service.name
}

# Budget alert
resource "google_billing_budget" "graphrag_budget" {
billing_account = var.billing_account
display_name = "GraphRAG API Budget"

budget_filter {
projects = ["projects/${var.project_id}"]
services = ["services/aiplatform.googleapis.com"]
}

amount {
specified_amount {
currency_code = "USD"
units = "1000"
}
}

threshold_rules {
threshold_percent = 0.5
spend_basis = "CURRENT_SPEND"
}

threshold_rules {
threshold_percent = 0.9
spend_basis = "CURRENT_SPEND"
}
}
```

## Best Practices

### **Security**

- Use service accounts with minimal required permissions
- Rotate service account keys regularly
- Store credentials securely (Secret Manager, Kubernetes secrets)
- Enable audit logging for all API calls
- Use VPC Service Controls for network isolation

### **Cost Management**

- Implement request caching to reduce API calls
- Use appropriate models for each task type
- Monitor usage and set up budget alerts
- Implement rate limiting to prevent cost spikes
- Regular cost analysis and optimization

### **Performance**

- Use batch processing for multiple requests
- Implement proper error handling and retries
- Monitor response times and optimize accordingly
- Use regional endpoints for better latency
- Implement circuit breakers for resilience

### **Monitoring**

- Set up comprehensive logging and monitoring
- Track key metrics (latency, error rates, costs)
- Implement health checks and alerting
- Monitor quota usage and limits
- Regular performance analysis and tuning
