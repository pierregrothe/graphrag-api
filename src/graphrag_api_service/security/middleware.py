# src/graphrag_api_service/security/middleware.py
# Basic Security Framework and Middleware
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Basic security framework with CORS, validation, and audit logging."""

import logging
import os
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SecurityConfig(BaseModel):
    """Configuration for security middleware."""

    # CORS settings
    cors_enabled: bool = True
    allowed_origins: list[str] = ["*"]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: list[str] = ["*"]
    allow_credentials: bool = False

    # Rate limiting
    rate_limiting_enabled: bool = True
    requests_per_minute: int = 100
    burst_limit: int = 20

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Disable rate limiting in testing mode
        if os.getenv("TESTING") == "true" or os.getenv("RATE_LIMITING_ENABLED") == "false":
            self.rate_limiting_enabled = False

    # Request validation
    max_request_size_mb: int = 10
    required_headers: list[str] = []
    blocked_user_agents: list[str] = []

    # Security headers
    security_headers_enabled: bool = True
    content_security_policy: str = "default-src 'self'"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"


class AuditLogEntry(BaseModel):
    """Audit log entry structure."""

    timestamp: float
    request_id: str
    method: str
    path: str
    user_agent: str | None
    ip_address: str
    status_code: int
    response_time: float
    error_message: str | None = None
    user_id: str | None = None


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int, burst_limit: int):
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst requests
        """
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client.

        Args:
            client_id: Client identifier (IP address)

        Returns:
            True if request is allowed
        """
        current_time = time.time()
        minute_ago = current_time - 60

        # Initialize client if not exists
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old requests
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id] if req_time > minute_ago
        ]

        # Check rate limits
        recent_requests = len(self._requests[client_id])

        # Check burst limit (last 10 seconds)
        ten_seconds_ago = current_time - 10
        burst_requests = len(
            [req_time for req_time in self._requests[client_id] if req_time > ten_seconds_ago]
        )

        if burst_requests >= self.burst_limit:
            return False

        if recent_requests >= self.requests_per_minute:
            return False

        # Record this request
        self._requests[client_id].append(current_time)
        return True

    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client.

        Args:
            client_id: Client identifier

        Returns:
            Number of remaining requests
        """
        if client_id not in self._requests:
            return self.requests_per_minute

        current_time = time.time()
        minute_ago = current_time - 60

        recent_requests = len(
            [req_time for req_time in self._requests[client_id] if req_time > minute_ago]
        )

        return max(0, self.requests_per_minute - recent_requests)


class RequestValidator:
    """Request validation and sanitization."""

    def __init__(self, config: SecurityConfig):
        """Initialize the request validator.

        Args:
            config: Security configuration
        """
        self.config = config

    def validate_request_size(self, request: Request) -> None:
        """Validate request size.

        Args:
            request: HTTP request

        Raises:
            HTTPException: If request is too large
        """
        content_length = request.headers.get("content-length")
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > self.config.max_request_size_mb:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"Request too large: {size_mb:.1f}MB "
                        f"(max: {self.config.max_request_size_mb}MB)"
                    ),
                )

    def validate_headers(self, request: Request) -> None:
        """Validate required headers.

        Args:
            request: HTTP request

        Raises:
            HTTPException: If required headers are missing
        """
        for header in self.config.required_headers:
            if header.lower() not in [h.lower() for h in request.headers.keys()]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required header: {header}",
                )

    def validate_user_agent(self, request: Request) -> None:
        """Validate user agent.

        Args:
            request: HTTP request

        Raises:
            HTTPException: If user agent is blocked
        """
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked_agent in self.config.blocked_user_agents:
            if blocked_agent.lower() in user_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="User agent not allowed"
                )

    def sanitize_input(self, data: Any) -> Any:
        """Sanitize input data.

        Args:
            data: Input data to sanitize

        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            # Basic XSS prevention
            data = data.replace("<script", "&lt;script")
            data = data.replace("javascript:", "")
            data = data.replace("data:", "")

        elif isinstance(data, dict):
            return {key: self.sanitize_input(value) for key, value in data.items()}

        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]

        return data


class AuditLogger:
    """Audit logging for security events."""

    def __init__(self) -> None:
        """Initialize the audit logger."""
        self._audit_log: list[AuditLogEntry] = []

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        user_agent: str | None,
        ip_address: str,
        status_code: int,
        response_time: float,
        error_message: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log an audit entry.

        Args:
            request_id: Unique request identifier
            method: HTTP method
            path: Request path
            user_agent: User agent string
            ip_address: Client IP address
            status_code: Response status code
            response_time: Response time in seconds
            error_message: Error message if any
            user_id: User identifier if authenticated
        """
        entry = AuditLogEntry(
            timestamp=time.time(),
            request_id=request_id,
            method=method,
            path=path,
            user_agent=user_agent,
            ip_address=ip_address,
            status_code=status_code,
            response_time=response_time,
            error_message=error_message,
            user_id=user_id,
        )

        self._audit_log.append(entry)

        # Keep only recent entries (last 10000)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

        # Log security-relevant events
        if status_code >= 400:
            logger.warning(
                f"Security event - {method} {path} - Status: {status_code} - "
                f"IP: {ip_address} - Error: {error_message}"
            )

    def get_audit_log(self, limit: int = 100) -> list[AuditLogEntry]:
        """Get recent audit log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        return self._audit_log[-limit:].copy()

    def get_security_summary(self) -> dict[str, Any]:
        """Get security summary statistics.

        Returns:
            Security summary
        """
        if not self._audit_log:
            return {}

        recent_entries = self._audit_log[-1000:]  # Last 1000 entries

        # Count by status code
        status_counts: dict[int, int] = {}
        error_counts: dict[str, int] = {}
        ip_counts: dict[str, int] = {}

        for entry in recent_entries:
            status_counts[entry.status_code] = status_counts.get(entry.status_code, 0) + 1

            if entry.status_code >= 400:
                error_counts[entry.path] = error_counts.get(entry.path, 0) + 1

            ip_counts[entry.ip_address] = ip_counts.get(entry.ip_address, 0) + 1

        # Find top error endpoints and IPs
        top_error_endpoints = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_requests": len(recent_entries),
            "status_code_distribution": status_counts,
            "top_error_endpoints": top_error_endpoints,
            "top_client_ips": top_ips,
            "error_rate": sum(1 for e in recent_entries if e.status_code >= 400)
            / len(recent_entries),
        }


class SecurityMiddleware:
    """Main security middleware coordinator."""

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize the security middleware.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()

        # Check for testing mode and adjust rate limiting accordingly
        import os

        testing_env = os.getenv("TESTING", "false").lower()
        rate_limiting_env = os.getenv("RATE_LIMITING_ENABLED", "true").lower()
        is_testing = testing_env == "true" or rate_limiting_env == "false"

        if is_testing:
            # In testing mode, use very high limits or disable completely
            self.rate_limiter = None
        else:
            self.rate_limiter = (
                RateLimiter(self.config.requests_per_minute, self.config.burst_limit)
                if self.config.rate_limiting_enabled
                else None
            )

        self.validator = RequestValidator(self.config)
        self.audit_logger = AuditLogger()

    def get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def add_security_headers(self, response: Response) -> None:
        """Add security headers to response.

        Args:
            response: HTTP response
        """
        if not self.config.security_headers_enabled:
            return

        response.headers["Content-Security-Policy"] = self.config.content_security_policy
        response.headers["X-Frame-Options"] = self.config.x_frame_options
        response.headers["X-Content-Type-Options"] = self.config.x_content_type_options
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    async def process_request(self, request: Request) -> None:
        """Process incoming request with security checks.

        Args:
            request: HTTP request

        Raises:
            HTTPException: If security checks fail
        """
        client_ip = self.get_client_ip(request)

        # Rate limiting - check for testing mode at runtime
        import os

        testing_env = os.getenv("TESTING", "false").lower()
        rate_limiting_env = os.getenv("RATE_LIMITING_ENABLED", "true").lower()
        is_testing = testing_env == "true" or rate_limiting_env == "false"

        if not is_testing and self.rate_limiter and not self.rate_limiter.is_allowed(client_ip):
            remaining = self.rate_limiter.get_remaining_requests(client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60", "X-RateLimit-Remaining": str(remaining)},
            )

        # Request validation
        self.validator.validate_request_size(request)
        self.validator.validate_headers(request)
        self.validator.validate_user_agent(request)

    def get_cors_config(self) -> dict | None:
        """Get CORS configuration for middleware.

        Returns:
            CORS configuration dictionary
        """
        if not self.config.cors_enabled:
            return None

        return {
            "allow_origins": self.config.allowed_origins,
            "allow_credentials": self.config.allow_credentials,
            "allow_methods": self.config.allowed_methods,
            "allow_headers": self.config.allowed_headers,
        }


# Global security middleware instance
_security_middleware: SecurityMiddleware | None = None


def get_security_middleware() -> SecurityMiddleware:
    """Get the global security middleware instance.

    Returns:
        Security middleware instance
    """
    global _security_middleware

    if _security_middleware is None:
        _security_middleware = SecurityMiddleware()

    return _security_middleware


def reset_security_middleware() -> None:
    """Reset the global security middleware instance.

    This is primarily used for testing to ensure a fresh instance
    with updated configuration.
    """
    global _security_middleware
    _security_middleware = None
