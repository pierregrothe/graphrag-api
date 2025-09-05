# src/graphrag_api_service/middleware/rate_limiting.py
# Rate limiting middleware for authentication endpoints
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Rate limiting middleware for GraphRAG API Service authentication endpoints."""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.security import RateLimitHelper

logger = logging.getLogger(__name__)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware specifically for authentication endpoints.

    This middleware applies different rate limits to different authentication
    endpoints to prevent brute force attacks and abuse.
    """

    def __init__(
        self,
        app,
        login_limit: int = 5,
        login_window: int = 300,  # 5 minutes
        register_limit: int = 3,
        register_window: int = 3600,  # 1 hour
        general_limit: int = 100,
        general_window: int = 3600,  # 1 hour
        enable_logging: bool = True,
    ):
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
            login_limit: Maximum login attempts per window
            login_window: Login rate limit window in seconds
            register_limit: Maximum registration attempts per window
            register_window: Registration rate limit window in seconds
            general_limit: General rate limit for other auth endpoints
            general_window: General rate limit window in seconds
            enable_logging: Whether to log rate limit events
        """
        super().__init__(app)
        self.rate_limiter = RateLimitHelper()

        # Rate limit configurations
        self.limits = {
            "/auth/login": {"max_requests": login_limit, "window": login_window},
            "/auth/register": {"max_requests": register_limit, "window": register_window},
            "/auth/refresh": {"max_requests": general_limit, "window": general_window},
            "/auth/logout": {"max_requests": general_limit, "window": general_window},
            "/auth/profile": {"max_requests": general_limit, "window": general_window},
        }

        self.enable_logging = enable_logging

        # Track rate limit violations for security monitoring
        self.violations: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        try:
            # Only apply rate limiting to authentication endpoints
            if not request.url.path.startswith("/auth/"):
                return await call_next(request)

            # Get client identifier (IP address with optional user info)
            client_id = self._get_client_identifier(request)

            # Get rate limit configuration for this endpoint
            endpoint_config = self.limits.get(request.url.path)

            if endpoint_config:
                # Check rate limit
                allowed, retry_after = self.rate_limiter.check_rate_limit(
                    identifier=f"{client_id}:{request.url.path}",
                    max_requests=endpoint_config["max_requests"],
                    window_seconds=endpoint_config["window"],
                )

                if not allowed:
                    # Log rate limit violation
                    self._log_rate_limit_violation(request, client_id, retry_after)

                    # Track violation for security monitoring
                    self._track_violation(client_id)

                    # Return rate limit error
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests to {request.url.path}",
                            "retry_after": retry_after,
                            "limit": endpoint_config["max_requests"],
                            "window": endpoint_config["window"],
                        },
                        headers={"Retry-After": str(retry_after)},
                    )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            if endpoint_config:
                self._add_rate_limit_headers(response, endpoint_config, client_id, request.url.path)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Don't block requests on middleware errors
            return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier for rate limiting."""
        # Try to get real IP from headers (for reverse proxy setups)
        real_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "").strip()
            or request.client.host
            if request.client
            else "unknown"
        )

        # Include user agent for additional uniqueness
        user_agent_hash = str(hash(request.headers.get("User-Agent", "")))[:8]

        return f"{real_ip}:{user_agent_hash}"

    def _log_rate_limit_violation(self, request: Request, client_id: str, retry_after: int) -> None:
        """Log rate limit violation for security monitoring."""
        if self.enable_logging:
            logger.warning(
                f"Rate limit exceeded for {request.url.path} from {client_id}. "
                f"Retry after {retry_after} seconds. "
                f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
            )

    def _track_violation(self, client_id: str) -> None:
        """Track rate limit violations for security analysis."""
        current_time = time.time()
        self.violations[client_id].append(current_time)

        # Clean up old violations (keep last 24 hours)
        cutoff_time = current_time - 86400  # 24 hours
        self.violations[client_id] = [t for t in self.violations[client_id] if t > cutoff_time]

        # Check for suspicious activity (many violations in short time)
        recent_violations = [
            t for t in self.violations[client_id] if t > current_time - 3600  # Last hour
        ]

        if len(recent_violations) >= 10:  # 10+ violations in an hour
            logger.critical(
                f"Suspicious activity detected from {client_id}: "
                f"{len(recent_violations)} rate limit violations in the last hour"
            )

    def _add_rate_limit_headers(
        self, response: Response, config: dict[str, int], client_id: str, path: str
    ) -> None:
        """Add rate limit information to response headers."""
        try:
            # Get current usage
            identifier = f"{client_id}:{path}"
            current_requests = len(
                [
                    t
                    for t in self.rate_limiter._requests.get(identifier, [])
                    if t > time.time() - config["window"]
                ]
            )

            # Add headers
            response.headers["X-RateLimit-Limit"] = str(config["max_requests"])
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, config["max_requests"] - current_requests)
            )
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + config["window"]))
            response.headers["X-RateLimit-Window"] = str(config["window"])

        except Exception as e:
            logger.debug(f"Failed to add rate limit headers: {e}")

    def get_violation_stats(self) -> dict[str, Any]:
        """Get rate limit violation statistics for monitoring."""
        current_time = time.time()
        stats = {
            "total_clients_with_violations": len(self.violations),
            "violations_last_hour": 0,
            "violations_last_24h": 0,
            "top_violators": [],
        }

        # Calculate statistics
        hour_ago = current_time - 3600
        day_ago = current_time - 86400

        client_violations = {}

        for client_id, violations in self.violations.items():
            recent_violations = [t for t in violations if t > day_ago]
            hour_violations = [t for t in violations if t > hour_ago]

            stats["violations_last_24h"] += len(recent_violations)
            stats["violations_last_hour"] += len(hour_violations)

            if recent_violations:
                client_violations[client_id] = len(recent_violations)

        # Get top violators
        stats["top_violators"] = sorted(
            client_violations.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return stats

    def reset_client_limits(self, client_id: str) -> bool:
        """Reset rate limits for a specific client (admin function)."""
        try:
            # Remove from rate limiter
            for path in self.limits.keys():
                identifier = f"{client_id}:{path}"
                self.rate_limiter.reset_identifier(identifier)

            # Remove from violations
            if client_id in self.violations:
                del self.violations[client_id]

            logger.info(f"Reset rate limits for client: {client_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset rate limits for {client_id}: {e}")
            return False


# Global middleware instance
_rate_limit_middleware: AuthRateLimitMiddleware | None = None


def get_rate_limit_middleware() -> AuthRateLimitMiddleware:
    """Get the global rate limiting middleware instance."""
    global _rate_limit_middleware
    if _rate_limit_middleware is None:
        # This will be initialized when added to the app
        raise RuntimeError("Rate limiting middleware not initialized")
    return _rate_limit_middleware


def setup_rate_limiting(app, **kwargs) -> AuthRateLimitMiddleware:
    """Set up rate limiting middleware for the application."""
    global _rate_limit_middleware
    _rate_limit_middleware = AuthRateLimitMiddleware(app, **kwargs)
    return _rate_limit_middleware
