# GraphRAG API Service Test Suite

## Overview
The test suite is organized into three main categories following best practices for test organization and maintainability.

## Test Structure

```
tests/
├── unit/                   # Unit tests for individual modules
├── integration/            # Integration tests for API endpoints
├── performance/           # Performance and load tests
├── fixtures/              # Shared test fixtures and utilities
└── archived/              # Old/deprecated tests (for reference)
```

## Test Categories

### Unit Tests (`tests/unit/`)
Tests individual modules in isolation with mocked dependencies.

- **test_config.py** - Configuration and settings validation
- **test_workspace.py** - Workspace management operations
- **test_providers.py** - LLM provider implementations
- **test_graph.py** - Graph operations
- **test_indexing.py** - Indexing operations
- **test_logging.py** - Logging configuration
- **test_middleware.py** - Middleware functionality
- **test_system.py** - System operations

### Integration Tests (`tests/integration/`)
Tests API endpoints and cross-module interactions.

- **test_api_endpoints.py** - REST API endpoint testing
- **test_graphql_endpoints.py** - GraphQL API testing

### Performance Tests (`tests/performance/`)
Tests system performance and scalability.

- **test_load.py** - Load testing
- **test_optimization.py** - Performance optimization testing

## Running Tests

### Run All Tests
```bash
poetry run pytest tests/
```

### Run Specific Category
```bash
# Unit tests only
poetry run pytest tests/unit/

# Integration tests only
poetry run pytest tests/integration/

# Performance tests only
poetry run pytest tests/performance/
```

### Run Specific Test File
```bash
poetry run pytest tests/unit/test_config.py
```

### Run with Coverage
```bash
poetry run pytest tests/ --cov=src/graphrag_api_service --cov-report=html
```

### Run with Verbose Output
```bash
poetry run pytest tests/ -v
```

## Test Naming Convention

### File Names
Format: `test_<module>_<feature>.py`
- Examples: `test_workspace.py`, `test_api_endpoints.py`

### Test Classes
- Unit: `Test<Module><Feature>`
- Integration: `Test<Feature>Integration`
- Performance: `Test<Feature>Performance`

### Test Methods
Format: `test_<action>_<condition>_<expected_result>`
- Examples:
  - `test_create_workspace_valid_data_returns_success`
  - `test_query_invalid_workspace_returns_404`
  - `test_authenticate_expired_token_raises_error`

## Coverage Matrix

| Module | Unit Tests | Integration Tests | Performance Tests |
|--------|------------|------------------|-------------------|
| Config | ✅ | ✅ | - |
| Workspace | ✅ | ✅ | - |
| Providers | ✅ | ✅ | - |
| Graph | ✅ | ✅ | - |
| Indexing | ✅ | ✅ | - |
| Logging | ✅ | - | - |
| Middleware | ✅ | ✅ | - |
| System | ✅ | ✅ | - |
| Performance | - | - | ✅ |

Legend: ✅ Complete | - Not Required

## Test Fixtures

Shared fixtures are located in `tests/fixtures/`:

### Client Fixtures (`clients.py`)
- `test_client` - Synchronous FastAPI test client
- `async_test_client` - Asynchronous test client
- `sync_test_client` - External HTTP client

### Data Fixtures (`data.py`)
- `test_data_path` - Temporary directory with sample files
- `sample_workspace_config` - Sample workspace configuration
- `sample_query_request` - Sample GraphRAG query
- `sample_graph_data` - Sample graph entities and relationships

### Mock Fixtures (`mocks.py`)
- `mock_workspace_manager` - Mocked workspace manager
- `mock_llm_provider` - Mocked LLM provider
- `mock_indexing_manager` - Mocked indexing manager

## Writing New Tests

### Unit Test Template
```python
# tests/unit/test_<module>.py
"""
Module: <Module Name>
Tests: <What this tests>
Coverage: <What scenarios are covered>
Dependencies: <External dependencies if any>
"""

import pytest
from src.graphrag_api_service.<module> import <Class>

class Test<Module><Feature>:
    """Test <feature> functionality."""

    def test_<action>_<condition>_<expected>(self):
        """Test that <action> with <condition> results in <expected>."""
        # Arrange
        # Act
        # Assert
```

### Integration Test Template
```python
# tests/integration/test_<feature>.py
"""
Module: <Feature> Integration
Tests: <Integration scenarios>
Coverage: <API endpoints or workflows tested>
Dependencies: FastAPI test client
"""

import pytest
from tests.fixtures.clients import async_test_client

class Test<Feature>Integration:
    """Test <feature> integration."""

    @pytest.mark.asyncio
    async def test_<workflow>_<scenario>(self, async_test_client):
        """Test <workflow> in <scenario>."""
        # Arrange
        # Act
        # Assert
```

## CI/CD Integration

Tests are automatically run in CI/CD pipeline:
1. Pre-commit hooks run linting and formatting
2. GitHub Actions run full test suite on push
3. Coverage reports are generated and tracked

## Maintenance

### Adding New Tests
1. Choose appropriate category (unit/integration/performance)
2. Follow naming conventions
3. Use shared fixtures when possible
4. Update coverage matrix in this README

### Deprecating Tests
1. Move old tests to `tests/archived/`
2. Document reason for deprecation
3. Update coverage matrix

## Coverage Goals
- Unit Tests: >80% code coverage
- Integration Tests: All API endpoints covered
- Performance Tests: Critical paths only
- Zero test duplication
