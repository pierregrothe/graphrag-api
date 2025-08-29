# GEMINI.md

## Project Overview

This project aims to create a comprehensive FastAPI-based API service for Microsoft GraphRAG with multi-provider
LLM support. The project was inspired by the backend of `severian42/GraphRAG-Local-UI`, but implements a fresh
architecture focusing on flexibility and deployment options.

## Key Architectural Decisions

### Multi-Provider LLM Support (2025-08-28)

**Decision**: Implement dual LLM provider architecture supporting both local and cloud deployments.

**Providers**:

- **Ollama (Local)**: Gemma3:4b model for privacy-focused, cost-effective local deployments
- Direct integration without proxy layers
- Local embeddings with nomic-embed-text
- Complete data privacy and no external API costs
- **Google Cloud Gemini**: gemini-2.5-flash/pro for cloud-based, high-performance deployments
- Latest Gemini models with multimodal capabilities
- Enterprise-grade reliability and scaling
- Integrated with Vertex AI platform

**Implementation Strategy**: Small incremental steps with comprehensive testing and validation at each phase.

### Core Technical Decisions

- **Dependency Management:** Poetry for environment and dependency management
- **Python Version:** Python 3.12 specifically for latest language features

### API Endpoints

- **Health**: `/`, `/health`, `/info`
- **GraphRAG**: `/graphrag/query`, `/graphrag/index`, `/graphrag/status`
- **Documentation**: `/docs`, `/redoc`

### Configuration

```bash
src/graphrag_api_service/ # Main application package
main.py # FastAPI application with GraphRAG endpoints
config.py # Pydantic settings configuration
logging_config.py # Logging setup
providers/ # LLM provider abstraction layer
__init__.py # Provider package exports
base.py # GraphRAGLLM abstract base class
factory.py # LLMProviderFactory for dynamic provider creation
ollama_provider.py # Ollama local LLM provider implementation
gemini_provider.py # Google Gemini cloud LLM provider implementation
registry.py # Provider registration for automatic startup

tests/ # Test suite
test_main.py # API endpoint tests
test_config.py # Configuration tests
test_logging_config.py # Logging tests
test_providers_base.py # Provider abstraction layer tests
test_ollama_provider.py # Ollama provider implementation tests
test_gemini_provider.py # Google Gemini provider implementation tests
```

- **Code Quality:** Black formatter + Ruff linter with 100% test coverage requirement
- **Testing Strategy:** pytest framework with provider-specific test suites
- **Version Control:** GitHub repository with semantic commit messages

## Building and Running

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

## Development Conventions

### Code Standards

- **Virtual Environment:** Poetry automatically manages the virtual environment
- **Coding Style:** PEP 8 style guide with Black formatter (100 char line length)
- **Linting:** Ruff with comprehensive rule set (E, W, F, I, B, C4, UP)
- **Testing:** pytest with 100% test pass requirement before commits
- **Documentation:** All functions and classes must have Google-style docstrings

### Implementation Approach

- **Incremental Development:** Small steps with validation at each phase
- **Provider Testing:** Each LLM provider tested independently
- **Configuration Validation:** All settings validated with pytest
- **Error Handling:** Comprehensive error handling with structured logging
- **Documentation Tracking:** Always update PROJECT_PLAN.md when completing tasks or steps

### Quality Gates

Before proceeding to next development phase:

- All tests pass (100% success rate)
- Code formatting passes (Black)
- Linting passes (Ruff)
- Static type checking passes (mypy)
- Documentation updated (including PROJECT_PLAN.md)
- Manual validation completed

### Coding Standards to Prevent Quality Issues

#### CRITICAL: NO EMOJIS IN CODE

**[WARNING] NEVER use emojis in Python code, strings, or any code output that will be executed.**

- Emojis cause `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows
- This includes checkmarks ([x]), warnings ([WARNING]), or any Unicode symbols in Python strings
- Use text alternatives: "SUCCESS", "ERROR", "WARNING", "[PASS]", "[FAIL]"
- Example that FAILS: `print("[x] Config loaded")`
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

**Black Formatting Guidelines:**

- Line length: 100 characters (configured in pyproject.toml)
- Use double quotes for strings consistently
- Include trailing commas in multiline structures
- Apply before committing: `poetry run black src/ tests/`

**Ruff Rules Applied:**

- Import sorting (I) - prevents I001 errors
- PEP 8 compliance (E, W) - style consistency
- Pyflakes (F) - unused import detection
- Bugbear (B) - common Python gotchas
- Comprehensions (C4) - list/dict comprehension improvements
- Pyupgrade (UP) - modern Python syntax

**mypy Type Checking:**

- Validates return type annotations match actual return values
- Detects Pydantic configuration issues (ConfigDict vs SettingsConfigDict)
- Identifies unused type ignore comments and unreachable code
- Ensures type consistency across function signatures
- Prevents runtime type errors through static analysis
- Catches all type issues that caused development problems

**Markdown Quality Control:**

- markdownlint-cli v0.45.0 for consistent markdown standards
- prettier v3.6.2 with 4-space indentation matching markdownlint
- Automated formatting and linting for all documentation files
- npm scripts for markdown quality control (lint:md, fix:md, check:md)
- Integration with development workflow for documentation quality

**Complete Quality Pipeline:**

```bash
# Python code quality (all checks must pass)
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes

# Markdown documentation quality
npm run check:md

# Combined quality verification
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/graphrag_api_service --show-error-codes && npm run check:md
```

**Mermaid Diagram Validation Workflow:**

No Python tools exist for reliable Mermaid validation. Use GitHub as the validation platform:

1. **Development**: Use standard Mermaid syntax (avoid bleeding-edge features)
2. **Local Check**: Ensure markdown passes `npm run check:md`
3. **Commit & Push**: Push to GitHub repository for rendering validation
4. **GitHub Check**: Verify diagrams at [README.md](https://github.com/pierregrothe/graphrag-api/blob/main/README.md)
5. **Visual Confirmation**: All diagrams render without parse errors or missing shapes
6. **Shape Compatibility**: Stick to universal shapes: `()`, `{}`, `[]`, `(())`, `[()]`, `{{}}`, `[//]`, `[\\]`

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
