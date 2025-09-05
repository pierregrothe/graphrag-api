# GraphRAG API Authentication System

## Overview

The GraphRAG API provides a comprehensive authentication system with JWT-based token authentication, user management, and enterprise-grade security features.

## Base URL

```
https://api.graphrag.example.com
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. After successful login, you'll receive:
- **Access Token**: Short-lived token for API requests (30 minutes)
- **Refresh Token**: Long-lived token for obtaining new access tokens (7 days)

### Using Access Tokens

Include the access token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

## Endpoints

### 1. User Registration

Register a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john.doe@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201 Created):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "roles": ["user"],
  "permissions": ["read:workspaces", "create:workspaces"],
  "created_at": "2025-09-05T10:30:00Z",
  "last_login_at": null
}
```

**Error Responses:**
- `400 Bad Request`: User already exists or validation failed
- `422 Unprocessable Entity`: Invalid input data

### 2. User Login

Authenticate and receive access tokens.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "johndoe",
    "email": "john.doe@example.com",
    "roles": ["user"]
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Rate limit exceeded

### 3. Get User Profile

Retrieve the current user's profile information.

**Endpoint:** `GET /auth/profile`

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "roles": ["user"],
  "permissions": ["read:workspaces", "create:workspaces"],
  "created_at": "2025-09-05T10:30:00Z",
  "last_login_at": "2025-09-05T11:15:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired token

### 4. Refresh Access Token

Obtain a new access token using a refresh token.

**Endpoint:** `POST /auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired refresh token

### 5. User Logout

Invalidate the current session and tokens.

**Endpoint:** `POST /auth/logout`

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired token

## Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Login attempts**: 5 attempts per 5 minutes per IP
- **Registration**: 3 attempts per hour per IP
- **General auth endpoints**: 100 requests per hour per IP

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1693920000
X-RateLimit-Window: 300
```

## Security Features

### Security Headers

All responses include comprehensive security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: ...`

### CORS Configuration

CORS is configured based on environment:
- **Production**: Restricted to configured origins
- **Development**: Allows localhost origins
- **Testing**: Allows all origins

### Token Security

- Access tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Tokens are signed with HS256 algorithm
- Blacklisted tokens are rejected

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": {
    "error": "authentication_failed",
    "message": "Invalid email or password",
    "code": 401,
    "timestamp": "2025-09-05T11:30:00Z"
  }
}
```

### Common Error Codes

- `400`: Bad Request - Invalid input or user already exists
- `401`: Unauthorized - Authentication required or failed
- `403`: Forbidden - Insufficient permissions
- `422`: Unprocessable Entity - Validation errors
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Server-side error

## Code Examples

### Python (requests)

```python
import requests

# Register a new user
response = requests.post('https://api.graphrag.example.com/auth/register', json={
    'username': 'johndoe',
    'email': 'john.doe@example.com',
    'password': 'SecurePass123!',
    'full_name': 'John Doe'
})

if response.status_code == 201:
    print("User registered successfully")

# Login
response = requests.post('https://api.graphrag.example.com/auth/login', json={
    'email': 'john.doe@example.com',
    'password': 'SecurePass123!'
})

if response.status_code == 200:
    tokens = response.json()
    access_token = tokens['access_token']
    
    # Use access token for authenticated requests
    headers = {'Authorization': f'Bearer {access_token}'}
    profile = requests.get('https://api.graphrag.example.com/auth/profile', headers=headers)
    print(profile.json())
```

### JavaScript (fetch)

```javascript
// Register a new user
const registerResponse = await fetch('https://api.graphrag.example.com/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'johndoe',
    email: 'john.doe@example.com',
    password: 'SecurePass123!',
    full_name: 'John Doe'
  })
});

if (registerResponse.ok) {
  console.log('User registered successfully');
}

// Login
const loginResponse = await fetch('https://api.graphrag.example.com/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'john.doe@example.com',
    password: 'SecurePass123!'
  })
});

if (loginResponse.ok) {
  const tokens = await loginResponse.json();
  const accessToken = tokens.access_token;
  
  // Use access token for authenticated requests
  const profileResponse = await fetch('https://api.graphrag.example.com/auth/profile', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  const profile = await profileResponse.json();
  console.log(profile);
}
```

### cURL

```bash
# Register a new user
curl -X POST https://api.graphrag.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john.doe@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'

# Login
curl -X POST https://api.graphrag.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
  }'

# Get profile (replace TOKEN with actual access token)
curl -X GET https://api.graphrag.example.com/auth/profile \
  -H "Authorization: Bearer TOKEN"
```

## Testing

The authentication system includes comprehensive test suites:

### Running Tests

```bash
# Run unit tests
pytest tests/test_auth_system.py -v

# Run integration tests
pytest tests/test_auth_integration.py -v

# Run all authentication tests
pytest tests/test_auth* -v
```

### Test Coverage

- User model validation
- Password strength validation
- Rate limiting functionality
- Authentication flows
- Token management
- Security features
- Error handling

## Troubleshooting

### Common Issues

1. **"Invalid email or password"**
   - Verify credentials are correct
   - Check if user account exists
   - Ensure password meets requirements

2. **"Rate limit exceeded"**
   - Wait for rate limit window to reset
   - Check `Retry-After` header for wait time

3. **"Token expired"**
   - Use refresh token to get new access token
   - Re-authenticate if refresh token expired

4. **"User already exists"**
   - Email or username already registered
   - Use different credentials or login instead

### Support

For additional support or questions:
- Check the troubleshooting guide
- Review error messages and codes
- Contact support with specific error details
