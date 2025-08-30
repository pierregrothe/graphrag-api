# Error Codes Reference

## Overview

The GraphRAG API uses standard HTTP status codes and provides detailed error information in JSON format. This document covers all possible error scenarios, their causes, and resolution steps.

## Error Response Format

All API errors return a consistent JSON structure:

```json
{
    "error": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
        "field": "Additional context",
        "suggestion": "How to fix the issue"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123def456"
}
```

## HTTP Status Codes

### 2xx Success Codes

| Code | Status     | Description                             |
| ---- | ---------- | --------------------------------------- |
| 200  | OK         | Request successful                      |
| 201  | Created    | Resource created successfully           |
| 202  | Accepted   | Request accepted for processing         |
| 204  | No Content | Request successful, no content returned |

### 4xx Client Error Codes

#### 400 Bad Request

**INVALID_REQUEST_FORMAT**

```json
{
    "error": "INVALID_REQUEST_FORMAT",
    "message": "Request body must be valid JSON",
    "details": {
        "received_content_type": "text/plain",
        "expected_content_type": "application/json"
    }
}
```

**Cause**: Request body is not valid JSON or has incorrect Content-Type header
**Resolution**: Ensure request body is valid JSON and Content-Type header is `application/json`

**MISSING_REQUIRED_FIELD**

```json
{
    "error": "MISSING_REQUIRED_FIELD",
    "message": "Required field 'name' is missing",
    "details": {
        "missing_fields": ["name"],
        "required_fields": ["name", "permissions"]
    }
}
```

**Cause**: Required fields are missing from the request
**Resolution**: Include all required fields in your request

**INVALID_FIELD_VALUE**

```json
{
    "error": "INVALID_FIELD_VALUE",
    "message": "Field 'limit' must be between 1 and 1000",
    "details": {
        "field": "limit",
        "value": 5000,
        "min": 1,
        "max": 1000
    }
}
```

**Cause**: Field value is outside acceptable range or format
**Resolution**: Provide a valid value within the specified range

**INVALID_QUERY_PARAMETER**

```json
{
    "error": "INVALID_QUERY_PARAMETER",
    "message": "Invalid query parameter 'sort_by'",
    "details": {
        "parameter": "sort_by",
        "value": "invalid_field",
        "allowed_values": ["name", "created_at", "updated_at"]
    }
}
```

**Cause**: Query parameter has invalid value
**Resolution**: Use one of the allowed values for the parameter

#### 401 Unauthorized

**AUTHENTICATION_REQUIRED**

```json
{
    "error": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required to access this resource",
    "details": {
        "supported_methods": ["Bearer token", "API key"],
        "headers": {
            "jwt": "Authorization: Bearer <token>",
            "api_key": "X-API-Key: <key>"
        }
    }
}
```

**Cause**: No authentication credentials provided
**Resolution**: Include valid JWT token or API key in request headers

**INVALID_TOKEN**

```json
{
    "error": "INVALID_TOKEN",
    "message": "The provided authentication token is invalid",
    "details": {
        "token_type": "jwt",
        "reason": "signature_invalid"
    }
}
```

**Cause**: JWT token signature is invalid or malformed
**Resolution**: Obtain a new token by logging in again

**TOKEN_EXPIRED**

```json
{
    "error": "TOKEN_EXPIRED",
    "message": "The authentication token has expired",
    "details": {
        "expired_at": "2024-01-15T10:00:00Z",
        "current_time": "2024-01-15T10:30:00Z",
        "refresh_endpoint": "/auth/refresh"
    }
}
```

**Cause**: JWT token has passed its expiration time
**Resolution**: Use refresh token to get a new access token, or login again

**INVALID_API_KEY**

```json
{
    "error": "INVALID_API_KEY",
    "message": "The provided API key is invalid or has been revoked",
    "details": {
        "key_prefix": "grag_abcd1234",
        "status": "revoked"
    }
}
```

**Cause**: API key is invalid, expired, or revoked
**Resolution**: Generate a new API key or check key status

#### 403 Forbidden

**PERMISSION_DENIED**

```json
{
    "error": "PERMISSION_DENIED",
    "message": "Insufficient permissions to perform this action",
    "details": {
        "required_permission": "write:entities",
        "user_permissions": ["read:entities", "read:relationships"],
        "action": "create_entity"
    }
}
```

**Cause**: User lacks required permissions for the operation
**Resolution**: Contact administrator to grant necessary permissions

**TENANT_ACCESS_DENIED**

```json
{
    "error": "TENANT_ACCESS_DENIED",
    "message": "Access denied to resources in this tenant",
    "details": {
        "user_tenant": "tenant_a",
        "resource_tenant": "tenant_b",
        "resource_id": "workspace_123"
    }
}
```

**Cause**: User trying to access resources from different tenant
**Resolution**: Ensure you're accessing resources within your tenant scope

**RATE_LIMIT_EXCEEDED**

```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "details": {
        "limit": 1000,
        "window": "1 hour",
        "reset_time": "2024-01-15T11:00:00Z",
        "retry_after": 1800
    }
}
```

**Cause**: API rate limit has been exceeded
**Resolution**: Wait until reset time or upgrade to higher rate limit

#### 404 Not Found

**ENTITY_NOT_FOUND**

```json
{
    "error": "ENTITY_NOT_FOUND",
    "message": "Entity with the specified ID was not found",
    "details": {
        "entity_id": "entity_123",
        "workspace_id": "workspace_456"
    }
}
```

**Cause**: Requested entity does not exist
**Resolution**: Verify entity ID and ensure it exists in the specified workspace

**WORKSPACE_NOT_FOUND**

```json
{
    "error": "WORKSPACE_NOT_FOUND",
    "message": "Workspace with the specified ID was not found",
    "details": {
        "workspace_id": "workspace_invalid",
        "available_workspaces": ["workspace_1", "workspace_2"]
    }
}
```

**Cause**: Requested workspace does not exist or user lacks access
**Resolution**: Use a valid workspace ID that you have access to

**ENDPOINT_NOT_FOUND**

```json
{
    "error": "ENDPOINT_NOT_FOUND",
    "message": "The requested endpoint does not exist",
    "details": {
        "path": "/api/invalid-endpoint",
        "method": "GET",
        "available_endpoints": "/docs"
    }
}
```

**Cause**: Requested URL path does not exist
**Resolution**: Check API documentation for correct endpoint paths

#### 409 Conflict

**RESOURCE_ALREADY_EXISTS**

```json
{
    "error": "RESOURCE_ALREADY_EXISTS",
    "message": "A resource with this identifier already exists",
    "details": {
        "resource_type": "workspace",
        "identifier": "my-workspace",
        "existing_id": "workspace_789"
    }
}
```

**Cause**: Attempting to create resource with duplicate identifier
**Resolution**: Use a unique identifier or update existing resource

**CONCURRENT_MODIFICATION**

```json
{
    "error": "CONCURRENT_MODIFICATION",
    "message": "Resource was modified by another request",
    "details": {
        "resource_id": "entity_123",
        "expected_version": 5,
        "current_version": 7
    }
}
```

**Cause**: Resource was modified between read and write operations
**Resolution**: Refresh resource data and retry the operation

#### 413 Payload Too Large

**REQUEST_TOO_LARGE**

```json
{
    "error": "REQUEST_TOO_LARGE",
    "message": "Request payload exceeds maximum allowed size",
    "details": {
        "size": "15MB",
        "max_size": "10MB",
        "suggestion": "Split large requests into smaller chunks"
    }
}
```

**Cause**: Request body exceeds size limits
**Resolution**: Reduce request size or split into multiple requests

#### 422 Unprocessable Entity

**VALIDATION_ERROR**

```json
{
    "error": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
        "errors": [
            {
                "field": "email",
                "message": "Invalid email format",
                "value": "invalid-email"
            },
            {
                "field": "permissions",
                "message": "Unknown permission 'invalid:permission'",
                "allowed_values": ["read:entities", "write:entities"]
            }
        ]
    }
}
```

**Cause**: Request data fails validation rules
**Resolution**: Fix validation errors and resubmit request

#### 429 Too Many Requests

**RATE_LIMIT_EXCEEDED** (detailed)

```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
        "limit_type": "per_minute",
        "limit": 20,
        "window": 60,
        "reset_time": "2024-01-15T10:31:00Z",
        "retry_after": 45
    }
}
```

**Cause**: Too many requests in short time period
**Resolution**: Implement exponential backoff and retry after specified time

### 5xx Server Error Codes

#### 500 Internal Server Error

**INTERNAL_SERVER_ERROR**

```json
{
    "error": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred",
    "details": {
        "request_id": "req_abc123def456",
        "support_contact": "support@graphrag.com"
    }
}
```

**Cause**: Unexpected server-side error
**Resolution**: Contact support with request ID if error persists

**DATABASE_ERROR**

```json
{
    "error": "DATABASE_ERROR",
    "message": "Database operation failed",
    "details": {
        "operation": "query",
        "retry_suggested": true,
        "request_id": "req_abc123def456"
    }
}
```

**Cause**: Database connection or query error
**Resolution**: Retry request; contact support if error persists

#### 502 Bad Gateway

**UPSTREAM_SERVICE_ERROR**

```json
{
    "error": "UPSTREAM_SERVICE_ERROR",
    "message": "Upstream service is unavailable",
    "details": {
        "service": "embedding_service",
        "status": "unavailable",
        "retry_after": 30
    }
}
```

**Cause**: Dependent service (LLM provider, embedding service) is unavailable
**Resolution**: Wait and retry; check service status page

#### 503 Service Unavailable

**SERVICE_MAINTENANCE**

```json
{
    "error": "SERVICE_MAINTENANCE",
    "message": "Service is temporarily unavailable for maintenance",
    "details": {
        "maintenance_window": "2024-01-15T02:00:00Z to 2024-01-15T04:00:00Z",
        "estimated_completion": "2024-01-15T04:00:00Z"
    }
}
```

**Cause**: Scheduled maintenance in progress
**Resolution**: Wait until maintenance window ends

**SERVICE_OVERLOADED**

```json
{
    "error": "SERVICE_OVERLOADED",
    "message": "Service is temporarily overloaded",
    "details": {
        "retry_after": 60,
        "load_level": "high",
        "suggestion": "Reduce request frequency"
    }
}
```

**Cause**: Service experiencing high load
**Resolution**: Implement backoff strategy and reduce request frequency

#### 504 Gateway Timeout

**REQUEST_TIMEOUT**

```json
{
    "error": "REQUEST_TIMEOUT",
    "message": "Request processing timed out",
    "details": {
        "timeout": "30s",
        "operation": "graph_query",
        "suggestion": "Reduce query complexity or increase timeout"
    }
}
```

**Cause**: Request took too long to process
**Resolution**: Simplify query or increase client timeout

## GraphQL-Specific Errors

GraphQL errors are returned in the standard GraphQL error format:

```json
{
    "errors": [
        {
            "message": "Entity not found",
            "locations": [{ "line": 3, "column": 5 }],
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

### Common GraphQL Error Codes

**GRAPHQL_VALIDATION_ERROR**

```json
{
    "errors": [
        {
            "message": "Cannot query field 'invalidField' on type 'Entity'",
            "locations": [{ "line": 4, "column": 7 }],
            "extensions": {
                "code": "GRAPHQL_VALIDATION_ERROR",
                "field": "invalidField",
                "type": "Entity"
            }
        }
    ]
}
```

**QUERY_COMPLEXITY_EXCEEDED**

```json
{
    "errors": [
        {
            "message": "Query complexity 1500 exceeds maximum allowed 1000",
            "extensions": {
                "code": "QUERY_COMPLEXITY_EXCEEDED",
                "complexity": 1500,
                "maxComplexity": 1000
            }
        }
    ]
}
```

**SUBSCRIPTION_ERROR**

```json
{
    "errors": [
        {
            "message": "Subscription connection failed",
            "extensions": {
                "code": "SUBSCRIPTION_ERROR",
                "reason": "authentication_failed"
            }
        }
    ]
}
```

## Error Handling Best Practices

### 1. Implement Proper Error Handling

```python
def handle_api_error(response):
"""Handle API errors with specific actions"""
error_data = response.json()
error_code = error_data.get('error')

if error_code == 'TOKEN_EXPIRED':
# Refresh token and retry
refresh_token()
return 'retry'
elif error_code == 'RATE_LIMIT_EXCEEDED':
# Wait and retry
retry_after = error_data['details']['retry_after']
time.sleep(retry_after)
return 'retry'
elif error_code == 'PERMISSION_DENIED':
# Log and notify user
log_permission_error(error_data)
return 'permission_error'
else:
# Generic error handling
raise APIError(error_data['message'])
```

### 2. Use Exponential Backoff for Retries

```python
import time
import random

def exponential_backoff_retry(func, max_retries=3):
for attempt in range(max_retries):
try:
return func()
except RateLimitError:
if attempt == max_retries - 1:
raise

# Exponential backoff with jitter
wait_time = (2 ** attempt) + random.uniform(0, 1)
time.sleep(wait_time)
```

### 3. Log Errors for Debugging

```python
import logging

def log_api_error(error_response, request_details):
"""Log API errors for debugging"""
logger.error(
"API Error",
extra={
'error_code': error_response.get('error'),
'message': error_response.get('message'),
'request_id': error_response.get('request_id'),
'endpoint': request_details.get('endpoint'),
'method': request_details.get('method'),
'user_id': request_details.get('user_id')
}
)
```

### 4. Provide User-Friendly Error Messages

```python
ERROR_MESSAGES = {
'AUTHENTICATION_REQUIRED': 'Please log in to continue',
'PERMISSION_DENIED': 'You don\'t have permission to perform this action',
'RATE_LIMIT_EXCEEDED': 'Too many requests. Please try again later',
'ENTITY_NOT_FOUND': 'The requested item could not be found',
'VALIDATION_ERROR': 'Please check your input and try again'
}

def get_user_friendly_message(error_code):
return ERROR_MESSAGES.get(error_code, 'An unexpected error occurred')
```

## Troubleshooting Common Issues

### Authentication Issues

1. **Token expired**: Use refresh token or login again
2. **Invalid API key**: Generate new API key
3. **Permission denied**: Contact admin for proper permissions

### Rate Limiting

1. **Implement exponential backoff**
2. **Cache responses when possible**
3. **Use batch operations for multiple items**

### Network Issues

1. **Check internet connectivity**
2. **Verify API endpoint URL**
3. **Check firewall settings**

### Data Issues

1. **Validate input data format**
2. **Check required fields**
3. **Verify data types and ranges**

## Support and Contact

For persistent errors or issues not covered in this documentation:

- **GitHub Issues**: <https://github.com/pierregrothe/graphrag-api/issues>
- **Email Support**: <pierre@grothe.ca>
- **Documentation**: <https://docs.graphrag.com>

When reporting errors, please include:

- Error code and message
- Request ID (if available)
- Steps to reproduce
- Expected vs actual behavior
