# CLAUDE.md

## Project Context for Claude Code

### Project Overview

GraphRAG API Service - A FastAPI-based API for Microsoft's GraphRAG library with multi-provider LLM support
(Ollama + Google Gemini), providing flexible graph-based retrieval-augmented generation capabilities for both
local and cloud deployments.

### Development Environment

- **Python Version**: 3.12 (Poetry managed virtual environment)
- **Package Manager**: Poetry
- **Framework**: FastAPI with Uvicorn ASGI server
- **Testing**: pytest framework
- **Code Quality**: Black (formatter) + Ruff (linter) + mypy (type checker)

### Key Commands

```bash
# Development server
poetry run uvicorn src.graphrag_api_service.main:app --reload

# Testing - Basic test suite
poetry run pytest tests/ -v

# Testing - Provider validation (tests configured provider from .env)
poetry run pytest tests/test_provider.py -v

# Code formatting
poetry run black src/ tests/

# Code linting
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/graphrag_api_service --show-error-codes

# Markdown linting and formatting
npm run lint:md
npm run fix:md

# Full quality check (run all tools)
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes && npm run check:md

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
├── conftest.py              # Pytest fixtures and configuration
├── test_main.py             # API endpoint tests
├── test_config.py           # Configuration tests
├── test_logging_config.py   # Logging tests
├── test_providers_base.py   # Provider abstraction layer tests
├── test_provider.py         # Unified provider validation tests (unit + integration)
└── test_workspace.py        # Workspace management tests (15 comprehensive tests)

src/graphrag_api_service/
├── workspace/               # Workspace management module
    ├── __init__.py         # Module exports
    ├── models.py           # Workspace data models (Workspace, WorkspaceConfig, etc.)
    └── manager.py          # WorkspaceManager implementation
```

### API Endpoints

- **Health**: `/`, `/health`, `/info`
- **GraphRAG**: `/api/query`, `/api/index`, `/api/status`
- **Workspace Management**: `/api/workspaces` (CRUD operations for multi-project support)
- **Documentation**: `/docs`, `/redoc`

### Configuration

Environment variables (via `.env` file):

**Core Application:**

- `GRAPHRAG_LLM_PROVIDER`: ollama|google_gemini (provider selection)
- `DEBUG`: Debug mode (true/false)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `PORT`: Server port (default: 8001, changed from 8000 to avoid Docker conflicts)

**GraphRAG Settings:**

- `GRAPHRAG_DATA_PATH`: Path to GraphRAG data directory
- `GRAPHRAG_CONFIG_PATH`: Path to GraphRAG configuration file

**Ollama Configuration (Local):**

- `OLLAMA_BASE_URL`: Ollama server URL (default: <http://localhost:11434>)
- `OLLAMA_LLM_MODEL`: LLM model name (default: gemma:4b)
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: nomic-embed-text)

**Google Gemini Configuration (Cloud):**

- `GOOGLE_API_KEY`: Google Cloud API key for Gemini
- `GOOGLE_PROJECT_ID`: Google Cloud project ID
- `GEMINI_MODEL`: Gemini model version (default: gemini-2.5-flash)

### Provider Testing

**Unified Testing Approach:**

1. **Provider Validation Tests**: Comprehensive pytest-based provider testing

    ```bash
    poetry run pytest tests/test_provider.py -v  # Provider validation
    poetry run pytest tests/test_provider.py -m integration -v  # LLM connectivity tests
    ```

    - Validates configuration completeness
    - Tests implementation patterns (no LLM access required)
    - Validates LLM connectivity (health, text generation, embeddings)
    - Uses proper pytest fixtures and integration markers

2. **Complete Unit Test Suite**: Full pytest coverage

    ```bash
    poetry run pytest tests/ -v  # All tests
    poetry run pytest -m integration -v  # Integration tests only
    ```

**Provider Setup Requirements:**

- **Ollama**: Requires Ollama server running at `http://localhost:11434` with models:
    - `gemma3:4b` (LLM model)
    - `nomic-embed-text` (embedding model)

- **Gemini**: Requires environment variables in .env:
    - `GOOGLE_API_KEY`: Google Cloud API key
    - `GOOGLE_PROJECT_ID`: Google Cloud project ID

**Testing Features:**

- Automatic provider detection from .env configuration
- LLM-free implementation pattern validation
- Real connectivity testing with detailed performance metrics
- Graceful error handling and informative failure messages

### Workspace Management

**Multi-Project Support**: Complete workspace management system for GraphRAG projects

**Key Features**:

- **Workspace Creation**: Individual isolated environments with custom configurations
- **Data Directory Management**: Automatic directory structure creation and management
- **Configuration Generation**: Provider-specific GraphRAG settings.yaml files
- **CRUD Operations**: Full REST API for workspace lifecycle management
- **Persistence**: JSON-based workspace index with UUID identification

**API Endpoints**:

```bash
# Create workspace
POST /api/workspaces
{
  "name": "project-name",
  "description": "Project description",
  "data_path": "/path/to/source/data",
  "chunk_size": 1200,  # optional
  "max_entities": 1000  # optional
}

# List all workspaces
GET /api/workspaces

# Get specific workspace
GET /api/workspaces/{workspace_id}

# Update workspace config
PUT /api/workspaces/{workspace_id}

# Delete workspace
DELETE /api/workspaces/{workspace_id}?remove_files=false

# Get workspace GraphRAG config
GET /api/workspaces/{workspace_id}/config
```

### Development Notes

- **Current Status**: Phase 4.1 complete - Full workspace management system operational
- **Architecture**: Multi-project GraphRAG with workspace isolation and provider abstraction
- **Next Steps**: Implement Phase 4.2 - Background indexing with progress tracking
- **Code Standards**: All code must pass Black formatting and Ruff linting (see coding standards below)
- **Testing**: 66 comprehensive tests covering all functionality
- **Git**: Use semantic commit messages, main branch for development
- **Implementation**: Small incremental steps with validation at each phase
- **Documentation**: Always update PROJECT_PLAN.md when completing tasks or steps

### Development Quality Standards

**Code Quality Pipeline:**

1. **Black**: Auto-format code style and structure
2. **Ruff**: Lint for bugs, style issues, and code improvements
3. **mypy**: Static type checking for runtime error prevention
4. **markdownlint**: Lint markdown files for consistency and formatting
5. **pytest**: Comprehensive test coverage validation

**Quick Quality Check:**

```bash
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes && npm run check:md
```

**Mermaid Diagram Validation:**

Since there are no reliable Python tools for Mermaid validation, use GitHub as the validation platform:

1. **Local Development**: Ensure Mermaid syntax follows standard patterns (avoid new @{ shape: } syntax)
2. **Commit & Push**: Push changes to GitHub repository
3. **GitHub Validation**: Check diagram rendering at [README.md](https://github.com/pierregrothe/graphrag-api/blob/main/README.md)
4. **Visual Verification**: Confirm all diagrams render correctly without parse errors
5. **Compatibility**: Use universally supported shapes: `()`, `{}`, `[]`, `(())`, `[()]`, `{{}}`, `[//]`, `[\\]`

### Coding Standards to Prevent Issues

#### CRITICAL: NO EMOJIS IN CODE

**⚠️ NEVER use emojis in Python code, strings, or any code output that will be executed.**

- Emojis cause `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows
- This includes checkmarks (✅), warnings (⚠️), or any Unicode symbols in Python strings
- Use text alternatives: "SUCCESS", "ERROR", "WARNING", "[PASS]", "[FAIL]"
- Example that FAILS: `print("✅ Config loaded")`
- Example that WORKS: `print("Config loaded successfully")`

#### Import Organization and Code Style

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

- Line length: 100 characters (configured in pyproject.toml)
- Use double quotes for strings
- Trailing commas in multiline structures
- Apply formatting before committing: `poetry run black src/ tests/`

**Ruff Configuration Applied:**

- Import sorting (I)
- PEP 8 style (E, W)
- Pyflakes (F)
- Bugbear (B)
- Comprehensions (C4)
- Pyupgrade (UP)

**mypy Configuration Applied:**

- Static type checking for Python 3.12
- Return type validation
- Pydantic model configuration validation
- External library type stub management
- Unused type ignore detection

### Common Issues & Solutions

- **Test Failures**: Run `poetry run pytest tests/ -v` to identify issues
- **Formatting Issues**: Run `poetry run black src/ tests/` to auto-format
- **Linting Issues**: Run `poetry run ruff check --fix src/ tests/` to auto-fix
- **Type Errors**: Run `poetry run mypy src/graphrag_api_service --show-error-codes` to detect type issues
- **Markdown Issues**: Run `npm run fix:md` to auto-fix markdown formatting and linting issues
- **Pydantic Config Issues**: Use `SettingsConfigDict` for `BaseSettings` classes, not `ConfigDict`
- **Return Type Mismatches**: Ensure function return types match actual returned values
- **Dependency Issues**: Run `poetry install` to sync dependencies

### Important Files

- `pyproject.toml`: Poetry configuration, dependencies, tool settings
- `src/graphrag_api_service/main.py`: Main FastAPI application
- `src/graphrag_api_service/config.py`: Settings and environment configuration
- `tests/`: Comprehensive test suite covering all functionality
