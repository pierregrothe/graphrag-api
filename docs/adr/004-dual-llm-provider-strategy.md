# ADR-004: Dual LLM Provider Strategy (Ollama + Gemini)

## Status

Accepted

## Date

2025-09-02

## Context

The application needs to support both local development and cloud production with different LLM providers:

- Local development on Windows with limited resources
- Production deployment on Google Cloud
- Cost optimization for small-scale usage
- Easy switching between providers

## Decision

Implement a dual-provider strategy:

- **Ollama** with small models (Gemma 2B) for local development
- **Google Gemini** (Flash model) for production

## Consequences

### Positive

- **Cost Effective**: Free local development with Ollama
- **Performance**: Gemini Flash is fast and affordable for production
- **Flexibility**: Easy to switch providers via environment variable
- **Consistency**: Same API interface for both providers
- **Local First**: Can develop without internet or API keys

### Negative

- **Model Differences**: Different capabilities between Gemma 2B and Gemini Flash
- **Maintenance**: Need to maintain two provider implementations
- **Testing**: Need to test with both providers

### Mitigation

- Abstract provider interface with common `GraphRAGLLM` base class
- Use factory pattern for provider instantiation
- Document model-specific limitations
- Provide configuration examples for both scenarios

## Implementation

- Created provider abstraction in `providers/base.py`
- Implemented `OllamaProvider` and `GeminiProvider`
- Used `LLM_PROVIDER` environment variable for selection
- Configured Docker Compose to include Ollama for local dev
- Documented configuration for both providers
