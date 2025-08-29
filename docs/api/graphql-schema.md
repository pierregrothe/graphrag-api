# GraphQL API Schema Documentation

## Overview

The GraphRAG API provides a comprehensive GraphQL interface with real-time subscriptions, offering 100% feature parity with the REST API. The GraphQL endpoint supports queries, mutations, and subscriptions for all knowledge graph operations.

**Endpoint**: `/graphql`  
**WebSocket Subscriptions**: `ws://localhost:8000/graphql` (or `wss://` for production)

## Authentication

GraphQL requests support the same authentication methods as REST:

```http
# JWT Token
Authorization: Bearer <jwt_token>

# API Key
X-API-Key: <api_key>
```

## Schema Overview

### Core Types

#### Entity
```graphql
type Entity {
  id: String!
  title: String!
  type: String!
  description: String
  degree: Int!
  communityIds: [String!]!
  textUnitIds: [String!]!
  relationships: [Relationship!]
}
```

#### Relationship
```graphql
type Relationship {
  id: String!
  source: String!
  target: String!
  type: String!
  description: String
  weight: Float!
  textUnitIds: [String!]!
}
```

#### Community
```graphql
type Community {
  id: String!
  level: Int!
  title: String!
  entityIds: [String!]!
  relationshipIds: [String!]!
}
```

### Query Operations

#### Basic Entity Queries

```graphql
# Get all entities with pagination
query GetEntities($first: Int, $after: String) {
  entities(first: $first, after: $after) {
    edges {
      node {
        id
        title
        type
        description
        degree
      }
      cursor
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}
```

```graphql
# Get specific entity with relationships
query GetEntityWithRelationships($id: String!) {
  entity(id: $id) {
    id
    title
    type
    description
    relationships {
      id
      source
      target
      type
      weight
    }
  }
}
```

#### Advanced Graph Queries

```graphql
# Semantic search with embeddings
query SemanticSearch($query: String!, $limit: Int = 10) {
  search(query: $query, limit: $limit) {
    entities {
      id
      title
      type
      description
    }
    relationships {
      id
      source
      target
      type
    }
    score
  }
}
```

```graphql
# Community detection
query GetCommunities($level: Int) {
  communities(level: $level) {
    id
    level
    title
    entityIds
    relationshipIds
  }
}
```

#### System and Monitoring Queries

```graphql
# System health and status
query SystemStatus {
  systemHealth {
    status
    uptime
    version
    activeWorkspaces
    totalEntities
    totalRelationships
  }
}
```

```graphql
# Performance metrics
query PerformanceMetrics {
  performanceMetrics {
    timestamp
    cpuUsagePercent
    memoryUsageMb
    activeConnections
    requestsPerSecond
    averageResponseTime
    cacheHitRate
  }
}
```

### Mutation Operations

#### Workspace Management

```graphql
# Create new workspace
mutation CreateWorkspace($name: String!, $description: String) {
  createWorkspace(name: $name, description: $description) {
    id
    name
    description
    status
    createdAt
  }
}
```

#### Indexing Operations

```graphql
# Start indexing job
mutation StartIndexing($workspaceId: String!, $dataPath: String!) {
  startIndexing(workspaceId: $workspaceId, dataPath: $dataPath) {
    jobId
    status
    startedAt
  }
}
```

#### Cache Management

```graphql
# Clear cache
mutation ClearCache($namespace: String) {
  clearCache(namespace: $namespace) {
    success
    clearedEntries
  }
}
```

### Subscription Operations

#### Real-time Updates

```graphql
# Subscribe to indexing updates
subscription IndexingUpdates {
  indexingUpdates {
    workspaceId
    status
    progress
    message
    error
    startedAt
    completedAt
  }
}
```

```graphql
# Subscribe to entity updates
subscription EntityUpdates($workspaceId: String) {
  entityUpdates(workspaceId: $workspaceId) {
    id
    title
    type
    description
    action # CREATED, UPDATED, DELETED
  }
}
```

```graphql
# Subscribe to system performance
subscription PerformanceUpdates {
  performanceUpdates {
    timestamp
    cpuUsagePercent
    memoryUsageMb
    activeConnections
    requestsPerSecond
    averageResponseTime
    cacheHitRate
  }
}
```

## Query Examples with Variables

### Example 1: Entity Search with Filtering

**Query:**
```graphql
query SearchEntities($name: String, $type: String, $first: Int) {
  entities(name: $name, type: $type, first: $first) {
    edges {
      node {
        id
        title
        type
        description
        degree
        communityIds
      }
    }
    totalCount
  }
}
```

**Variables:**
```json
{
  "name": "artificial intelligence",
  "type": "CONCEPT",
  "first": 20
}
```

### Example 2: Multi-hop Graph Traversal

**Query:**
```graphql
query MultiHopTraversal($startEntity: String!, $hops: Int!, $relationTypes: [String!]) {
  multiHopQuery(
    startEntity: $startEntity
    hops: $hops
    relationTypes: $relationTypes
  ) {
    paths {
      entities {
        id
        title
        type
      }
      relationships {
        id
        type
        weight
      }
    }
    totalPaths
  }
}
```

**Variables:**
```json
{
  "startEntity": "entity_123",
  "hops": 3,
  "relationTypes": ["RELATED_TO", "PART_OF"]
}
```

### Example 3: Centrality Analysis

**Query:**
```graphql
query CentralityAnalysis($algorithm: CentralityAlgorithm!, $limit: Int) {
  centralityAnalysis(algorithm: $algorithm, limit: $limit) {
    entities {
      id
      title
      centralityScore
    }
    algorithm
    executionTime
  }
}
```

**Variables:**
```json
{
  "algorithm": "BETWEENNESS",
  "limit": 50
}
```

## Error Handling

GraphQL errors follow the standard GraphQL error format:

```json
{
  "errors": [
    {
      "message": "Entity not found",
      "locations": [{"line": 2, "column": 3}],
      "path": ["entity"],
      "extensions": {
        "code": "ENTITY_NOT_FOUND",
        "entityId": "invalid_id"
      }
    }
  ],
  "data": null
}
```

### Common Error Codes

- `ENTITY_NOT_FOUND`: Requested entity does not exist
- `WORKSPACE_NOT_FOUND`: Requested workspace does not exist
- `INVALID_QUERY`: Query syntax or validation error
- `AUTHENTICATION_REQUIRED`: Valid authentication token required
- `PERMISSION_DENIED`: Insufficient permissions for operation
- `RATE_LIMIT_EXCEEDED`: API rate limit exceeded
- `INTERNAL_ERROR`: Server-side error occurred

## Performance Optimization

### Field Selection
GraphQL automatically optimizes database queries based on requested fields:

```graphql
# Only fetches id and title - optimized query
query OptimizedQuery {
  entities(first: 100) {
    edges {
      node {
        id
        title
      }
    }
  }
}
```

### Query Complexity
Queries are automatically analyzed for complexity. Maximum complexity: 1000 points.

```graphql
# High complexity query - use with caution
query ComplexQuery {
  entities(first: 1000) {
    edges {
      node {
        id
        title
        relationships {
          id
          target
          source
        }
      }
    }
  }
}
```

### Caching
Query results are automatically cached based on:
- Selected fields
- Query parameters
- User permissions
- Data freshness

## WebSocket Subscriptions

### Connection Setup

```javascript
// JavaScript WebSocket connection
const ws = new WebSocket('ws://localhost:8000/graphql', 'graphql-ws');

// Send connection init
ws.send(JSON.stringify({
  type: 'connection_init',
  payload: {
    Authorization: 'Bearer <jwt_token>'
  }
}));
```

### Subscription Example

```javascript
// Subscribe to entity updates
ws.send(JSON.stringify({
  id: '1',
  type: 'start',
  payload: {
    query: `
      subscription {
        entityUpdates {
          id
          title
          action
        }
      }
    `
  }
}));
```

## GraphQL Playground

Access the interactive GraphQL playground at:
- **Local Development**: http://localhost:8000/graphql
- **Production**: https://api.graphrag.example.com/graphql

The playground provides:
- Schema introspection
- Query autocompletion
- Real-time query execution
- Subscription testing
- Documentation explorer

## Best Practices

### 1. Use Fragments for Reusable Fields
```graphql
fragment EntityBasic on Entity {
  id
  title
  type
  description
}

query GetEntities {
  entities(first: 10) {
    edges {
      node {
        ...EntityBasic
        degree
      }
    }
  }
}
```

### 2. Implement Proper Error Handling
```javascript
const result = await client.query({
  query: GET_ENTITIES,
  errorPolicy: 'all'
});

if (result.errors) {
  result.errors.forEach(error => {
    console.error('GraphQL Error:', error.message);
  });
}
```

### 3. Use Variables for Dynamic Queries
```graphql
# Good - using variables
query GetEntity($id: String!) {
  entity(id: $id) {
    id
    title
  }
}

# Avoid - string interpolation
# query GetEntity {
#   entity(id: "hardcoded_id") {
#     id
#     title
#   }
# }
```

### 4. Optimize Subscription Usage
```graphql
# Subscribe only to necessary updates
subscription OptimizedUpdates($workspaceId: String!) {
  entityUpdates(workspaceId: $workspaceId) {
    id
    action
    # Only fetch essential fields
  }
}
```
