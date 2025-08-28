# CLAUDE.md

## Project Context for Claude Code

### Project Overview

GraphRAG API Service - A FastAPI-based API for Microsoft's GraphRAG library with multi-provider LLM support (Ollama + Google Gemini), providing flexible graph-based retrieval-augmented generation capabilities for both local and cloud deployments.

### Development Environment

* **Python Version**: 3.12 (Poetry managed virtual environment)
* **Package Manager**: Poetry
* **Framework**: FastAPI with Uvicorn ASGI server
* **Testing**: pytest framework
* **Code Quality**: Black (formatter) + Ruff (linter) + mypy (type checker)

### Key Commands

```bash
# Development server
poetry run uvicorn src.graphrag_api_service.main:app --reload

# Testing
poetry run pytest tests/ -v

# Code formatting
poetry run black src/ tests/

# Code linting  
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/graphrag_api_service --show-error-codes

# Full quality check (run all tools)
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes

# Install dependencies
poetry install

# Add new dependency
poetry add <package-name>

# Add dev dependency
poetry add --group dev <package-name>
```

### Project Structure

```bash
src/graphrag_api_service/    # Main application package
├── main.py                  # FastAPI application with GraphRAG endpoints
├── config.py                # Pydantic settings configuration
├── logging_config.py        # Logging setup
└── providers/              # LLM provider abstraction layer
    ├── __init__.py         # Provider package exports
    ├── base.py             # GraphRAGLLM abstract base class
    ├── factory.py          # LLMProviderFactory for dynamic provider creation
    ├── ollama_provider.py  # Ollama local LLM provider implementation
    ├── gemini_provider.py  # Google Gemini cloud LLM provider implementation
    └── registry.py         # Provider registration for automatic startup

tests/                       # Test suite
├── test_main.py            # API endpoint tests
├── test_config.py          # Configuration tests
├── test_logging_config.py  # Logging tests
├── test_providers_base.py  # Provider abstraction layer tests
├── test_ollama_provider.py # Ollama provider implementation tests
└── test_gemini_provider.py # Google Gemini provider implementation tests
```

### API Endpoints

* **Health**: `/`, `/health`, `/info`
* **GraphRAG**: `/graphrag/query`, `/graphrag/index`, `/graphrag/status`
* **Documentation**: `/docs`, `/redoc`

### Configuration

Environment variables (via `.env` file):

**Core Application:**

* `GRAPHRAG_LLM_PROVIDER`: ollama|google_gemini (provider selection)
* `DEBUG`: Debug mode (true/false)
* `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
* `PORT`: Server port (default: 8001, changed from 8000 to avoid Docker conflicts)

**GraphRAG Settings:**

* `GRAPHRAG_DATA_PATH`: Path to GraphRAG data directory
* `GRAPHRAG_CONFIG_PATH`: Path to GraphRAG configuration file

**Ollama Configuration (Local):**

* `OLLAMA_BASE_URL`: Ollama server URL (default: <http://localhost:11434>)
* `OLLAMA_LLM_MODEL`: LLM model name (default: gemma:4b)
* `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: nomic-embed-text)

**Google Gemini Configuration (Cloud):**

* `GOOGLE_API_KEY`: Google Cloud API key for Gemini
* `GOOGLE_PROJECT_ID`: Google Cloud project ID
* `GEMINI_MODEL`: Gemini model version (default: gemini-2.5-flash)

### Development Notes

* **Current Status**: Dual provider system fully operational with comprehensive testing
* **Architecture**: Complete GraphRAGLLM abstraction with both Ollama and Google Gemini providers
* **Next Steps**: Implement Phase 3 GraphRAG Core Integration with Microsoft GraphRAG library
* **Code Standards**: All code must pass Black formatting and Ruff linting (see coding standards below)
* **Testing**: Maintain 100% test pass rate before committing, test each provider independently
* **Git**: Use semantic commit messages, main branch for development
* **Implementation**: Small incremental steps with validation at each phase
* **Documentation**: Always update PROJECT_PLAN.md when completing tasks or steps

### Development Quality Standards

**Code Quality Pipeline:**
1. **Black**: Auto-format code style and structure
2. **Ruff**: Lint for bugs, style issues, and code improvements  
3. **mypy**: Static type checking for runtime error prevention
4. **pytest**: Comprehensive test coverage validation

**Quick Quality Check:**
```bash
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes
```

### Coding Standards to Prevent Issues

**Import Organization (Ruff I001):**

```python
# Standard library imports first
import os
import sys
from pathlib import Path

# Third-party imports second
import pytest
from unittest.mock import patch

# Local imports last
from src.graphrag_api_service.config import Settings
```

**Black Formatting Rules:**

* Line length: 100 characters (configured in pyproject.toml)
* Use double quotes for strings
* Trailing commas in multiline structures
* Apply formatting before committing: `poetry run black src/ tests/`

**Ruff Configuration Applied:**

* Import sorting (I)
* PEP 8 style (E, W)
* Pyflakes (F)  
* Bugbear (B)
* Comprehensions (C4)
* Pyupgrade (UP)

**mypy Configuration Applied:**

* Static type checking for Python 3.12
* Return type validation
* Pydantic model configuration validation
* External library type stub management
* Unused type ignore detection

### Common Issues & Solutions

* **Test Failures**: Run `poetry run pytest tests/ -v` to identify issues
* **Formatting Issues**: Run `poetry run black src/ tests/` to auto-format
* **Linting Issues**: Run `poetry run ruff check --fix src/ tests/` to auto-fix
* **Type Errors**: Run `poetry run mypy src/graphrag_api_service --show-error-codes` to detect type issues
* **Pydantic Config Issues**: Use `SettingsConfigDict` for `BaseSettings` classes, not `ConfigDict`
* **Return Type Mismatches**: Ensure function return types match actual returned values
* **Dependency Issues**: Run `poetry install` to sync dependencies

### Important Files

* `pyproject.toml`: Poetry configuration, dependencies, tool settings
* `src/graphrag_api_service/main.py`: Main FastAPI application
* `src/graphrag_api_service/config.py`: Settings and environment configuration
* `tests/`: Comprehensive test suite covering all functionality
