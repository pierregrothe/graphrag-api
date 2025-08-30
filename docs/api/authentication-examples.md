# Authentication Examples

## Overview

The GraphRAG API supports two authentication methods:

1. **JWT Tokens**: For user-based authentication with role-based access control
2. **API Keys**: For service-to-service authentication with configurable permissions

## JWT Token Authentication

### Python Examples

#### Basic Login and Token Usage

```python
import requests
import json

# Login to get JWT token
def login(username, password, base_url="http://localhost:8000"):
"""Login and get JWT token"""
login_data = {
"username": username,
"password": password
}

response = requests.post(
f"{base_url}/auth/login",
json=login_data,
headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
return response.json()
else:
raise Exception(f"Login failed: {response.text}")

# Use JWT token for API calls
def get_entities_with_jwt(token, base_url="http://localhost:8000"):
"""Get entities using JWT token"""
headers = {
"Authorization": f"Bearer {token}",
"Content-Type": "application/json"
}

response = requests.get(
f"{base_url}/api/entities",
headers=headers
)

return response.json()

# Example usage
try:
# Login
auth_response = login("admin", "secure_password")
access_token = auth_response["access_token"]

# Use token
entities = get_entities_with_jwt(access_token)
print(f"Found {len(entities.get('entities', []))} entities")

except Exception as e:
print(f"Error: {e}")
```

#### JWT Token Refresh

```python
def refresh_token(refresh_token, base_url="http://localhost:8000"):
"""Refresh JWT access token"""
refresh_data = {
"refresh_token": refresh_token
}

response = requests.post(
f"{base_url}/auth/refresh",
json=refresh_data,
headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
return response.json()
else:
raise Exception(f"Token refresh failed: {response.text}")

# Example with automatic token refresh
class GraphRAGClient:
def __init__(self, base_url="http://localhost:8000"):
self.base_url = base_url
self.access_token = None
self.refresh_token = None

def login(self, username, password):
"""Login and store tokens"""
auth_response = login(username, password, self.base_url)
self.access_token = auth_response["access_token"]
self.refresh_token = auth_response["refresh_token"]

def _make_request(self, method, endpoint, **kwargs):
"""Make authenticated request with automatic token refresh"""
headers = kwargs.get("headers", {})
headers["Authorization"] = f"Bearer {self.access_token}"
kwargs["headers"] = headers

response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)

# If token expired, try to refresh
if response.status_code == 401 and self.refresh_token:
try:
auth_response = refresh_token(self.refresh_token, self.base_url)
self.access_token = auth_response["access_token"]

# Retry request with new token
headers["Authorization"] = f"Bearer {self.access_token}"
response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
except Exception:
raise Exception("Token refresh failed, please login again")

return response

def get_entities(self, **params):
"""Get entities with automatic authentication"""
response = self._make_request("GET", "/api/entities", params=params)
return response.json()

# Usage
client = GraphRAGClient()
client.login("admin", "secure_password")
entities = client.get_entities(limit=50)
```

### JavaScript/Node.js Examples

#### Basic JWT Authentication

```javascript
const axios = require('axios');

class GraphRAGClient {
constructor(baseURL = 'http://localhost:8000') {
this.baseURL = baseURL;
this.accessToken = null;
this.refreshToken = null;

// Create axios instance with interceptors
this.client = axios.create({
baseURL: this.baseURL,
headers: {
'Content-Type': 'application/json'
}
});

// Request interceptor to add auth header
this.client.interceptors.request.use(
(config) => {
if (this.accessToken) {
config.headers.Authorization = `Bearer ${this.accessToken}`;
}
return config;
},
(error) => Promise.reject(error)
);

// Response interceptor for token refresh
this.client.interceptors.response.use(
(response) => response,
async (error) => {
if (error.response?.status === 401 && this.refreshToken) {
try {
await this.refreshAccessToken();
// Retry original request
return this.client.request(error.config);
} catch (refreshError) {
throw new Error('Token refresh failed, please login again');
}
}
return Promise.reject(error);
}
);
}

async login(username, password) {
try {
const response = await axios.post(`${this.baseURL}/auth/login`, {
username,
password
});

this.accessToken = response.data.access_token;
this.refreshToken = response.data.refresh_token;

return response.data;
} catch (error) {
throw new Error(`Login failed: ${error.response?.data?.message || error.message}`);
}
}

async refreshAccessToken() {
const response = await axios.post(`${this.baseURL}/auth/refresh`, {
refresh_token: this.refreshToken
});

this.accessToken = response.data.access_token;
return response.data;
}

async getEntities(params = {}) {
const response = await this.client.get('/api/entities', { params });
return response.data;
}

async getEntity(entityId) {
const response = await this.client.get(`/api/entities/${entityId}`);
return response.data;
}
}

// Usage example
async function example() {
const client = new GraphRAGClient();

try {
// Login
await client.login('admin', 'secure_password');
console.log('Login successful');

// Get entities
const entities = await client.getEntities({ limit: 10 });
console.log(`Found ${entities.entities.length} entities`);

// Get specific entity
if (entities.entities.length > 0) {
const entity = await client.getEntity(entities.entities[0].id);
console.log('Entity details:', entity);
}

} catch (error) {
console.error('Error:', error.message);
}
}

example();
```

#### GraphQL with JWT

```javascript
const { GraphQLClient } = require('graphql-request');

class GraphQLGraphRAGClient {
constructor(endpoint = 'http://localhost:8000/graphql') {
this.endpoint = endpoint;
this.client = new GraphQLClient(endpoint);
}

async login(username, password) {
// Login via REST API to get token
const response = await axios.post('http://localhost:8000/auth/login', {
username,
password
});

const token = response.data.access_token;

// Set authorization header for GraphQL client
this.client.setHeader('Authorization', `Bearer ${token}`);

return response.data;
}

async getEntities(first = 10) {
const query = `
query GetEntities($first: Int) {
entities(first: $first) {
edges {
node {
id
title
type
description
}
}
totalCount
}
}
`;

return await this.client.request(query, { first });
}

async subscribeToEntityUpdates() {
const subscription = `
subscription {
entityUpdates {
id
title
action
}
}
`;

// Note: For subscriptions, you'd typically use a WebSocket client
// This is a simplified example
return subscription;
}
}
```

### cURL Examples

#### JWT Login and Usage

```bash
#!/bin/bash

# Login to get JWT token
LOGIN_RESPONSE=$(curl -s -X POST \
http://localhost:8000/auth/login \
-H "Content-Type: application/json" \
-d '{
"username": "admin",
"password": "secure_password"
}')

# Extract access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" = "null" ]; then
echo "Login failed"
exit 1
fi

echo "Login successful, token: ${ACCESS_TOKEN:0:20}..."

# Use token to get entities
curl -X GET \
http://localhost:8000/api/entities \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json"

# GraphQL query with JWT
curl -X POST \
http://localhost:8000/graphql \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"query": "query { entities(first: 5) { edges { node { id title type } } } }"
}'
```

## API Key Authentication

### Python Examples

#### Create and Use API Key

```python
import requests

def create_api_key(jwt_token, name, permissions, base_url="http://localhost:8000"):
"""Create a new API key"""
headers = {
"Authorization": f"Bearer {jwt_token}",
"Content-Type": "application/json"
}

data = {
"name": name,
"permissions": permissions,
"rate_limit": 1000,
"expires_in_days": 365
}

response = requests.post(
f"{base_url}/auth/api-keys",
json=data,
headers=headers
)

return response.json()

def use_api_key(api_key, base_url="http://localhost:8000"):
"""Use API key for authentication"""
headers = {
"X-API-Key": api_key,
"Content-Type": "application/json"
}

response = requests.get(
f"{base_url}/api/entities",
headers=headers
)

return response.json()

# Example usage
try:
# First login to get JWT token
auth_response = login("admin", "secure_password")
jwt_token = auth_response["access_token"]

# Create API key
api_key_response = create_api_key(
jwt_token,
"Production API Key",
["read:entities", "read:relationships", "read:communities"]
)

api_key = api_key_response["key"]
print(f"Created API key: {api_key_response['prefix']}...")

# Use API key
entities = use_api_key(api_key)
print(f"Found {len(entities.get('entities', []))} entities using API key")

except Exception as e:
print(f"Error: {e}")
```

### JavaScript Examples

```javascript
class APIKeyClient {
constructor(apiKey, baseURL = 'http://localhost:8000') {
this.apiKey = apiKey;
this.baseURL = baseURL;

this.client = axios.create({
baseURL: this.baseURL,
headers: {
'X-API-Key': this.apiKey,
'Content-Type': 'application/json'
}
});
}

async getEntities(params = {}) {
const response = await this.client.get('/api/entities', { params });
return response.data;
}

async getRelationships(params = {}) {
const response = await this.client.get('/api/relationships', { params });
return response.data;
}

async graphqlQuery(query, variables = {}) {
const response = await this.client.post('/graphql', {
query,
variables
});
return response.data;
}
}

// Usage
const apiClient = new APIKeyClient('grag_abcd1234...');

async function example() {
try {
const entities = await apiClient.getEntities({ limit: 10 });
console.log('Entities:', entities);

const graphqlResult = await apiClient.graphqlQuery(`
query {
entities(first: 5) {
edges {
node {
id
title
type
}
}
}
}
`);
console.log('GraphQL result:', graphqlResult);

} catch (error) {
console.error('Error:', error.message);
}
}
```

### cURL Examples

```bash
#!/bin/bash

# Set your API key
API_KEY="grag_abcd1234efgh5678ijkl9012mnop3456"

# Get entities using API key
curl -X GET \
http://localhost:8000/api/entities \
-H "X-API-Key: $API_KEY" \
-H "Content-Type: application/json"

# GraphQL query using API key
curl -X POST \
http://localhost:8000/graphql \
-H "X-API-Key: $API_KEY" \
-H "Content-Type: application/json" \
-d '{
"query": "query GetEntities($first: Int) { entities(first: $first) { edges { node { id title type } } } }",
"variables": { "first": 10 }
}'

# Get performance metrics
curl -X GET \
http://localhost:8000/metrics/performance \
-H "X-API-Key: $API_KEY"
```

## Error Handling Examples

### Python Error Handling

```python
import requests
from requests.exceptions import RequestException

def handle_api_errors(response):
"""Handle common API errors"""
if response.status_code == 401:
raise Exception("Authentication failed - check your credentials")
elif response.status_code == 403:
raise Exception("Permission denied - insufficient privileges")
elif response.status_code == 429:
raise Exception("Rate limit exceeded - please wait before retrying")
elif response.status_code >= 400:
error_data = response.json() if response.content else {}
raise Exception(f"API error {response.status_code}: {error_data.get('message', 'Unknown error')}")

def safe_api_call(func, *args, **kwargs):
"""Make API call with error handling"""
try:
response = func(*args, **kwargs)
handle_api_errors(response)
return response.json()
except RequestException as e:
raise Exception(f"Network error: {e}")
except ValueError as e:
raise Exception(f"Invalid JSON response: {e}")

# Usage
try:
result = safe_api_call(
requests.get,
"http://localhost:8000/api/entities",
headers={"X-API-Key": "your_api_key"}
)
print("Success:", result)
except Exception as e:
print("Error:", e)
```

### JavaScript Error Handling

```javascript
class APIError extends Error {
constructor(message, status, details) {
super(message);
this.name = 'APIError';
this.status = status;
this.details = details;
}
}

function handleAPIError(error) {
if (error.response) {
const { status, data } = error.response;

switch (status) {
case 401:
throw new APIError('Authentication failed', status, data);
case 403:
throw new APIError('Permission denied', status, data);
case 429:
throw new APIError('Rate limit exceeded', status, data);
default:
throw new APIError(
data.message || 'API error occurred',
status,
data
);
}
} else if (error.request) {
throw new APIError('Network error - no response received', 0, error.request);
} else {
throw new APIError('Request setup error', 0, error.message);
}
}

// Usage with async/await
async function safeAPICall(apiFunction) {
try {
return await apiFunction();
} catch (error) {
handleAPIError(error);
}
}
```

## Best Practices

### 1. Token Storage and Security

```python
# Good - use environment variables or secure storage
import os
from keyring import get_password, set_password

# Store tokens securely
def store_token_securely(token, service="graphrag_api", username="default"):
set_password(service, username, token)

def get_stored_token(service="graphrag_api", username="default"):
return get_password(service, username)

# Bad - don't hardcode tokens
# api_key = "grag_abcd1234..." # Never do this
```

### 2. Rate Limiting Handling

```python
import time
from functools import wraps

def retry_on_rate_limit(max_retries=3, backoff_factor=2):
def decorator(func):
@wraps(func)
def wrapper(*args, **kwargs):
for attempt in range(max_retries):
try:
return func(*args, **kwargs)
except Exception as e:
if "rate limit" in str(e).lower() and attempt < max_retries - 1:
wait_time = backoff_factor ** attempt
print(f"Rate limited, waiting {wait_time} seconds...")
time.sleep(wait_time)
continue
raise
return None
return wrapper
return decorator

@retry_on_rate_limit()
def get_entities_with_retry(api_key):
# Your API call here
pass
```

### 3. Connection Pooling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
session = requests.Session()

retry_strategy = Retry(
total=3,
backoff_factor=1,
status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

return session

# Use session for all requests
session = create_session_with_retries()
response = session.get("http://localhost:8000/api/entities", headers=headers)
```
