"""CSRF Protection Middleware for GraphRAG API Service.

This module provides Cross-Site Request Forgery (CSRF) protection for the GraphRAG API service.
It implements token-based CSRF protection for state-changing operations.
"""

import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF Protection Middleware.

    Provides CSRF protection for state-changing HTTP methods (POST, PUT, PATCH, DELETE).
    Uses double-submit cookie pattern with HMAC-signed tokens.
    """

    def __init__(self, app, secret_key: str | None = None, token_lifetime: int = 3600):
        """Initialize CSRF protection middleware.

        Args:
            app: FastAPI application instance
            secret_key: Secret key for HMAC signing (defaults to app secret)
            token_lifetime: Token lifetime in seconds (default: 1 hour)
        """
        super().__init__(app)
        # Ensure secret_key is always a string
        self.secret_key: str
        if secret_key:
            self.secret_key = secret_key
        else:
            self.secret_key = str(getattr(settings, "SECRET_KEY", "default-csrf-secret"))
        self.token_lifetime: int = token_lifetime
        self.csrf_header_name: str = "X-CSRF-Token"
        self.csrf_cookie_name: str = "csrf_token"

        # Methods that require CSRF protection
        self.protected_methods = {"POST", "PUT", "PATCH", "DELETE"}

        # Paths exempt from CSRF protection (API endpoints with API key auth)
        self.exempt_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/info",
            "/api/workspaces",  # Workspace management endpoints
            "/api/v1/workspaces",
            "/api/graphql",  # GraphQL endpoint
            "/api/v1/graphql",
        }

    async def dispatch(self, request: Request, call_next):
        """Process request with CSRF protection."""
        # Skip CSRF protection for test environments
        if getattr(settings, "TESTING", False) or getattr(settings, "DEBUG", False):
            return await call_next(request)

        # Skip CSRF protection for exempt paths and safe methods
        if self._is_exempt_path(request.url.path) or request.method not in self.protected_methods:
            return await call_next(request)

        # Skip CSRF protection for API key authenticated requests
        if self._is_api_key_request(request):
            return await call_next(request)

        # Validate CSRF token for protected requests
        if not self._validate_csrf_token(request):
            logger.warning(  # nosemgrep: python-logger-credential-disclosure
                "CSRF token validation failed for %s %s from %s",
                request.method,
                request.url.path,
                self._get_client_ip(request),
            )
            raise HTTPException(status_code=403, detail="CSRF token validation failed")

        response = await call_next(request)

        # Set CSRF token cookie for authenticated users
        if hasattr(request.state, "user") and request.state.user:
            self._set_csrf_cookie(response)

        return response

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        if path in self.exempt_paths:
            return True

        # Check for path patterns
        exempt_patterns = [
            "/api/workspaces",
            "/api/v1/workspaces",
            "/api/graphql",
            "/api/v1/graphql",
        ]

        for pattern in exempt_patterns:
            if path.startswith(pattern):
                return True

        return False

    def _is_api_key_request(self, request: Request) -> bool:
        """Check if request uses API key authentication."""
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Bearer ") or "X-API-Key" in request.headers

    def _validate_csrf_token(self, request: Request) -> bool:
        """Validate CSRF token from header and cookie."""
        # Get token from header
        header_token = request.headers.get(self.csrf_header_name)
        if not header_token:
            return False

        # Get token from cookie
        cookie_token = request.cookies.get(self.csrf_cookie_name)
        if not cookie_token:
            return False

        # Tokens must match
        if not hmac.compare_digest(header_token, cookie_token):
            return False

        # Validate token signature and expiration
        return self._verify_token(header_token)

    def _verify_token(self, token: str) -> bool:
        """Verify CSRF token signature and expiration."""
        try:
            # Token format: timestamp:random_data:signature
            parts = token.split(":")
            if len(parts) != 3:
                return False

            timestamp_str, random_data, signature = parts
            timestamp = int(timestamp_str)

            # Check token expiration
            if time.time() - timestamp > self.token_lifetime:
                return False

            # Verify signature
            expected_signature = self._generate_signature(timestamp_str, random_data)
            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, TypeError):
            return False

    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        timestamp = str(int(time.time()))
        random_data = secrets.token_urlsafe(16)
        signature = self._generate_signature(timestamp, random_data)
        return f"{timestamp}:{random_data}:{signature}"

    def _generate_signature(self, timestamp: str, random_data: str) -> str:
        """Generate HMAC signature for token components."""
        message = f"{timestamp}:{random_data}"
        # self.secret_key is always a string due to initialization
        secret_key_bytes: bytes = self.secret_key.encode()
        return hmac.new(secret_key_bytes, message.encode(), hashlib.sha256).hexdigest()

    def _set_csrf_cookie(self, response: Response) -> None:
        """Set CSRF token cookie in response."""
        token = self._generate_csrf_token()
        response.set_cookie(
            key=self.csrf_cookie_name,
            value=token,
            max_age=self.token_lifetime,
            httponly=True,
            secure=True,  # HTTPS only in production
            samesite="strict",
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        client = request.client
        if client:
            return client.host

        return "unknown"


def get_csrf_token_endpoint(request: Request) -> dict:
    """Endpoint to get CSRF token for authenticated users.

    This endpoint can be called by frontend applications to obtain
    a CSRF token for subsequent state-changing requests.
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Generate new CSRF token
    middleware = CSRFProtectionMiddleware(None)
    token = middleware._generate_csrf_token()

    return {
        "csrf_token": token,
        "header_name": middleware.csrf_header_name,
        "expires_in": middleware.token_lifetime,
    }
