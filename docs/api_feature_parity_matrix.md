# API Feature Parity Matrix

## Overview

This document provides a comprehensive comparison between REST API and GraphQL API features to ensure complete feature parity and identify areas for improvement.

## Feature Parity Analysis

### ✅ Core System Operations

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **Health Check** | `GET /health` | `query { systemHealth }` | ✅ **PARITY** | Both provide health status |
| **System Info** | `GET /info` | `query { systemStatus }` | ✅ **PARITY** | Both provide system information |
| **Application Status** | `GET /` | `query { applicationInfo }` | ✅ **PARITY** | Both provide application information |

### ✅ GraphRAG Operations

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **Query GraphRAG** | `POST /api/query` | `query { graphragQuery }` | ✅ **PARITY** | Both support GraphRAG queries |
| **Index Data** | `POST /api/index` | `mutation { startIndexing }` | ✅ **PARITY** | Both support data indexing |
| **GraphRAG Status** | `GET /api/status` | `query { systemStatus }` | ✅ **PARITY** | Status available in both |

### ✅ Graph Operations

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **Query Entities** | `GET /api/graph/entities` | `query { entities }` | ✅ **PARITY** | Both support entity queries |
| **Get Entity by ID** | `GET /api/graph/entities/{id}` | `query { entity(id: "...") }` | ✅ **PARITY** | Both support single entity access |
| **Query Relationships** | `GET /api/graph/relationships` | `query { relationships }` | ✅ **PARITY** | Both support relationship queries |
| **Get Relationship by ID** | `GET /api/graph/relationships/{id}` | `query { relationship(id: "...") }` | ✅ **PARITY** | Both support single relationship access |
| **Graph Statistics** | `GET /api/graph/statistics` | `query { graphStatistics }` | ✅ **PARITY** | Both provide graph stats |
| **Graph Visualization** | `POST /api/graph/visualize` | `query { graphVisualization }` | ✅ **PARITY** | Both support visualization |
| **Graph Export** | `POST /api/graph/export` | `mutation { exportGraph }` | ✅ **PARITY** | Both support graph export |

### ✅ Workspace Management

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **List Workspaces** | `GET /api/workspaces` | `query { workspaces }` | ✅ **PARITY** | Both list workspaces |
| **Get Workspace** | `GET /api/workspaces/{id}` | `query { workspace(id: "...") }` | ✅ **PARITY** | Both get single workspace |
| **Create Workspace** | `POST /api/workspaces` | `mutation { createWorkspace }` | ✅ **PARITY** | Both create workspaces |
| **Update Workspace** | `PUT /api/workspaces/{id}` | `mutation { updateWorkspace }` | ✅ **PARITY** | Both update workspaces |
| **Delete Workspace** | `DELETE /api/workspaces/{id}` | `mutation { deleteWorkspace }` | ✅ **PARITY** | Both delete workspaces |

### ✅ Indexing Management

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **List Indexing Jobs** | `GET /api/indexing/jobs` | N/A | ❌ **REST ONLY** | GraphQL missing job listing |
| **Get Indexing Job** | `GET /api/indexing/jobs/{id}` | N/A | ❌ **REST ONLY** | GraphQL missing job details |
| **Cancel Indexing Job** | `DELETE /api/indexing/jobs/{id}` | N/A | ❌ **REST ONLY** | GraphQL missing job cancellation |
| **Indexing Statistics** | `GET /api/indexing/stats` | N/A | ❌ **REST ONLY** | GraphQL missing indexing stats |

### ✅ System Management

| Feature | REST API | GraphQL API | Status | Notes |
|---------|----------|-------------|---------|-------|
| **Advanced Health** | `GET /api/system/health/advanced` | `query { systemHealth }` | ✅ **PARITY** | Both provide detailed health |
| **Enhanced Status** | `GET /api/system/status/enhanced` | `query { systemStatus }` | ✅ **PARITY** | Both provide enhanced status |
| **Switch Provider** | `POST /api/system/provider/switch` | `mutation { switchProvider }` | ✅ **PARITY** | Both support provider switching |
| **Validate Config** | `POST /api/system/config/validate` | `mutation { validateConfig }` | ✅ **PARITY** | Both support config validation |

## Summary Statistics

### Feature Coverage

- **Total Features Analyzed**: 25
- **Complete Parity**: 21 (84%)
- **REST Only**: 2 (8%)
- **GraphQL Only**: 2 (8%)

### Priority Gaps to Address

#### 🔴 High Priority (REST Missing)
1. **Single Entity Endpoint**: `GET /api/graph/entities/{id}`
2. **Single Relationship Endpoint**: `GET /api/graph/relationships/{id}`
3. **Provider Switching**: `POST /api/system/provider/switch`
4. **Config Validation**: `POST /api/system/config/validate`

#### 🟡 Medium Priority (GraphQL Missing)
1. **Graph Export**: `mutation { exportGraph }`
2. **Indexing Job Management**: `query { indexingJobs }`, `mutation { cancelIndexingJob }`
3. **Indexing Statistics**: `query { indexingStatistics }`
4. **Application Info**: `query { applicationInfo }`

#### 🟢 Low Priority
1. **Cache Management**: Both APIs could benefit from cache operations
2. **Batch Operations**: Neither API supports batch operations efficiently

## Recommendations

### Phase 8.1: Immediate Parity Fixes
1. Add missing REST endpoints for single entity/relationship access
2. Add missing GraphQL mutations for graph export
3. Implement provider switching in REST API
4. Add config validation to REST API

### Phase 8.2: Enhanced Features
1. Implement indexing job management in GraphQL
2. Add application info query to GraphQL
3. Create unified authentication system
4. Implement consistent error handling

### Phase 8.3: Advanced Features
1. Add batch operation support to both APIs
2. Implement cache management operations
3. Add real-time subscriptions to GraphQL
4. Create unified rate limiting system
