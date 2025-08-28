# GraphRAG API Service - Project Plan

## Project Overview

Building a comprehensive FastAPI-based service for Microsoft GraphRAG with multi-provider LLM support (local Ollama + Google Cloud Gemini).

## Architecture Decisions

### Multi-Provider LLM Support

**Decision Date**: 2025-08-28  
**Decision**: Implement dual LLM provider support for flexibility and different deployment scenarios.

**Providers**:

- **Ollama (Local)**: Gemma3:4b model for privacy-focused, cost-effective local deployments
- **Google Cloud Gemini**: gemini-2.5-flash/pro for cloud-based, high-performance deployments

**Benefits**:

- Development flexibility (local vs cloud)
- Cost optimization options
- Privacy control (local processing)
- Scalability options (cloud resources)

### Implementation Strategy

**Approach**: Small incremental steps with validation and testing at each phase.

**Validation Requirements**:

- Configuration changes must pass pytest validation
- Each provider integration tested independently
- API endpoints validated with both providers
- Comprehensive error handling and logging

## Implementation Phases

### Phase 1: Foundation & Configuration ⏳

**Status**: In Progress  
**Goal**: Establish multi-provider configuration architecture

#### Step 1.1: Update Documentation

- [x] Create PROJECT_PLAN.md
- [x] Update README.md with multi-provider architecture
- [x] Update CLAUDE.md with new context
- [x] Update GEMINI.md with architectural decisions

#### Step 1.2: Configuration Extension ✅ **COMPLETED 2025-08-28**

- [x] Extend config.py for multi-provider support
- [x] Add LLM provider enumeration (LLMProvider enum)
- [x] Add Ollama-specific configuration (base_url, llm_model, embedding_model)
- [x] Add Google Gemini-specific configuration (api_key, project_id, models)
- [x] Create configuration validation tests (11 new tests, all passing)
- [x] Update API endpoints with provider information (/info, /graphrag/status)
- [x] Implement modern Pydantic v2 field validators
- [x] Add helper methods (is_ollama_provider, get_provider_info)

#### Step 1.3: Dependencies

- [ ] Add required dependencies to pyproject.toml
- [ ] Add ollama Python client
- [ ] Add google-cloud-aiplatform
- [ ] Add google-generativeai
- [ ] Update poetry.lock

### Phase 2: Provider Abstraction Layer 📋

**Status**: Planned  
**Goal**: Create unified LLM interface supporting both providers

#### Step 2.1: Abstract Base Classes

- [ ] Create GraphRAGLLM abstract base class
- [ ] Define common interface methods
- [ ] Create provider factory pattern
- [ ] Add provider detection logic

#### Step 2.2: Ollama Integration

- [ ] Implement OllamaGraphRAGLLM class
- [ ] Direct API integration (no proxy)
- [ ] Gemma3:4b model configuration
- [ ] Local embeddings (nomic-embed-text)
- [ ] Connection validation and health checks

#### Step 2.3: Google Gemini Integration

- [ ] Implement GeminiGraphRAGLLM class
- [ ] Vertex AI API integration
- [ ] Authentication handling
- [ ] Model selection (gemini-2.5-flash/pro)
- [ ] Rate limiting and error handling

### Phase 3: GraphRAG Core Implementation 📋

**Status**: Planned  
**Goal**: Implement actual GraphRAG functionality

#### Step 3.1: Workspace Management

- [ ] Create GraphRAG workspace structure
- [ ] Multi-project support
- [ ] Configuration file generation
- [ ] Data directory management

#### Step 3.2: Indexing Implementation

- [ ] Background task processing
- [ ] Progress tracking and logging
- [ ] Provider-agnostic indexing pipeline
- [ ] Error handling and recovery

#### Step 3.3: Query Implementation

- [ ] Global search implementation
- [ ] Local search implementation
- [ ] Community-level search
- [ ] Response formatting and caching

### Phase 4: API Enhancement & Testing 📋

**Status**: Planned  
**Goal**: Comprehensive testing and API refinement

#### Step 4.1: Enhanced Endpoints

- [ ] Provider switching endpoints
- [ ] Health check enhancements
- [ ] Status reporting improvements
- [ ] Configuration validation endpoints

#### Step 4.2: Comprehensive Testing

- [ ] Unit tests for each provider
- [ ] Integration tests with mock services
- [ ] End-to-end API testing
- [ ] Performance benchmarking

#### Step 4.3: Error Handling & Monitoring

- [ ] Comprehensive error handling
- [ ] Structured logging
- [ ] Metrics collection
- [ ] Health monitoring

### Phase 5: Production Readiness 📋

**Status**: Planned  
**Goal**: Production deployment preparation

#### Step 5.1: Security & Authentication

- [ ] API key management
- [ ] Rate limiting
- [ ] Input validation
- [ ] Security headers

#### Step 5.2: Performance Optimization

- [ ] Response caching
- [ ] Connection pooling
- [ ] Resource management
- [ ] Load testing

#### Step 5.3: Documentation & Deployment

- [ ] API documentation
- [ ] Deployment guides
- [ ] Configuration examples
- [ ] Troubleshooting guides

## Current Status

- **Phase**: Phase 1 (Foundation & Configuration)
- **Current Step**: Step 1.1 (Update Documentation)
- **Next Milestone**: Complete configuration extension and validation

## Testing Strategy

Every step must include:

1. **Unit Tests**: Component-level validation
2. **Integration Tests**: Provider connectivity
3. **API Tests**: Endpoint functionality
4. **Configuration Tests**: Settings validation

## Quality Gates

Before proceeding to next phase:

- [ ] All tests pass (100% success rate)
- [ ] Code formatting (Black) passes
- [ ] Linting (Ruff) passes  
- [ ] Documentation updated
- [ ] Manual validation completed

## Risk Mitigation

- **Provider Availability**: Graceful fallback handling
- **API Changes**: Version pinning and compatibility checks
- **Performance**: Resource monitoring and optimization
- **Security**: Input validation and secure credential handling
