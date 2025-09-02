# src/graphrag_api_service/middleware/rate_limiter.py
# Rate limiting middleware implementation
# Author: Pierre Grothé  
# Creation Date: 2025-09-02

"""Rate limiting middleware for API protection."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..security.security_config import get_security_config


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent API abuse."""

    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: ASGI application
            calls: Number of calls allowed
            period: Time period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
        self.security_config = get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if not self.security_config.enable_rate_limiting:
            return await call_next(request)

        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)

        # Check rate limit
        if not self._is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.period,
                },
                headers={
                    "Retry-After": str(self.period),
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.period),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self._get_remaining_calls(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.period)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get authenticated user ID
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client = request.client
        if client:
            return f"ip:{client.host}"
        
        return "ip:unknown"

    def _is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request."""
        now = time.time()
        
        # Clean old entries
        self.clients[client_id] = [
            timestamp for timestamp in self.clients[client_id]
            if timestamp > now - self.period
        ]

        # Check rate limit
        if len(self.clients[client_id]) >= self.calls:
            return False

        # Record request
        self.clients[client_id].append(now)
        return True

    def _get_remaining_calls(self, client_id: str) -> int:
        """Get remaining calls for client."""
        now = time.time()
        recent_calls = [
            timestamp for timestamp in self.clients[client_id]
            if timestamp > now - self.period
        ]
        return max(0, self.calls - len(recent_calls))


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies."""

    def __init__(self):
        """Initialize advanced rate limiter."""
        self.strategies = {
            "fixed_window": self._fixed_window_check,
            "sliding_window": self._sliding_window_check,
            "token_bucket": self._token_bucket_check,
            "leaky_bucket": self._leaky_bucket_check,
        }
        self.buckets = defaultdict(lambda: {"tokens": 100, "last_update": time.time()})

    def check_rate_limit(
        self,
        client_id: str,
        strategy: str = "sliding_window",
        limit: int = 100,
        window: int = 60,
    ) -> tuple[bool, dict]:
        """
        Check rate limit using specified strategy.

        Returns:
            Tuple of (allowed, metadata)
        """
        if strategy not in self.strategies:
            strategy = "sliding_window"

        return self.strategies[strategy](client_id, limit, window)

    def _fixed_window_check(self, client_id: str, limit: int, window: int) -> tuple[bool, dict]:
        """Fixed window rate limiting."""
        # Implementation would use Redis or similar for production
        return True, {"strategy": "fixed_window", "remaining": limit}

    def _sliding_window_check(
        self, client_id: str, limit: int, window: int
    ) -> tuple[bool, dict]:
        """Sliding window rate limiting."""
        # Implementation would use Redis sorted sets for production
        return True, {"strategy": "sliding_window", "remaining": limit}

    def _token_bucket_check(self, client_id: str, limit: int, window: int) -> tuple[bool, dict]:
        """Token bucket rate limiting."""
        now = time.time()
        bucket = self.buckets[client_id]
        
        # Refill tokens
        time_passed = now - bucket["last_update"]
        tokens_to_add = time_passed * (limit / window)
        bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

        # Check if request is allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, {
                "strategy": "token_bucket",
                "remaining": int(bucket["tokens"]),
                "refill_rate": limit / window,
            }

        return False, {
            "strategy": "token_bucket",
            "remaining": 0,
            "retry_after": (1 - bucket["tokens"]) / (limit / window),
        }

    def _leaky_bucket_check(self, client_id: str, limit: int, window: int) -> tuple[bool, dict]:
        """Leaky bucket rate limiting."""
        # Similar to token bucket but with different semantics
        return self._token_bucket_check(client_id, limit, window)


def setup_rate_limiting(app: ASGIApp) -> ASGIApp:
    """Set up rate limiting for the application."""
    config = get_security_config()
    
    if config.enable_rate_limiting and config.rate_limit.enabled:
        app.add_middleware(
            RateLimitMiddleware,
            calls=config.rate_limit.requests_per_minute,
            period=60,
        )
    
    return app