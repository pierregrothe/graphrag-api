# Ollama Integration Guide

## Overview

Ollama provides local LLM deployment for GraphRAG API, offering complete data privacy, no API costs, and offline operation capabilities. This guide covers installation, configuration, and optimization for production use.

## Installation & Setup

### 1. Install Ollama

#### **Linux/macOS**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version
```

#### **Windows**
1. Download installer from https://ollama.ai/download
2. Run installer and follow setup wizard
3. Verify installation in Command Prompt:
```cmd
ollama --version
```

#### **Docker Installation**
```bash
# Run Ollama in Docker
docker run -d \
--name ollama \
-p 11434:11434 \
-v ollama:/root/.ollama \
ollama/ollama

# Verify container is running
docker ps | grep ollama
```

### 2. Download Required Models

#### **Text Generation Models**
```bash
# Recommended models for GraphRAG
ollama pull llama2 # 7B parameters, good balance
ollama pull llama2:13b # 13B parameters, better quality
ollama pull codellama # Code-optimized model
ollama pull mistral # Fast and efficient
ollama pull gemma:7b # Google's Gemma model

# List installed models
ollama list
```

#### **Embedding Models**
```bash
# Essential for semantic search
ollama pull nomic-embed-text # Recommended for text embeddings
ollama pull all-minilm # Alternative embedding model

# Verify embedding model
ollama run nomic-embed-text "test embedding"
```

### 3. Configuration

#### **Environment Variables**
```env
# Ollama Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT=60
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=1

# Performance Tuning
OLLAMA_NUM_PARALLEL=4
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_PREDICT=512
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_K=40
OLLAMA_TOP_P=0.9
```

#### **Advanced Configuration**
```env
# Memory Management
OLLAMA_MAX_LOADED_MODELS=3
OLLAMA_KEEP_ALIVE=5m
OLLAMA_NUM_GPU=1

# Network Configuration
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_ORIGINS=["http://localhost:8000"]

# Logging
OLLAMA_DEBUG=false
OLLAMA_LOG_LEVEL=INFO
```

## Model Selection Guide

### **Text Generation Models**

| Model | Size | RAM Required | Speed | Quality | Use Case |
|-------|------|--------------|-------|---------|----------|
| **llama2** | 7B | 8GB | Fast | Good | General purpose |
| **llama2:13b** | 13B | 16GB | Medium | Better | High quality responses |
| **mistral** | 7B | 8GB | Very Fast | Good | Quick responses |
| **codellama** | 7B | 8GB | Fast | Code-focused | Code analysis |
| **gemma:7b** | 7B | 8GB | Fast | Good | Balanced performance |

### **Embedding Models**

| Model | Dimensions | Performance | Use Case |
|-------|------------|-------------|----------|
| **nomic-embed-text** | 768 | Excellent | General text embeddings |
| **all-minilm** | 384 | Good | Lightweight embeddings |

### **Recommended Configurations**

#### **Development Environment**
```env
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=256
```

#### **Production Environment**
```env
OLLAMA_MODEL=llama2:13b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_PREDICT=512
OLLAMA_NUM_PARALLEL=8
```

## Performance Optimization

### **Hardware Requirements**

#### **Minimum Requirements**
- **CPU**: 4 cores, 2.5GHz+
- **RAM**: 8GB (for 7B models)
- **Storage**: 10GB free space
- **GPU**: Optional (NVIDIA with CUDA support)

#### **Recommended Requirements**
- **CPU**: 8+ cores, 3.0GHz+
- **RAM**: 16GB+ (for 13B models)
- **Storage**: 50GB+ SSD
- **GPU**: NVIDIA RTX 3060+ with 8GB+ VRAM

#### **Production Requirements**
- **CPU**: 16+ cores, 3.5GHz+
- **RAM**: 32GB+ (for multiple models)
- **Storage**: 100GB+ NVMe SSD
- **GPU**: NVIDIA RTX 4080+ with 16GB+ VRAM

### **GPU Acceleration**

#### **NVIDIA GPU Setup**
```bash
# Install NVIDIA drivers and CUDA
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit

# Verify GPU detection
nvidia-smi

# Configure Ollama for GPU
export OLLAMA_NUM_GPU=1
ollama serve
```

#### **AMD GPU Setup (ROCm)**
```bash
# Install ROCm (Linux only)
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian/ ubuntu main' | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt update
sudo apt install rocm-dev

# Configure environment
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export OLLAMA_NUM_GPU=1
```

### **Memory Optimization**

#### **Model Loading Strategy**
```bash
# Preload frequently used models
ollama run llama2 "preload"
ollama run nomic-embed-text "preload"

# Configure keep-alive to reduce loading time
export OLLAMA_KEEP_ALIVE=10m
```

#### **Concurrent Request Handling**
```env
# Optimize for concurrent requests
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_CONCURRENT_REQUESTS=8
```

## Integration Examples

### **Python Client Example**
```python
import requests
import json

class OllamaClient:
def __init__(self, base_url="http://localhost:11434"):
self.base_url = base_url

def generate_text(self, prompt, model="llama2"):
"""Generate text using Ollama"""
response = requests.post(
f"{self.base_url}/api/generate",
json={
"model": model,
"prompt": prompt,
"stream": False,
"options": {
"temperature": 0.7,
"top_k": 40,
"top_p": 0.9
}
}
)
return response.json()["response"]

def get_embeddings(self, text, model="nomic-embed-text"):
"""Get text embeddings"""
response = requests.post(
f"{self.base_url}/api/embeddings",
json={
"model": model,
"prompt": text
}
)
return response.json()["embedding"]

def health_check(self):
"""Check Ollama service health"""
try:
response = requests.get(f"{self.base_url}/api/tags")
return response.status_code == 200
except:
return False

# Usage example
client = OllamaClient()

# Check if service is running
if client.health_check():
# Generate text
result = client.generate_text("Explain machine learning in simple terms")
print(result)

# Get embeddings
embedding = client.get_embeddings("machine learning")
print(f"Embedding dimension: {len(embedding)}")
```

### **GraphRAG Integration**
```python
# GraphRAG API integration with Ollama
from src.graphrag_api_service.providers.ollama_provider import OllamaProvider

# Initialize provider
provider = OllamaProvider(
base_url="http://localhost:11434",
model="llama2",
embedding_model="nomic-embed-text"
)

# Use in GraphRAG operations
async def process_documents(documents):
"""Process documents with Ollama"""
for doc in documents:
# Generate embeddings
embedding = await provider.get_embeddings(doc.content)

# Extract entities and relationships
entities = await provider.extract_entities(doc.content)
relationships = await provider.extract_relationships(doc.content)

# Store in knowledge graph
await store_in_graph(doc, embedding, entities, relationships)
```

## Monitoring & Troubleshooting

### **Health Monitoring**
```bash
# Check Ollama service status
curl http://localhost:11434/api/tags

# Monitor resource usage
htop # or top on macOS
nvidia-smi # for GPU monitoring

# Check model loading status
ollama ps
```

### **Performance Monitoring**
```python
import time
import psutil
import requests

def monitor_ollama_performance():
"""Monitor Ollama performance metrics"""
start_time = time.time()

# Test text generation
response = requests.post(
"http://localhost:11434/api/generate",
json={
"model": "llama2",
"prompt": "Test prompt",
"stream": False
}
)

generation_time = time.time() - start_time

# System metrics
cpu_usage = psutil.cpu_percent()
memory_usage = psutil.virtual_memory().percent

print(f"Generation time: {generation_time:.2f}s")
print(f"CPU usage: {cpu_usage}%")
print(f"Memory usage: {memory_usage}%")

return {
"generation_time": generation_time,
"cpu_usage": cpu_usage,
"memory_usage": memory_usage
}
```

### **Common Issues & Solutions**

#### **Model Loading Errors**
```bash
# Issue: Model not found
# Solution: Download the model
ollama pull llama2

# Issue: Insufficient memory
# Solution: Use smaller model or increase RAM
ollama pull llama2:7b # instead of 13b
```

#### **Connection Issues**
```bash
# Issue: Connection refused
# Solution: Start Ollama service
ollama serve

# Issue: Port conflicts
# Solution: Change port
export OLLAMA_HOST=0.0.0.0:11435
ollama serve
```

#### **Performance Issues**
```bash
# Issue: Slow generation
# Solutions:
export OLLAMA_NUM_GPU=1 # Enable GPU
export OLLAMA_NUM_PARALLEL=4 # Increase parallelism
export OLLAMA_NUM_CTX=2048 # Reduce context size
```

## Production Deployment

### **Docker Compose Configuration**
```yaml
version: '3.8'
services:
ollama:
image: ollama/ollama:latest
container_name: ollama
ports:
- "11434:11434"
volumes:
- ollama_data:/root/.ollama
environment:
- OLLAMA_NUM_PARALLEL=4
- OLLAMA_MAX_LOADED_MODELS=3
- OLLAMA_KEEP_ALIVE=10m
deploy:
resources:
reservations:
devices:
- driver: nvidia
count: 1
capabilities: [gpu]
restart: unless-stopped
healthcheck:
test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
interval: 30s
timeout: 10s
retries: 3

graphrag-api:
image: graphrag-api:latest
depends_on:
- ollama
environment:
- LLM_PROVIDER=ollama
- OLLAMA_BASE_URL=http://ollama:11434
- OLLAMA_MODEL=llama2
ports:
- "8000:8000"

volumes:
ollama_data:
```

### **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
name: ollama
spec:
replicas: 1
selector:
matchLabels:
app: ollama
template:
metadata:
labels:
app: ollama
spec:
containers:
- name: ollama
image: ollama/ollama:latest
ports:
- containerPort: 11434
env:
- name: OLLAMA_NUM_PARALLEL
value: "4"
- name: OLLAMA_MAX_LOADED_MODELS
value: "3"
resources:
requests:
memory: "8Gi"
cpu: "4"
nvidia.com/gpu: 1
limits:
memory: "16Gi"
cpu: "8"
nvidia.com/gpu: 1
volumeMounts:
- name: ollama-data
mountPath: /root/.ollama
volumes:
- name: ollama-data
persistentVolumeClaim:
claimName: ollama-pvc
```

## Cost Analysis

### **Operational Costs**

| Component | Development | Production | Enterprise |
|-----------|-------------|------------|------------|
| **Hardware** | $0 (existing) | $2,000-5,000 | $10,000+ |
| **Electricity** | $20-50/month | $100-300/month | $500+/month |
| **Maintenance** | $0 | $200-500/month | $1,000+/month |
| **Total Monthly** | $20-50 | $300-800 | $1,500+ |

### **Cost Comparison vs Cloud**

| Usage Level | Ollama (Local) | OpenAI API | Google Cloud |
|-------------|----------------|------------|--------------|
| **1M tokens/month** | $50 | $200 | $150 |
| **10M tokens/month** | $100 | $2,000 | $1,500 |
| **100M tokens/month** | $300 | $20,000 | $15,000 |

**Break-even Point**: ~5M tokens/month for production deployment

## Best Practices

### **Security**
- Run Ollama in isolated network segment
- Use firewall rules to restrict access
- Regular security updates and patches
- Monitor for unusual resource usage

### **Backup & Recovery**
- Backup model files and configurations
- Document model versions and settings
- Test recovery procedures regularly
- Monitor disk space for model storage

### **Scaling**
- Use load balancers for multiple Ollama instances
- Implement model caching strategies
- Monitor and scale based on usage patterns
- Consider model quantization for efficiency

### **Monitoring**
- Set up alerts for service availability
- Monitor resource usage and performance
- Track model loading times and errors
- Log all API interactions for debugging
