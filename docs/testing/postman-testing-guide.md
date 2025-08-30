# Postman Testing Guide for GraphRAG API

## Overview

This guide provides comprehensive instructions for testing the GraphRAG API using Postman. The collection includes all REST endpoints, GraphQL queries, authentication methods, and performance testing scenarios.

## Quick Start

### 1. Import Collection and Environment

1. **Import Collection**:

- Open Postman
- Click "Import" → "Upload Files"
- Select `postman/GraphRAG-API-Collection.json`

2. **Import Environment**:

- Import `postman/environments/Local-Development.postman_environment.json` for local testing
- Import `postman/environments/Production.postman_environment.json` for production testing

3. **Select Environment**:

- Click the environment dropdown (top right)
- Select "GraphRAG API - Local Development"

### 2. Initial Setup

1. **Start Local Server**:

```bash
cd /path/to/graphrag
docker-compose up -d
# OR
python -m uvicorn src.graphrag_api_service.main:app --reload
```

2. **Verify Health**:

- Run "Health & System" → "Basic Health Check"
- Should return `{"status": "healthy"}`

## Authentication Setup

### JWT Token Authentication

1. **Login to Get JWT Token**:

- Go to "Authentication" → "Login (JWT)"
- Update environment variables if needed:
- `username`: Your username (default: "admin")
- `password`: Your password (default: "admin123")
- Run the request
- JWT token will be automatically stored in environment

2. **Verify Token**:

- Run any request in "Entities" folder
- Should work without additional setup

### API Key Authentication

1. **Create API Key**:

- Ensure you're logged in with JWT token
- Go to "Authentication" → "Create API Key"
- Run the request
- API key will be automatically stored in environment

2. **Test API Key**:

- Go to "API Key Authentication" folder
- Run "Get Entities (API Key)"
- Should work without JWT token

## Testing Scenarios

### 1. Entity Operations

#### Basic Entity Retrieval

```
Test Sequence:
1. "Entities" → "List Entities"
2. "Entities" → "Get Entity by ID" (uses auto-stored entity ID)
3. "Entities" → "Search Entities"

Expected Results:
- Status: 200 OK
- Response contains entities array
- Entity IDs are automatically stored for subsequent tests
```

#### Entity Filtering

```
Test Parameters:
- Set entity_name_filter: "technology"
- Set entity_type_filter: "CONCEPT"
- Enable query parameters in "List Entities"

Expected Results:
- Filtered results based on criteria
- Reduced result set
```

### 2. Relationship Operations

#### Relationship Retrieval

```
Test Sequence:
1. "Relationships" → "List Relationships"
2. "Relationships" → "Get Entity Relationships"

Expected Results:
- Status: 200 OK
- Relationships array with source/target entities
- Relationship types and weights
```

#### Relationship Filtering

```
Test Parameters:
- Set source_entity: {{sample_entity_id}}
- Set relationship_type: "RELATED_TO"
- Enable query parameters

Expected Results:
- Filtered relationships for specific entity
- Only specified relationship types
```

### 3. Graph Operations

#### Semantic Search

```
Test Sequence:
1. "Graph Operations" → "Semantic Search"
2. Modify search_query: "artificial intelligence"

Expected Results:
- Status: 200 OK
- Relevant entities and relationships
- Search scores and rankings
```

#### Multi-hop Queries

```
Test Parameters:
- start_entity: {{sample_entity_id}}
- hops: 2
- relation_types: ["RELATED_TO", "PART_OF"]

Expected Results:
- Graph traversal paths
- Connected entities within specified hops
- Relationship chains
```

### 4. Community Detection

#### Community Retrieval

```
Test Sequence:
1. "Communities" → "List Communities"
2. "Communities" → "Community Detection"

Expected Results:
- Detected community structures
- Entity groupings
- Community hierarchy levels
```

### 5. GraphQL Testing

#### Basic GraphQL Queries

```
Test Sequence:
1. "GraphQL" → "GraphQL - Get Entities"
2. "GraphQL" → "Entity with Relationships"
3. "GraphQL" → "Semantic Search"

Expected Results:
- GraphQL response format with data field
- No errors in response
- Proper field selection optimization
```

#### Complex GraphQL Operations

```
Test Query:
query ComplexQuery {
entities(first: 10) {
edges {
node {
id
title
type
relationships {
id
type
weight
}
}
}
}
communities(first: 5) {
id
title
entityIds
}
}

Expected Results:
- Multiple operation results in single request
- Optimized database queries
- Response time under 2 seconds
```

### 6. Workspace Management

#### Workspace Lifecycle

```
Test Sequence:
1. "Workspace Management" → "Create Workspace"
2. "Workspace Management" → "List Workspaces"
3. "Workspace Management" → "Start Indexing"

Expected Results:
- Workspace created successfully
- Workspace appears in list
- Indexing job started
```

## Performance Testing

### Load Testing

#### Entity Load Test

```
Configuration:
- Run "Performance Testing" → "Load Test - Entities"
- Use Postman Runner with 10-50 iterations
- Monitor response times and success rates

Success Criteria:
- 95% success rate
- Average response time < 1 second
- No rate limiting errors
```

#### GraphQL Stress Test

```
Configuration:
- Run "Performance Testing" → "Stress Test - GraphQL"
- Complex query with multiple operations
- Monitor query complexity and performance

Success Criteria:
- Response time < 5 seconds
- No GraphQL errors
- Proper complexity analysis
```

### Rate Limiting Tests

#### API Key Rate Limiting

```
Test Procedure:
1. Create API key with low rate limit (e.g., 10 requests/hour)
2. Make rapid requests using API key
3. Verify rate limiting kicks in

Expected Results:
- HTTP 429 Too Many Requests
- Proper retry-after headers
- Rate limit reset information
```

## Error Testing

### Authentication Errors

#### Invalid Credentials

```
Test Cases:
1. Login with wrong password
2. Use expired JWT token
3. Use invalid API key

Expected Results:
- HTTP 401 Unauthorized
- Proper error messages
- Security audit logging
```

#### Permission Errors

```
Test Cases:
1. Access restricted endpoints
2. Use API key with limited permissions
3. Cross-tenant access attempts

Expected Results:
- HTTP 403 Forbidden
- Permission denied messages
- Required permission information
```

### Validation Errors

#### Invalid Request Data

```
Test Cases:
1. Send malformed JSON
2. Missing required fields
3. Invalid field values

Expected Results:
- HTTP 400 Bad Request
- Detailed validation errors
- Field-specific error messages
```

### Server Errors

#### Timeout Testing

```
Test Cases:
1. Very complex GraphQL queries
2. Large result set requests
3. Concurrent request load

Expected Results:
- HTTP 504 Gateway Timeout (if applicable)
- Proper timeout handling
- Graceful error responses
```

## Environment Configuration

### Local Development Environment

```json
{
"base_url": "http://localhost:8000",
"username": "admin",
"password": "admin123",
"entity_limit": "20",
"search_query": "artificial intelligence"
}
```

### Staging Environment

```json
{
"base_url": "https://staging-api.graphrag.example.com",
"username": "staging_user",
"password": "staging_password",
"entity_limit": "10",
"search_query": "machine learning"
}
```

### Production Environment

```json
{
"base_url": "https://api.graphrag.example.com",
"username": "",
"password": "",
"entity_limit": "5",
"search_query": "innovation"
}
```

**Security Note**: Never store production credentials in environment files. Set them manually in Postman.

## Automated Testing

### Collection Runner

1. **Setup Runner**:

- Click "Runner" in Postman
- Select "GraphRAG API - Complete Collection"
- Choose environment

2. **Configure Run**:

- Iterations: 1-10 (depending on test type)
- Delay: 100ms between requests
- Data file: Optional CSV for data-driven tests

3. **Monitor Results**:

- Pass/fail rates
- Response times
- Error patterns

### Newman CLI

```bash
# Install Newman
npm install -g newman

# Run collection
newman run postman/GraphRAG-API-Collection.json \
-e postman/environments/Local-Development.postman_environment.json \
--reporters cli,html \
--reporter-html-export results.html

# Run with data file
newman run postman/GraphRAG-API-Collection.json \
-e postman/environments/Local-Development.postman_environment.json \
-d test-data.csv \
--iteration-count 10
```

## Sample Data Sets

### Entity Test Data

```csv
entity_name,entity_type,search_term
"artificial intelligence",CONCEPT,"AI technology"
"machine learning",CONCEPT,"ML algorithms"
"neural networks",CONCEPT,"deep learning"
"data science",CONCEPT,"analytics"
```

### Search Test Data

```csv
search_query,expected_results
"artificial intelligence",5
"machine learning",8
"data analysis",3
"neural networks",6
```

## Troubleshooting

### Common Issues

#### Authentication Failures

```
Problem: 401 Unauthorized errors
Solutions:
1. Check username/password in environment
2. Verify JWT token hasn't expired
3. Ensure API key is valid and active
4. Check authentication headers
```

#### Rate Limiting

```
Problem: 429 Too Many Requests
Solutions:
1. Reduce request frequency
2. Implement delays between requests
3. Check rate limit settings
4. Use different API keys for testing
```

#### Network Issues

```
Problem: Connection timeouts
Solutions:
1. Verify server is running
2. Check base_url in environment
3. Test with simple health check
4. Check firewall/proxy settings
```

#### GraphQL Errors

```
Problem: GraphQL validation errors
Solutions:
1. Validate query syntax
2. Check field names and types
3. Verify query complexity
4. Test with GraphQL playground
```

### Debug Tips

1. **Enable Console Logging**:

- Open Postman Console (View → Show Postman Console)
- Monitor request/response details
- Check pre-request and test script logs

2. **Use Test Scripts**:

- Add console.log statements
- Validate response structure
- Store values for debugging

3. **Monitor Network**:

- Use browser dev tools for GraphQL playground
- Check actual HTTP requests
- Verify headers and payloads

## Best Practices

### Test Organization

1. **Use Folders**: Group related tests logically
2. **Naming Convention**: Clear, descriptive request names
3. **Documentation**: Add descriptions to all requests
4. **Variables**: Use environment variables for reusability

### Security

1. **Credential Management**: Never commit credentials to version control
2. **Environment Separation**: Use different environments for different stages
3. **API Key Rotation**: Regularly rotate API keys
4. **Permission Testing**: Test with minimal required permissions

### Performance

1. **Response Time Monitoring**: Set reasonable thresholds
2. **Load Testing**: Test with realistic data volumes
3. **Caching Validation**: Verify cache hit rates
4. **Resource Monitoring**: Monitor server resources during tests

### Maintenance

1. **Regular Updates**: Keep collection updated with API changes
2. **Test Data**: Maintain realistic test datasets
3. **Environment Sync**: Keep environments synchronized
4. **Documentation**: Update guides with new features
