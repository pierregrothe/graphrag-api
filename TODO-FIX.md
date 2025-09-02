# GraphRAG API Service - TODO and Fix Plan

This document outlines the necessary fixes and improvements for the GraphRAG API service, based on a detailed code analysis. The plan is divided into phases to ensure a structured and manageable approach to resolving the identified issues.

**IMPORTANT NOTE:** According to the README.md, this project is marked as "PRODUCTION READY" with Phase 11 completed. However, the analysis reveals several architectural inconsistencies that should be addressed for true production readiness.

## Phase 1: Code Cleanup and Consolidation

**Goal:** Refactor the codebase to remove redundancy, improve consistency, and establish a solid foundation for future development.

-   **Task 1.1: Unify Configuration Management**
    -   [ ] **CORRECTION:** Keep both configuration modules but refactor for clarity:
        - `config.py` for application runtime settings
        - `deployment/config.py` for infrastructure and deployment-specific settings
    -   [ ] Create a clear separation of concerns between runtime and deployment configurations
    -   [ ] Document which settings belong in which configuration file
    -   [ ] Consider using a configuration factory pattern to merge settings when needed

-   **Task 1.2: Consolidate API Routes**
    -   [ ] **CORRECTION:** The v2 routes ARE actively used and loaded in main.py
    -   [ ] Complete the implementation of v2 route handlers (they currently return mock data)
    -   [ ] Remove the old v1 route files once v2 implementation is complete
    -   [ ] The v2 routes already use dependency injection correctly via `GraphOperationsDep`

-   **Task 1.3: Remove `main_backup.py`**
    -   [ ] The `main_backup.py` file appears to be an older version of `main.py`. This file should be removed to avoid confusion.

## Phase 2: Authentication and Authorization

**Goal:** Implement a robust and secure authentication and authorization system suitable for production use.

-   **Task 2.1: Implement Persistent User Store**
    -   [ ] Replace the in-memory user store in `src/graphrag_api_service/auth/jwt_auth.py` (line 315) with a database-backed implementation
    -   [ ] Create database models for users, roles, and permissions
    -   [ ] **NOTE:** The comment explicitly states "replace with database" indicating this is a known limitation

-   **Task 2.2: Complete API Key and JWT Integration**
    -   [ ] Implement the `TODO` for the admin check in the `revoke_api_key` function (line 212 in `api_keys.py`)
    -   [ ] **CORRECTION:** Authentication middleware IS already integrated via `setup_auth_middleware` in main.py
    -   [ ] The middleware stack includes both JWT and API key authentication

## Phase 3: GraphQL Implementation

**Goal:** Complete the GraphQL interface to be on par with the REST API and ready for production use.

-   **Task 3.1: GraphQL Resolver Status**
    -   [ ] **CORRECTION:** Most GraphQL resolvers appear to be implemented
    -   [ ] Only one TODO found: cache clearing functionality in mutations.py (line 510)
    -   [ ] Verify all resolvers are returning real data, not mock responses
    -   [ ] Complete the cache clearing implementation

-   **Task 3.2: Integrate DataLoader**
    -   [ ] **CONFIRMED:** No DataLoader implementation exists in the codebase
    -   [ ] This is a critical performance optimization for GraphQL
    -   [ ] Implement DataLoader for entity and relationship fetching

-   **Task 3.3: Advanced GraphQL Features Status**
    -   [ ] **NOTE:** According to README.md, GraphQL subscriptions ARE implemented (WebSocket-based)
    -   [ ] Query complexity analysis appears to be implemented via `get_complexity_analyzer` in optimization.py
    -   [ ] Verify field-level permissions are working as expected

## Phase 4: Production Readiness

**Goal:** Prepare the application for production deployment by addressing scalability, observability, and deployment automation.

-   **Task 4.1: Implement a Data Persistence Layer**
    -   [ ] **CONFIRMED:** Workspace manager uses JSON file storage (workspaces.json)
    -   [ ] No real database integration exists despite deployment/config.py having DatabaseConfig
    -   [ ] The ConnectionPool class exists but appears to be a mock/placeholder
    -   [ ] Implement actual PostgreSQL integration with pgvector for embeddings
    -   [ ] Refactor workspace and indexing modules to use the database

-   **Task 4.2: Enhance Logging and Error Handling**
    -   [ ] **NOTE:** Logging configuration exists in logging_config.py
    -   [ ] Structured logging may already be partially implemented
    -   [ ] Verify and enhance JSON logging format for production
    -   [ ] Review error handling middleware in main.py

-   **Task 4.3: Create a CI/CD Pipeline**
    -   [ ] **NOTE:** README mentions 300+ tests with 100% pass rate
    -   [ ] Verify if GitHub Actions already exists in the repository
    -   [ ] Add automated deployment steps if not present

-   **Task 4.4: Deployment Infrastructure**
    -   [ ] **NOTE:** Docker support is mentioned as "Ready" in README
    -   [ ] Verify Docker Compose configuration exists and works
    -   [ ] Create Kubernetes manifests if required for cloud deployment

## Priority Recommendations

Based on the analysis, here are the **CRITICAL** issues that should be addressed first for true production readiness:

### High Priority (Security & Data Integrity)
1. **Replace in-memory user store** - The JWT auth system uses an in-memory dictionary which will lose all users on restart
2. **Implement database persistence** - Currently using JSON files for workspace storage, not suitable for production
3. **Complete admin authorization check** - Security vulnerability in API key revocation

### Medium Priority (Performance & Reliability)
1. **Complete v2 route implementations** - Currently returning mock data
2. **Implement DataLoader for GraphQL** - Prevent N+1 query problems
3. **Add real database connection pooling** - Current ConnectionPool appears to be a placeholder

### Low Priority (Code Quality)
1. **Remove main_backup.py** - Cleanup redundant code
2. **Document configuration separation** - Clarify which settings go where
3. **Verify test coverage** - Ensure the claimed 300+ tests are comprehensive

## Architecture Observations

The codebase shows signs of being in transition:
- **Dual routing system** (v1 and v2) with v2 being actively used but incomplete
- **Configuration split** between runtime and deployment is intentional but needs documentation
- **Authentication middleware** is properly integrated despite initial analysis concerns
- **GraphQL implementation** is more complete than initially assessed
- **Database layer** is the most critical missing piece despite infrastructure code existing
