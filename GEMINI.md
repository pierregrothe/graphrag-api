# GEMINI.md

## Project Overview

This project aims to create a comprehensive FastAPI-based API service for Microsoft GraphRAG with multi-provider LLM support. The project was inspired by the backend of `severian42/GraphRAG-Local-UI`, but implements a fresh architecture focusing on flexibility and deployment options.

## Key Architectural Decisions

### Multi-Provider LLM Support (2025-08-28)

**Decision**: Implement dual LLM provider architecture supporting both local and cloud deployments.

**Providers**:

* **Ollama (Local)**: Gemma3:4b model for privacy-focused, cost-effective local deployments
  * Direct integration without proxy layers
  * Local embeddings with nomic-embed-text
  * Complete data privacy and no external API costs
* **Google Cloud Gemini**: gemini-2.5-flash/pro for cloud-based, high-performance deployments
  * Latest Gemini models with multimodal capabilities
  * Enterprise-grade reliability and scaling
  * Integrated with Vertex AI platform

**Implementation Strategy**: Small incremental steps with comprehensive testing and validation at each phase.

### Core Technical Decisions

* **Dependency Management:** Poetry for environment and dependency management
* **Python Version:** Python 3.12 specifically for latest language features
* **Project Structure:** Standard Python project with `src` directory organization
* **Code Quality:** Black formatter + Ruff linter with 100% test coverage requirement
* **Testing Strategy:** pytest framework with provider-specific test suites
* **Version Control:** GitHub repository with semantic commit messages

## Building and Running

### Development Setup

1. **Install dependencies:**

    ```bash
    poetry install
    ```

2. **Configure LLM Provider:**

   **For Ollama (Local Development):**

   ```bash
   export GRAPHRAG_LLM_PROVIDER=ollama
   export OLLAMA_LLM_MODEL=gemma:4b
   export OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```

   **For Google Gemini (Cloud Deployment):**

   ```bash
   export GRAPHRAG_LLM_PROVIDER=google_gemini  
   export GOOGLE_API_KEY=your_api_key
   export GOOGLE_PROJECT_ID=your_project_id
   ```

3. **Run the FastAPI application:**

    ```bash
    poetry run uvicorn src.graphrag_api_service.main:app --reload
    ```

## Development Conventions

### Code Standards

* **Virtual Environment:** Poetry automatically manages the virtual environment
* **Coding Style:** PEP 8 style guide with Black formatter (100 char line length)
* **Linting:** Ruff with comprehensive rule set (E, W, F, I, B, C4, UP)
* **Testing:** pytest with 100% test pass requirement before commits
* **Documentation:** All functions and classes must have Google-style docstrings

### Implementation Approach

* **Incremental Development:** Small steps with validation at each phase
* **Provider Testing:** Each LLM provider tested independently
* **Configuration Validation:** All settings validated with pytest
* **Error Handling:** Comprehensive error handling with structured logging

### Quality Gates

Before proceeding to next development phase:

* All tests pass (100% success rate)
* Code formatting passes (Black)
* Linting passes (Ruff)
* Documentation updated
* Manual validation completed
