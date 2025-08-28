# CLAUDE.md

## Project Context for Claude Code

### Project Overview

GraphRAG API Service - A FastAPI-based API for Microsoft's GraphRAG library with multi-provider LLM support (Ollama + Google Gemini), providing flexible graph-based retrieval-augmented generation capabilities for both local and cloud deployments.

### Development Environment

- **Python Version**: 3.12 (Poetry managed virtual environment)
- **Package Manager**: Poetry
- **Framework**: FastAPI with Uvicorn ASGI server
- **Testing**: pytest framework
- **Code Quality**: Black (formatter) + Ruff (linter)

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

# Install dependencies
poetry install

# Add new dependency
poetry add <package-name>

# Add dev dependency
poetry add --group dev <package-name>
```

### Project Structure

```
src/graphrag_api_service/    # Main application package
├── main.py                  # FastAPI application with GraphRAG endpoints
├── config.py                # Pydantic settings configuration
└── logging_config.py        # Logging setup

tests/                       # Test suite
├── test_main.py            # API endpoint tests
├── test_config.py          # Configuration tests
└── test_logging_config.py  # Logging tests
```

### API Endpoints

- **Health**: `/`, `/health`, `/info`
- **GraphRAG**: `/graphrag/query`, `/graphrag/index`, `/graphrag/status`
- **Documentation**: `/docs`, `/redoc`

### Configuration

Environment variables (via `.env` file):

**Core Application:**

- `GRAPHRAG_LLM_PROVIDER`: ollama|google_gemini (provider selection)
- `DEBUG`: Debug mode (true/false)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `PORT`: Server port (default: 8000)

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

### Development Notes

- **Current Status**: Multi-provider architecture designed, updating documentation
- **Architecture**: Dual LLM provider support (Ollama local + Google Gemini cloud)
- **Next Steps**: Implement configuration extension and provider abstraction layer
- **Code Standards**: All code must pass Black formatting and Ruff linting
- **Testing**: Maintain 100% test pass rate before committing, test each provider independently
- **Git**: Use semantic commit messages, main branch for development
- **Implementation**: Small incremental steps with validation at each phase

### Common Issues & Solutions

- **Test Failures**: Run `poetry run pytest tests/ -v` to identify issues
- **Formatting Issues**: Run `poetry run black src/ tests/` to auto-format
- **Linting Issues**: Run `poetry run ruff check --fix src/ tests/` to auto-fix
- **Dependency Issues**: Run `poetry install` to sync dependencies

### Important Files

- `pyproject.toml`: Poetry configuration, dependencies, tool settings
- `src/graphrag_api_service/main.py`: Main FastAPI application
- `src/graphrag_api_service/config.py`: Settings and environment configuration
- `tests/`: Comprehensive test suite covering all functionality
