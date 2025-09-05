# GraphRAG API Authentication Troubleshooting Guide

## Common Issues and Solutions

### Authentication Errors

#### 1. "Invalid email or password"

**Symptoms:**
- Login returns 401 Unauthorized
- Error message: "Invalid email or password"

**Possible Causes:**
- Incorrect credentials
- User account doesn't exist
- Password doesn't meet requirements
- Account is deactivated

**Solutions:**
```bash
# Check if user exists in database
python -c "
import asyncio
from src.graphrag_api_service.repositories.user_repository import UserRepository
from src.graphrag_api_service.database.sqlite_models import SQLiteManager

async def check_user():
    db = SQLiteManager('data/graphrag.db')
    await db.initialize()
    repo = UserRepository(db)
    user = await repo.get_user_by_email('user@example.com')
    print(f'User exists: {user is not None}')
    if user:
        print(f'User active: {user.is_active}')

asyncio.run(check_user())
"
```

#### 2. "Token expired" or "Invalid token"

**Symptoms:**
- API requests return 401 Unauthorized
- Error message mentions token expiration

**Possible Causes:**
- Access token has expired (30 minutes default)
- Token was blacklisted
- JWT secret key changed
- Token format is incorrect

**Solutions:**
```python
# Use refresh token to get new access token
import requests

response = requests.post('http://localhost:8000/auth/refresh', json={
    'refresh_token': 'your_refresh_token_here'
})

if response.status_code == 200:
    new_tokens = response.json()
    print(f"New access token: {new_tokens['access_token']}")
else:
    print("Refresh token expired, need to login again")
```

#### 3. "Rate limit exceeded"

**Symptoms:**
- HTTP 429 Too Many Requests
- Headers show rate limit information

**Possible Causes:**
- Too many requests in short time period
- Brute force attack detection
- Misconfigured rate limits

**Solutions:**
```python
# Check rate limit status
response = requests.post('http://localhost:8000/auth/login', json={
    'email': 'test@example.com',
    'password': 'wrong_password'
})

print(f"Rate limit remaining: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Rate limit reset: {response.headers.get('X-RateLimit-Reset')}")
print(f"Retry after: {response.headers.get('Retry-After')} seconds")

# Wait for rate limit to reset or contact admin to reset
```

### Database Issues

#### 1. "Database not initialized"

**Symptoms:**
- Application fails to start
- Database connection errors

**Solutions:**
```bash
# Initialize database manually
python -c "
import asyncio
from src.graphrag_api_service.database.sqlite_models import SQLiteManager

async def init_db():
    db = SQLiteManager('data/graphrag.db')
    await db.initialize()
    print('Database initialized successfully')

asyncio.run(init_db())
"
```

#### 2. "Database locked" or "Database is busy"

**Symptoms:**
- SQLite database lock errors
- Timeout errors during database operations

**Solutions:**
```bash
# Check for long-running transactions
lsof data/graphrag.db

# Restart the application
# Ensure proper connection cleanup in code
```

### Configuration Issues

#### 1. "JWT decode error"

**Symptoms:**
- Token validation fails
- JWT decode errors in logs

**Possible Causes:**
- JWT_SECRET_KEY not set or changed
- Algorithm mismatch
- Token format corruption

**Solutions:**
```bash
# Check JWT configuration
python -c "
import os
from src.graphrag_api_service.config import get_settings

settings = get_settings()
print(f'JWT Secret Key set: {bool(settings.jwt_secret_key)}')
print(f'JWT Algorithm: {settings.jwt_algorithm}')
"

# Regenerate secret key if needed
python -c "import secrets; print(f'New secret key: {secrets.token_urlsafe(32)}')"
```

#### 2. "CORS error"

**Symptoms:**
- Browser console shows CORS errors
- Preflight requests fail

**Solutions:**
```python
# Check CORS configuration
import os
print(f"CORS Origins: {os.getenv('CORS_ALLOWED_ORIGINS', 'Not set')}")
print(f"Environment: {os.getenv('ENVIRONMENT', 'Not set')}")

# Update CORS origins in .env file
# CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Security Issues

#### 1. "Suspicious activity detected"

**Symptoms:**
- Security alerts in logs
- IP addresses blocked
- Multiple failed login attempts

**Solutions:**
```python
# Check security status
from src.graphrag_api_service.security.logging import get_security_logger

security_logger = get_security_logger()
status = security_logger.get_security_status()

print(f"Active threats: {status['active_threats']}")
print(f"Blocked IPs: {status['blocked_ips']}")
print(f"Recent alerts: {status['recent_alerts']}")

# Unblock IP if legitimate
security_logger.unblock_ip('192.168.1.100')
```

#### 2. "Password validation failed"

**Symptoms:**
- Registration fails with password errors
- Password requirements not met

**Solutions:**
```python
# Test password strength
from src.graphrag_api_service.utils.security import PasswordValidator

validator = PasswordValidator()
password = "your_password_here"
is_valid, message = validator.validate_password_strength(password)

print(f"Password valid: {is_valid}")
print(f"Message: {message}")

# Password requirements:
# - Minimum 8 characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one number
# - At least one special character
```

## Diagnostic Tools

### 1. Health Check Script

```python
#!/usr/bin/env python3
# health_check.py

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def health_check():
    """Comprehensive health check for authentication system."""
    print("🏥 GraphRAG Authentication Health Check")
    print("=" * 50)

    # Check database
    try:
        from src.graphrag_api_service.database.sqlite_models import SQLiteManager
        db = SQLiteManager('data/graphrag.db')
        await db.initialize()
        result = await db.execute_query("SELECT COUNT(*) FROM users")
        print(f"✅ Database: Connected ({result[0][0]} users)")
    except Exception as e:
        print(f"❌ Database: {e}")

    # Check JWT configuration
    try:
        from src.graphrag_api_service.config import get_settings
        settings = get_settings()
        print(f"✅ JWT: Configured (algorithm: {settings.jwt_algorithm})")
    except Exception as e:
        print(f"❌ JWT: {e}")

    # Check security logger
    try:
        from src.graphrag_api_service.security.logging import get_security_logger
        logger = get_security_logger()
        status = logger.get_security_status()
        print(f"✅ Security: Active (threats: {status['active_threats']})")
    except Exception as e:
        print(f"❌ Security: {e}")

    print("=" * 50)
    print("Health check complete")

if __name__ == "__main__":
    asyncio.run(health_check())
```

### 2. User Management Script

```python
#!/usr/bin/env python3
# user_management.py

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def list_users():
    """List all users in the system."""
    from src.graphrag_api_service.database.sqlite_models import SQLiteManager

    db = SQLiteManager('data/graphrag.db')
    await db.initialize()

    users = await db.execute_query("""
        SELECT user_id, username, email, is_active, created_at, last_login_at
        FROM users
        ORDER BY created_at DESC
    """)

    print("👥 User List")
    print("-" * 80)
    for user in users:
        status = "Active" if user[3] else "Inactive"
        print(f"{user[1]:<20} {user[2]:<30} {status:<10} {user[4]}")

async def deactivate_user(email):
    """Deactivate a user account."""
    from src.graphrag_api_service.database.sqlite_models import SQLiteManager

    db = SQLiteManager('data/graphrag.db')
    await db.initialize()

    await db.execute_query(
        "UPDATE users SET is_active = 0 WHERE email = ?",
        (email,)
    )
    print(f"User {email} deactivated")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            asyncio.run(list_users())
        elif sys.argv[1] == "deactivate" and len(sys.argv) > 2:
            asyncio.run(deactivate_user(sys.argv[2]))
    else:
        print("Usage: python user_management.py [list|deactivate <email>]")
```

### 3. Security Audit Script

```python
#!/usr/bin/env python3
# security_audit.py

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def security_audit():
    """Perform security audit of authentication system."""
    print("🔒 Security Audit Report")
    print("=" * 50)

    # Check for weak passwords (in a real system, you wouldn't store plaintext)
    from src.graphrag_api_service.database.sqlite_models import SQLiteManager
    db = SQLiteManager('data/graphrag.db')
    await db.initialize()

    # Check user activity
    users = await db.execute_query("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
               SUM(CASE WHEN last_login_at IS NULL THEN 1 ELSE 0 END) as never_logged_in
        FROM users
    """)

    total, active, never_logged_in = users[0]
    print(f"📊 User Statistics:")
    print(f"   Total users: {total}")
    print(f"   Active users: {active}")
    print(f"   Never logged in: {never_logged_in}")

    # Check security events
    from src.graphrag_api_service.security.logging import get_security_logger
    logger = get_security_logger()
    status = logger.get_security_status()

    print(f"\n🚨 Security Status:")
    print(f"   Failed attempts (last hour): {status['failed_attempts_last_hour']}")
    print(f"   Active threats: {status['active_threats']}")
    print(f"   Blocked IPs: {status['blocked_ips']}")
    print(f"   Recent alerts: {status['recent_alerts']}")

    # Recommendations
    print(f"\n💡 Recommendations:")
    if never_logged_in > 0:
        print(f"   - Review {never_logged_in} users who never logged in")
    if status['active_threats'] > 0:
        print(f"   - Investigate {status['active_threats']} active threats")
    if status['blocked_ips'] > 10:
        print(f"   - Review blocked IPs list ({status['blocked_ips']} total)")

if __name__ == "__main__":
    asyncio.run(security_audit())
```

## Performance Issues

### 1. Slow Authentication

**Symptoms:**
- Login/registration takes too long
- Database queries are slow

**Solutions:**
```sql
-- Add database indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Analyze query performance
EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'user@example.com';
```

### 2. High Memory Usage

**Symptoms:**
- Application memory usage grows over time
- Out of memory errors

**Solutions:**
```python
# Check for connection leaks
import gc
from src.graphrag_api_service.database.sqlite_models import SQLiteManager

# Ensure proper connection cleanup
async def check_connections():
    db = SQLiteManager('data/graphrag.db')
    await db.initialize()
    # Always close connections
    await db.close()

# Monitor memory usage
import psutil
process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## Getting Help

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging for authentication components
logging.getLogger("graphrag.security").setLevel(logging.DEBUG)
logging.getLogger("AuthService").setLevel(logging.DEBUG)
logging.getLogger("UserRepository").setLevel(logging.DEBUG)

# Add console handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logging.getLogger("graphrag.security").addHandler(handler)
```

### 2. Collect Diagnostic Information

When reporting issues, include:
- Error messages and stack traces
- Configuration settings (without secrets)
- Database schema version
- Python version and dependencies
- Environment details

### 3. Test Isolation

```bash
# Run tests to isolate issues
pytest tests/test_auth_system.py::TestUserRepository::test_create_user -v
pytest tests/test_auth_integration.py::TestAuthenticationFlow::test_complete_login_flow -v
```

### 4. Contact Support

When contacting support, provide:
- Detailed error description
- Steps to reproduce
- Diagnostic script output
- Relevant log entries
- Configuration details (sanitized)

## Prevention

### 1. Regular Maintenance

- Monitor authentication logs daily
- Review security alerts weekly
- Update dependencies monthly
- Rotate JWT secrets quarterly

### 2. Monitoring Setup

```python
# Set up monitoring alerts
def setup_monitoring():
    from src.graphrag_api_service.security.logging import get_security_logger

    logger = get_security_logger()
    status = logger.get_security_status()

    # Alert thresholds
    if status['failed_attempts_last_hour'] > 100:
        send_alert("High failed login attempts")

    if status['active_threats'] > 5:
        send_alert("Multiple active threats detected")
```

### 3. Backup Strategy

```bash
# Regular database backups
cp data/graphrag.db backups/graphrag_$(date +%Y%m%d_%H%M%S).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="backups"
DB_FILE="data/graphrag.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_FILE $BACKUP_DIR/graphrag_$TIMESTAMP.db

# Keep only last 30 backups
ls -t $BACKUP_DIR/graphrag_*.db | tail -n +31 | xargs rm -f
```
