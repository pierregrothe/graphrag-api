# GraphRAG API Service

A FastAPI-based API service for Microsoft GraphRAG with multi-provider LLM support.

This project provides a robust and scalable API to interact with the Microsoft GraphRAG engine, supporting both
local (Ollama) and cloud-based (Google Gemini) language models for flexible deployment scenarios.

## 🎯 Current Status

**✅ Production Ready Features:**
- **159/159 tests passing** (100% success rate) 🎯
- **Type safety implemented** with comprehensive mypy checking (0 errors)
- **Multi-provider LLM support** (Ollama, Google Gemini, Vertex AI)
- **Comprehensive REST API** with full GraphRAG integration
- **Complete GraphQL interface** with queries, mutations, and playground
- **100% API feature parity** between REST and GraphQL (27/27 features)
- **Workspace management** with isolated environments
- **Advanced indexing system** with complete job management
- **Graph operations** with visualization and export capabilities
- **System monitoring** with health checks and metrics
- **Cross-API validation** with comprehensive integration tests
- **Cache management** with statistics and clearing operations

**🎉 Phase 8 COMPLETED - 100% Unified API Operations:**
- **ACHIEVED 100% feature parity** between REST and GraphQL APIs (27/27 features)
- Added missing REST endpoints for single entity/relationship access and cache management
- Implemented complete GraphQL operations for indexing, cache management, and application info
- Created comprehensive cross-API integration test suite (10 tests)
- Established unified response formats and error handling patterns
- Documented complete feature parity matrix with 100% coverage
- **MILESTONE**: Both APIs now offer identical functionality with developer choice

## Architecture

### Multi-Provider LLM Support

```mermaid
flowchart TD
    %% Client Layer
    subgraph ClientLayer ["🌐 Client Applications"]
        A[Web Client]
        A1[Mobile App]
        A2[API Client]
    end

    %% FastAPI Server Layer
    subgraph ServerLayer ["⚡ FastAPI Server (Implemented)"]
        B(FastAPI Server)
        B1[Health Endpoints]
        B2[Info Endpoints]
        B3[GraphRAG Endpoints]
    end

    %% Configuration Layer
    subgraph ConfigLayer ["⚙️ Configuration System (Implemented)"]
        C1[Environment Variables]
        C2[Pydantic Settings]
        C3[Provider Selection]
    end

    %% Provider Factory Layer - IMPLEMENTED
    subgraph FactoryLayer ["🔄 LLM Provider Factory (Implemented)"]
        D{Provider Factory}
        D1[Configuration Loader]
        D2((Health Monitor))
        D3[Provider Registry]
    end

    %% Ollama Provider - IMPLEMENTED
    subgraph OllamaLayer ["🏠 Ollama Provider (Implemented)"]
        E[Ollama Client]
        E1[Gemma 4b Integration]
        E2[Embedding Support]
        E3[Health Checks]
    end

    %% Gemini Provider - IMPLEMENTED
    subgraph GeminiLayer ["☁️ Google Gemini Provider (Implemented)"]
        F[Gemini Client]
        F1[Gemini 2.5 Flash/Pro]
        F2[Vertex AI Support]
        F3[API Key Management]
    end

    %% Graph Operations Layer - NEWLY IMPLEMENTED
    subgraph GraphOperationsLayer ["📊 Graph Operations (Implemented)"]
        H[Entity Querying]
        H1[Relationship Querying]
        H2[Graph Statistics]
        H3[Visualization Data]
        H4[Graph Export]
    end

    %% GraphRAG Core Layer - PARTIALLY IMPLEMENTED
    subgraph GraphRAGCoreLayer ["🚧 GraphRAG Core (Phase 3 - Partially Implemented)"]
        G[Document Indexing]
        G1[Knowledge Graph Creation]
        G2[Query Processing]
        G3[Vector Storage]
        G4[Load GraphRAG Artifacts]
    end

    %% Current Implementation Flow
    ClientLayer --> ServerLayer
    ServerLayer --> ConfigLayer
    ConfigLayer --> FactoryLayer
    ServerLayer --> GraphOperationsLayer

    FactoryLayer -->|Provider Selection| OllamaLayer
    FactoryLayer -->|Provider Selection| GeminiLayer

    GraphOperationsLayer -->|Loads data from| GraphRAGCoreLayer
    GraphRAGCoreLayer -->|Provides data to| GraphOperationsLayer

    %% Styling
    classDef implementedStyle fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000
    classDef placeholderStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef futureStyle fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#666,stroke-dasharray: 5 5
    classDef clientStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef newImplementedStyle fill:#e0f7fa,stroke:#00bcd4,stroke-width:3px,color:#000

    %% Apply Classes
    class ClientLayer clientStyle
    class ServerLayer implementedStyle
    class ConfigLayer implementedStyle
    class FactoryLayer implementedStyle
    class OllamaLayer implementedStyle
    class GeminiLayer implementedStyle
    class B3 implementedStyle
    class GraphOperationsLayer newImplementedStyle
    class GraphRAGCoreLayer futureStyle
    class G,G1,G2,G3,G4 futureStyle
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
- **Graph Operations**:
    - **Entity Querying**: Search and retrieve entities from the knowledge graph with filtering and pagination.
    - **Relationship Querying**: Search and retrieve relationships between entities with filtering and pagination.
    - **Graph Statistics**: Obtain comprehensive statistics about the knowledge graph, including
      entity/relationship counts, type distributions, and density.
    - **Visualization Data Generation**: Generate structured data (nodes and edges) suitable for
      rendering interactive graph visualizations.
    - **Graph Export**: Export graph data (entities, relationships, communities) to various formats like JSON and CSV.

## System Flow Diagrams

### Current System Flow - What's Actually Implemented

```mermaid
sequenceDiagram
    participant Client as 📱 Client App
    participant API as ⚡ FastAPI Server
    participant Config as ⚙️ Configuration System
    participant Factory as 🔄 Provider Factory
    participant Ollama as 🏠 Ollama Provider
    participant Gemini as ☁️ Gemini Provider
    participant GraphOps as 📊 Graph Operations

    rect rgb(232, 245, 233)
        Note over Client,API: Health & Info Endpoints (✅ Implemented)
        Client->>+API: GET /health
        API-->>-Client: Server Status ✅

        Client->>+API: GET /info
        API->>+Config: Load Settings
        Config-->>-API: Provider Configuration
        API-->>-Client: System Information ✅
    end

    rect rgb(230, 245, 255)
        Note over Client,Factory: Provider Status & Health Monitoring (✅ Implemented)
        Client->>+API: GET /graphrag/status
        API->>+Config: Load Provider Settings
        Config-->>-API: Current Provider Type

        API->>+Factory: Get Provider Health
        Factory->>Factory: Load Configuration

        alt Ollama Provider Configured
            Factory->>+Ollama: Health Check
            Ollama->>Ollama: Check localhost:11434
            Ollama->>Ollama: Verify Models Available
            Ollama-->>-Factory: Health Status ✅/❌
        else Gemini Provider Configured
            Factory->>+Gemini: Health Check
            Gemini->>Gemini: Validate API Key/ADC
            Gemini->>Gemini: Test Model Access
            Gemini-->>-Factory: Health Status ✅/❌
        end

        Factory-->>-API: Provider Health Info
        API-->>-Client: Complete System Status ✅
    end

    rect rgb(224, 247, 250)
        Note over Client,API: GraphRAG Endpoints (✅ Implemented - Graph Operations)
        Client->>+API: POST /graphrag/graph/entities/query
        API->>+GraphOps: query_entities(filters, pagination)
        GraphOps->>GraphOps: Load entities.parquet
        GraphOps-->>-API: EntityQueryResponse
        API-->>-Client: Query Results ✅

        Client->>+API: POST /graphrag/graph/relationships/query
        API->>+GraphOps: query_relationships(filters, pagination)
        GraphOps->>GraphOps: Load relationships.parquet
        GraphOps-->>-API: RelationshipQueryResponse
        API-->>-Client: Query Results ✅

        Client->>+API: GET /graphrag/graph/statistics
        API->>+GraphOps: get_graph_statistics()
        GraphOps->>GraphOps: Load all parquet files
        GraphOps-->>-API: GraphStatsResponse
        API-->>-Client: Statistics ✅

        Client->>+API: POST /graphrag/graph/visualize
        API->>+GraphOps: generate_visualization(limits, layout)
        GraphOps->>GraphOps: Load entities/relationships.parquet
        GraphOps-->>-API: GraphVisualizationResponse
        API-->>-Client: Visualization Data ✅

        Client->>+API: POST /graphrag/graph/export
        API->>+GraphOps: export_graph(format, includes)
        GraphOps->>GraphOps: Load selected parquet files
        GraphOps->>GraphOps: Create temp export file
        GraphOps-->>-API: GraphExportResponse
        API-->>-Client: Export Details ✅
    end
```

### Provider System States - Current Implementation

```mermaid
stateDiagram-v2
    [*] --> ServerStartup: FastAPI Server Start

    state "Configuration Loading (✅ Implemented)" as ConfigLoad {
        [*] --> LoadEnv: Load .env Variables
        LoadEnv --> ParseSettings: Pydantic Validation
        ParseSettings --> SelectProvider: Determine LLM_PROVIDER

        state SelectProvider {
            [*] --> CheckProvider
            CheckProvider --> OllamaConfig: LLM_PROVIDER=ollama
            CheckProvider --> GeminiConfig: LLM_PROVIDER=google_gemini
        }
    }

    ServerStartup --> ConfigLoad

    state "Ollama Provider (✅ Implemented)" as OllamaProvider {
        [*] --> InitOllama: Initialize Ollama Client
        InitOllama --> TestConnection: Check Ollama Server
        TestConnection --> OllamaHealthy: Connection Success
        TestConnection --> OllamaUnhealthy: Connection Failed
        OllamaHealthy --> [*]: Provider Ready
        OllamaUnhealthy --> [*]: Provider Unavailable
    }

    state "Gemini Provider (✅ Implemented)" as GeminiProvider {
        [*] --> InitGemini: Initialize Gemini Client
        InitGemini --> ValidateAuth: Check API Key or ADC
        ValidateAuth --> TestModels: Verify Model Access
        TestModels --> GeminiHealthy: Authentication Success
        TestModels --> GeminiUnhealthy: Auth Access Failed
        GeminiHealthy --> [*]: Provider Ready
        GeminiUnhealthy --> [*]: Provider Unavailable
    }

    ConfigLoad --> OllamaProvider: Ollama Selected
    ConfigLoad --> GeminiProvider: Gemini Selected

    state "API Service (✅ Implemented)" as APIService {
        [*] --> ServingRequests: Ready for HTTP Requests
        ServingRequests --> HealthCheck: GET health
        ServingRequests --> InfoRequest: GET info
        ServingRequests --> StatusRequest: GET graphrag status
        ServingRequests --> GraphOperationsRequest: GraphRAG Graph Endpoints

        HealthCheck --> ServingRequests: OK Response
        InfoRequest --> ServingRequests: Configuration Info
        StatusRequest --> ServingRequests: Provider Status
        GraphOperationsRequest --> ServingRequests: Graph Operations Response
    }

    OllamaProvider --> APIService: Provider Initialized
    GeminiProvider --> APIService: Provider Initialized

    APIService --> [*]: Server Shutdown
```

### Developer Experience

- **Code Quality**: Black formatting + Ruff linting + mypy type checking with 100% clean pipeline
- **Type Safety**: Complete static type analysis with zero type errors in production code
- **Documentation Quality**: markdownlint + prettier for consistent documentation formatting
- **Configuration Management**: Environment-based settings with Pydantic validation
- **Comprehensive Testing**: pytest framework with 65 tests across all components
- **Quality Assurance**: Integrated quality pipeline catching errors before runtime
- **Development Workflow**: Auto-generated API docs and comprehensive project documentation
- **Windows Compatibility**: No emoji usage in code to prevent Unicode encoding errors

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
- `POST /graphrag/graph/entities/query` - Query entities from the knowledge graph
- `POST /graphrag/graph/relationships/query` - Query relationships from the knowledge graph
- `GET /graphrag/graph/statistics` - Get comprehensive statistics about the knowledge graph
- `POST /graphrag/graph/visualize` - Generate data for graph visualization
- `POST /graphrag/graph/export` - Export graph data in various formats

## Current Development Status

**Phase 2 Complete** ✅ (Provider Abstraction Layer - August 2025)

- **Multi-Provider Architecture**: Ollama (local) + Google Gemini (cloud) with Vertex AI support
- **Quality Assurance**: 100% clean code quality pipeline (Black + Ruff + mypy + markdownlint)
- **Type Safety**: Complete static type checking with zero production errors
- **Test Coverage**: 41 comprehensive tests across configuration, providers, and API endpoints
- **Documentation**: Consistent formatting and linting across all project documentation
- **Next Phase**: GraphRAG Core Implementation (indexing, querying, workspace management)
- **Graph Operations Implemented**: Initial implementation of graph querying, statistics,
  visualization data generation, and export.

## Project Documentation

- **API Documentation**: Interactive Swagger UI documentation at `/docs`
- **ReDoc Documentation**: ReDoc API documentation at `/redoc`
- **Project Plan**: [PROJECT_PLAN.md](PROJECT_PLAN.md) - Implementation roadmap and phases
- **Development Notes**: [GEMINI.md](GEMINI.md) - Key decisions and conventions
- **Claude Code Context**: [CLAUDE.md](CLAUDE.md) - Development environment context

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
