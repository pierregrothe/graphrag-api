# GraphRAG API Service

A FastAPI-based API service for Microsoft GraphRAG with multi-provider LLM support.

This project provides a robust and scalable API to interact with the Microsoft GraphRAG engine, supporting both
local (Ollama) and cloud-based (Google Gemini) language models for flexible deployment scenarios.

## Architecture

### Multi-Provider LLM Support

```mermaid
graph TD
    A[Client] --> B[FastAPI Server]
    B --> C{LLM Provider Factory}
    C -->|Local| D[Ollama Integration]
    C -->|Cloud| E[Google Gemini Integration]
    D --> F[Gemma3:4b Model]
    E --> G[Gemini 2.5 Flash/Pro]
    D --> H[Local Embeddings]
    E --> I[Cloud Embeddings]
    F --> J[GraphRAG Engine]
    G --> J
    H --> J
    I --> J
    J --> K[Knowledge Graph]
```

## Key Features

### Core Capabilities

- **FastAPI Backend**: High-performance async web framework with automatic OpenAPI documentation
- **GraphRAG Integration**: Complete Microsoft GraphRAG implementation for graph-based RAG
- **Multi-Provider Architecture**: Unified abstraction layer with factory pattern for LLM provider switching
- **Provider Abstraction**: Abstract base classes for consistent interface across all providers

### LLM Provider Support

- **Local Ollama**: Privacy-focused local deployment with Gemma3:4b
    - No external API costs
    - Complete data privacy
    - Local embeddings with nomic-embed-text
    - Direct integration without proxy layers

- **Google Cloud Gemini**: Cloud-based high-performance deployment
    - Latest Gemini models (2.5-flash, 2.5-pro)
    - Enterprise-grade reliability and scaling
    - Advanced multimodal capabilities
    - Support for both Google Cloud API and Vertex AI endpoints
    - Flexible authentication (API keys or Application Default Credentials)

### GraphRAG Operations

- **Indexing**: Background processing for document ingestion and knowledge graph creation
- **Querying**: Global and local search modes with configurable community levels
- **Workspace Management**: Multi-project support with isolated configurations
- **Real-time Status**: Progress tracking and health monitoring

### Developer Experience

- **Code Quality**: Black formatting + Ruff linting + mypy type checking with 100% test coverage
- **Type Safety**: Static type analysis prevents runtime errors and improves IDE support
- **Configuration Management**: Environment-based settings with Pydantic validation
- **Comprehensive Testing**: pytest framework with provider-specific test suites
- **Documentation**: Auto-generated API docs and comprehensive project documentation

## Getting Started

### Prerequisites

- **Python 3.12**: Project uses Python 3.12 specifically
- **Poetry**: For dependency management
- **Provider Setup**: Either Ollama (local) or Google Cloud credentials

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/pierregrothe/graphrag-api.git
   cd graphrag-api
   ```

2. **Install dependencies:**

   ```bash
   poetry install
   ```

3. **Configure your LLM provider:**

   **For Ollama (Local):**

   ```bash
   # Install and start Ollama
   # Pull required models
   ollama pull gemma:4b
   ollama pull nomic-embed-text

   # Set environment variables
   export GRAPHRAG_LLM_PROVIDER=ollama
   export OLLAMA_BASE_URL=http://localhost:11434
   ```

   **For Google Gemini (Cloud):**

   ```bash
   # Standard Google Cloud API (requires API key)
   export GRAPHRAG_LLM_PROVIDER=google_gemini
   export GOOGLE_API_KEY=your_api_key
   export GOOGLE_PROJECT_ID=your_project_id

   # Optional: Use Vertex AI endpoints (no API key needed if using ADC)
   export GOOGLE_CLOUD_USE_VERTEX_AI=true
   export VERTEX_AI_LOCATION=us-central1
   export VERTEX_AI_ENDPOINT=https://custom-vertex.googleapis.com  # Optional custom endpoint
   ```

4. **Run the application:**

   ```bash
   poetry run uvicorn src.graphrag_api_service.main:app --reload
   ```

5. **Access the API:**
   - **API Documentation**: <http://localhost:8001/docs>
   - **Health Check**: <http://localhost:8001/health>
   - **GraphRAG Status**: <http://localhost:8001/graphrag/status>

## API Endpoints

### Core Endpoints

- `GET /` - API information and status
- `GET /health` - Health check
- `GET /info` - Application configuration details

### GraphRAG Endpoints

- `POST /graphrag/index` - Index documents for knowledge graph creation
- `POST /graphrag/query` - Query the knowledge graph
- `GET /graphrag/status` - Get GraphRAG system status and configuration

## Project Documentation

- **API Documentation**: Interactive Swagger UI documentation at `/docs`
- **ReDoc Documentation**: ReDoc API documentation at `/redoc`
- **Project Plan**: [PROJECT_PLAN.md](PROJECT_PLAN.md) - Implementation roadmap and phases
- **Development Notes**: [GEMINI.md](GEMINI.md) - Key decisions and conventions
- **Claude Code Context**: [CLAUDE.md](CLAUDE.md) - Development environment context

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
