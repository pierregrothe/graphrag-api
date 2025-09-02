# Test Suite Reorganization Plan

## Current Issues
1. **Redundancy**: Multiple test files testing similar functionality (e.g., test_main.py, test_api_integration.py, test_api_parity.py)
2. **Poor Naming**: Inconsistent naming conventions (test_fixes.py, test_phase11_graphql_enhancement.py)
3. **No Module Alignment**: Tests not organized by the actual module structure
4. **Missing Coverage Matrix**: No clear mapping of what's tested

## Proposed Test Structure

### Core Module Tests (Unit Tests)
Each module should have its corresponding test file:

```
tests/
├── unit/                           # Unit tests for individual modules
│   ├── test_auth.py               # Auth module tests
│   ├── test_cache.py              # Cache module tests
│   ├── test_config.py             # Configuration tests
│   ├── test_database.py           # Database module tests
│   ├── test_graph.py              # Graph operations tests
│   ├── test_indexing.py           # Indexing module tests
│   ├── test_providers.py          # LLM providers tests
│   ├── test_workspace.py          # Workspace management tests
│   └── test_middleware.py         # Middleware tests
│
├── integration/                    # Integration tests
│   ├── test_api_endpoints.py     # REST API endpoint tests
│   ├── test_graphql_endpoints.py # GraphQL endpoint tests
│   ├── test_workflow.py          # End-to-end workflow tests
│   └── test_provider_integration.py # Provider integration tests
│
├── performance/                    # Performance tests
│   ├── test_load.py               # Load testing
│   ├── test_cache_performance.py # Cache performance
│   └── test_query_performance.py # Query performance
│
└── fixtures/                       # Shared test fixtures
    ├── __init__.py
    ├── data.py                    # Test data fixtures
    ├── mocks.py                   # Mock objects
    └── clients.py                 # Test clients
```

## Test Naming Convention

### Format: `test_<module>_<functionality>_<scenario>.py`

Examples:
- `test_auth_jwt_validation.py`
- `test_workspace_create_success.py`
- `test_api_query_invalid_params.py`

### Test Class Naming
- Unit Tests: `Test<Module><Feature>`
- Integration Tests: `Test<Feature>Integration`
- Performance Tests: `Test<Feature>Performance`

### Test Method Naming
- `test_<action>_<condition>_<expected_result>`
- Examples:
  - `test_create_workspace_valid_data_returns_success`
  - `test_query_invalid_workspace_returns_404`
  - `test_authenticate_expired_token_raises_error`

## API/GraphQL Test Matrix

| Feature | REST API | GraphQL | Unit Test | Integration Test | Performance Test |
|---------|----------|---------|-----------|------------------|------------------|
| **Authentication** |
| - Login | ✓ | ✓ | ✓ | ✓ | - |
| - Token Validation | ✓ | ✓ | ✓ | ✓ | - |
| - API Key Auth | ✓ | ✓ | ✓ | ✓ | - |
| **Workspace Management** |
| - Create Workspace | ✓ | ✓ | ✓ | ✓ | - |
| - List Workspaces | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Update Workspace | ✓ | ✓ | ✓ | ✓ | - |
| - Delete Workspace | ✓ | ✓ | ✓ | ✓ | - |
| **GraphRAG Operations** |
| - Query (Local) | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Query (Global) | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Indexing | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Status Check | ✓ | ✓ | ✓ | ✓ | - |
| **Graph Operations** |
| - Get Entities | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Get Relationships | ✓ | ✓ | ✓ | ✓ | ✓ |
| - Get Communities | ✓ | ✓ | ✓ | ✓ | - |
| - Graph Statistics | ✓ | ✓ | ✓ | ✓ | - |
| **System Operations** |
| - Health Check | ✓ | ✓ | - | ✓ | - |
| - Provider Switch | ✓ | - | ✓ | ✓ | - |
| - Cache Clear | ✓ | ✓ | ✓ | ✓ | - |
| - Configuration | ✓ | - | ✓ | ✓ | - |

## Tests to Remove/Consolidate

### Remove (Redundant/Obsolete):
- `test_fixes.py` - Unclear purpose
- `test_main.py` - Redundant with test_api_integration.py
- `test_api_parity.py` - Should be part of integration tests
- `test_postman_runner.py` - External tool, not core functionality
- `test_advanced_query_engine.py` - Should be part of graph tests
- `test_graph_analytics.py` - Should be part of graph tests

### Consolidate:
- `test_api_integration.py` + `test_main.py` → `integration/test_api_endpoints.py`
- `test_graphql.py` + GraphQL parts of `test_api_parity.py` → `integration/test_graphql_endpoints.py`
- `test_indexing.py` + `test_indexing_api.py` → `unit/test_indexing.py` + `integration/test_indexing_workflow.py`
- `test_providers_base.py` + `test_provider.py` → `unit/test_providers.py`
- `test_graph_operations.py` + `test_graph_analytics.py` + `test_advanced_query_engine.py` → `unit/test_graph.py`

## Implementation Steps

1. **Create new directory structure**
2. **Move and reorganize existing tests**
3. **Remove redundant tests**
4. **Update imports and fixtures**
5. **Create shared fixtures module**
6. **Document test coverage**
7. **Update CI/CD configuration**

## Test Documentation Template

Each test file should have:
```python
"""
Module: <module_name>
Tests: <what this file tests>
Coverage: <what scenarios are covered>
Dependencies: <external dependencies if any>
"""
```

## Coverage Goals
- Unit Test Coverage: >80%
- Integration Test Coverage: All API endpoints
- Performance Tests: Critical paths only
- No duplicate tests across files
- Clear separation of concerns