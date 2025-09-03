# 🛡️ Middleware Module

The middleware module provides comprehensive security, performance, and monitoring middleware for enterprise-grade request processing.

## 📁 Module Structure

```
middleware/
├── __init__.py              # Module exports
├── auth.py                 # Authentication middleware
├── cors.py                 # CORS configuration
├── error_handling.py       # Error handling middleware
├── logging.py              # Request logging middleware
├── rate_limiting.py        # Rate limiting middleware
├── security.py             # Security headers middleware
└── README.md               # This documentation
```

## 🔧 Core Components

### Authentication Middleware (`auth.py`)

```python
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from graphrag_api_service.auth.jwt_auth import JWTManager

security = HTTPBearer()
jwt_manager = JWTManager()

async def auth_middleware(request: Request, call_next):
    """Process authentication for all requests."""
    # Skip auth for public endpoints
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Extract and validate token
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = auth_header.split(" ")[1]
    try:
        payload = jwt_manager.verify_token(token)
        request.state.user = payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return await call_next(request)
```

### Rate Limiting (`rate_limiting.py`)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limiting decorators
@limiter.limit("100/minute")
async def api_rate_limit(request: Request):
    """Standard API rate limit."""
    pass

@limiter.limit("10/minute")
async def auth_rate_limit(request: Request):
    """Stricter rate limit for auth endpoints."""
    pass

# Custom rate limit handler
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": exc.retry_after
        }
    )
```

### Security Headers (`security.py`)

```python
from fastapi import Request
from fastapi.responses import Response

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response
```

### Error Handling (`error_handling.py`)

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": request.url.path
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )
```

## 🔐 Security Features

### CORS Configuration (`cors.py`)

```python
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    """Configure CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"]
    )
```

### Request Logging (`logging.py`)

```python
import time
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

async def logging_middleware(request: Request, call_next):
    """Log all requests with timing and user info."""
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Response: {response.status_code} - {duration:.3f}s",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": duration,
            "user": getattr(request.state, "user", {}).get("sub", "anonymous")
        }
    )

    return response
```

## 📊 Performance Monitoring

### Request Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

async def metrics_middleware(request: Request, call_next):
    """Collect request metrics."""
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response
```

## 🧪 Testing

### Middleware Testing

```python
import pytest
from fastapi.testclient import TestClient
from graphrag_api_service.main import app

def test_security_headers():
    client = TestClient(app)
    response = client.get("/health")

    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers

def test_rate_limiting():
    client = TestClient(app)

    # Make requests up to limit
    for _ in range(100):
        response = client.get("/api/workspaces")
        if response.status_code == 429:
            break

    # Should eventually hit rate limit
    assert response.status_code == 429

def test_cors_headers():
    client = TestClient(app)
    response = client.options(
        "/api/workspaces",
        headers={"Origin": "http://localhost:3000"}
    )

    assert "Access-Control-Allow-Origin" in response.headers
```

---

For more information, see the [main documentation](../../../README.md) or other module documentation.
