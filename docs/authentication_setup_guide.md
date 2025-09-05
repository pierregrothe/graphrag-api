# GraphRAG API Authentication Setup Guide

## Overview

This guide walks you through setting up and configuring the GraphRAG API authentication system. The system provides enterprise-grade security with JWT tokens, user management, and comprehensive security features.

## Prerequisites

- Python 3.8+
- FastAPI application
- SQLite database (or compatible database)
- Required Python packages (see requirements.txt)

## Installation

### 1. Install Dependencies

```bash
pip install fastapi uvicorn passlib[bcrypt] python-jose[cryptography] python-multipart
```

### 2. Database Setup

The authentication system uses SQLite by default. The database will be automatically initialized on first run.

```python
# Database will be created at the configured path
DATABASE_PATH = "data/graphrag.db"
```

### 3. Environment Configuration

Create a `.env` file with the following configuration:

```env
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration
DATABASE_PATH=data/graphrag.db

# Security Configuration
ENVIRONMENT=development
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Rate Limiting Configuration
LOGIN_RATE_LIMIT=5
LOGIN_RATE_WINDOW=300
REGISTER_RATE_LIMIT=3
REGISTER_RATE_WINDOW=3600
```

## Configuration Options

### JWT Settings

```python
class JWTConfig:
    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
```

**Important**: Change the `secret_key` in production to a secure random string.

### Password Requirements

Configure password validation rules:

```python
class PasswordConfig:
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    max_length: int = 128
```

### Rate Limiting

Configure rate limits for different endpoints:

```python
# Login rate limiting
LOGIN_LIMIT = 5  # attempts
LOGIN_WINDOW = 300  # seconds (5 minutes)

# Registration rate limiting
REGISTER_LIMIT = 3  # attempts
REGISTER_WINDOW = 3600  # seconds (1 hour)

# General auth endpoints
GENERAL_LIMIT = 100  # requests
GENERAL_WINDOW = 3600  # seconds (1 hour)
```

### CORS Configuration

Configure CORS based on your environment:

```python
# Production CORS (restrictive)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]

# Development CORS (permissive)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000"
]
```

## Deployment Setup

### 1. Production Environment Variables

```env
# Production JWT Configuration
JWT_SECRET_KEY=your-production-secret-key-256-bits-minimum
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Production Database
DATABASE_PATH=/app/data/graphrag.db

# Production Security
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Production Rate Limiting (stricter)
LOGIN_RATE_LIMIT=3
LOGIN_RATE_WINDOW=600
REGISTER_RATE_LIMIT=2
REGISTER_RATE_WINDOW=7200
```

### 2. Security Considerations

#### JWT Secret Key

- Use a cryptographically secure random key
- Minimum 256 bits (32 characters)
- Never commit to version control
- Rotate periodically

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Database Security

- Use proper file permissions (600) for database file
- Regular backups
- Consider encryption at rest for sensitive data

#### HTTPS Configuration

- Always use HTTPS in production
- Configure proper SSL/TLS certificates
- Enable HSTS headers

### 3. Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY docs/ ./docs/

# Create data directory
RUN mkdir -p /app/data

# Set proper permissions
RUN chmod 600 /app/data

EXPOSE 8000

CMD ["uvicorn", "src.graphrag_api_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing the Setup

### 1. Basic Functionality Test

```python
import requests

# Test registration
response = requests.post('http://localhost:8000/auth/register', json={
    'username': 'testuser',
    'email': 'test@example.com',
    'password': 'SecurePass123!',
    'full_name': 'Test User'
})

print(f"Registration: {response.status_code}")

# Test login
response = requests.post('http://localhost:8000/auth/login', json={
    'email': 'test@example.com',
    'password': 'SecurePass123!'
})

print(f"Login: {response.status_code}")
if response.status_code == 200:
    tokens = response.json()
    print(f"Access token received: {bool(tokens.get('access_token'))}")
```

### 2. Run Test Suite

```bash
# Run all authentication tests
pytest tests/test_auth* -v

# Run specific test categories
pytest tests/test_auth_system.py::TestUserRepository -v
pytest tests/test_auth_integration.py::TestAuthenticationFlow -v
```

### 3. Security Headers Test

```bash
curl -I http://localhost:8000/auth/profile
```

Should return headers like:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

## Monitoring and Maintenance

### 1. Security Monitoring

The system provides built-in security monitoring:

```python
from src.graphrag_api_service.security.logging import get_security_logger

security_logger = get_security_logger()

# Get security status
status = security_logger.get_security_status()
print(f"Failed attempts last hour: {status['failed_attempts_last_hour']}")
print(f"Active threats: {status['active_threats']}")
print(f"Blocked IPs: {status['blocked_ips']}")
```

### 2. Database Maintenance

```python
# Check database health
from src.graphrag_api_service.database.sqlite_models import SQLiteManager

db_manager = SQLiteManager("data/graphrag.db")
await db_manager.initialize()

# Check user count
user_count = await db_manager.execute_query(
    "SELECT COUNT(*) FROM users WHERE is_active = 1"
)
print(f"Active users: {user_count[0][0]}")
```

### 3. Log Monitoring

Monitor authentication logs for:

- Failed login attempts
- Rate limit violations
- Security violations
- Token refresh patterns

```bash
# Monitor security logs
tail -f logs/security.log | grep "authentication_failed"
```

## Troubleshooting

### Common Issues

#### 1. "Database not initialized"

```bash
# Solution: Initialize database manually
python -c "
import asyncio
from src.graphrag_api_service.database.sqlite_models import SQLiteManager

async def init_db():
    db = SQLiteManager('data/graphrag.db')
    await db.initialize()
    print('Database initialized')

asyncio.run(init_db())
"
```

#### 2. "JWT decode error"

- Check JWT_SECRET_KEY is set correctly
- Verify token hasn't expired
- Ensure algorithm matches configuration

#### 3. "Rate limit exceeded"

- Check rate limit configuration
- Wait for rate limit window to reset
- Consider adjusting limits for your use case

#### 4. "CORS error"

- Verify CORS_ALLOWED_ORIGINS includes your frontend URL
- Check protocol (http vs https)
- Ensure no trailing slashes in origins

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("graphrag.security").setLevel(logging.DEBUG)
logging.getLogger("AuthService").setLevel(logging.DEBUG)
```

### Health Check Endpoint

Create a health check to verify system status:

```python
@app.get("/health/auth")
async def auth_health_check():
    try:
        # Test database connection
        db_manager = await get_db_manager()
        await db_manager.execute_query("SELECT 1")

        # Test JWT manager
        jwt_manager = await get_jwt_manager()
        test_token = jwt_manager.create_access_token({"sub": "health_check"})

        return {
            "status": "healthy",
            "database": "connected",
            "jwt": "functional",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat()
        }
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
```

### 2. Caching

Consider implementing caching for:

- User profile data
- JWT token validation
- Rate limit counters

### 3. Connection Pooling

For high-traffic applications, implement connection pooling:

```python
# Use connection pooling for database
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
```

## Security Best Practices

1. **Regular Security Audits**
   - Review authentication logs
   - Monitor for suspicious patterns
   - Update dependencies regularly

2. **Token Management**
   - Use short-lived access tokens
   - Implement proper token rotation
   - Blacklist compromised tokens

3. **Password Security**
   - Enforce strong password policies
   - Consider implementing password history
   - Monitor for credential stuffing attacks

4. **Rate Limiting**
   - Implement progressive delays
   - Use IP-based and user-based limits
   - Monitor for distributed attacks

5. **Monitoring and Alerting**
   - Set up alerts for security events
   - Monitor authentication metrics
   - Implement automated responses to threats

## Support and Resources

- **API Documentation**: `docs/authentication_api.md`
- **Troubleshooting Guide**: `docs/authentication_troubleshooting.md`
- **Test Examples**: `tests/test_auth_*.py`
- **Security Logging**: `src/graphrag_api_service/security/logging.py`
- **Configuration**: `src/graphrag_api_service/config.py`

For additional support, review the troubleshooting section or contact the development team with specific error details and logs.
