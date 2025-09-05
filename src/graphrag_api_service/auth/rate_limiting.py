"""
Rate limiting system for GraphRAG API Service.

This module provides comprehensive rate limiting with different strategies
for different authentication methods and endpoints.
"""

import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from ..exceptions import RateLimitError
from ..security import get_security_logger


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"  # nosec B105 - Rate limiting algorithm name, not a password


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW


class RateLimitInfo(BaseModel):
    """Rate limit information."""

    limit: int
    remaining: int
    reset_time: datetime
    retry_after: int | None = None


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""

    def __init__(self) -> None:
        self.security_logger = get_security_logger()

        # Storage for different rate limiting strategies
        self._fixed_windows: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._sliding_windows: dict[str, deque[float]] = defaultdict(lambda: deque())
        self._token_buckets: dict[str, dict[str, Any]] = defaultdict(dict)
        self._last_reset: dict[str, datetime] = {}

    async def check_rate_limit(
        self, identifier: str, config: RateLimitConfig, request: Request | None = None
    ) -> RateLimitInfo:
        """Check if request is within rate limits.

        Args:
            identifier: Unique identifier for rate limiting (user_id, api_key_id, ip)
            config: Rate limit configuration
            request: Optional request object for logging

        Returns:
            Rate limit information

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(identifier, config, request)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(identifier, config, request)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(identifier, config, request)
        else:
            raise ValueError(f"Unknown rate limit strategy: {config.strategy}")

    async def _check_fixed_window(
        self, identifier: str, config: RateLimitConfig, request: Request | None
    ) -> RateLimitInfo:
        """Fixed window rate limiting."""
        now = datetime.now(UTC)
        window_key = f"{identifier}:minute:{now.strftime('%Y-%m-%d-%H-%M')}"

        # Get current count
        current_count = self._fixed_windows[identifier].get(window_key, 0)

        # Calculate next window reset time
        next_window = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)

        # Check limit
        if current_count >= config.requests_per_minute:
            # Calculate retry after
            retry_after = int((next_window - now).total_seconds())

            # Log rate limit exceeded
            if request:
                self.security_logger.rate_limit_exceeded(
                    limit_type="requests_per_minute",
                    request=request,
                    current_rate=current_count,
                    limit=config.requests_per_minute,
                )

            raise RateLimitError(
                message=(
                    f"Rate limit exceeded: {current_count}/{config.requests_per_minute} "
                    "requests per minute"
                ),
                retry_after=retry_after,
                limit_type="requests_per_minute",
            )

        # Increment counter
        self._fixed_windows[identifier][window_key] = current_count + 1

        # Clean old windows
        await self._cleanup_fixed_windows(identifier)

        return RateLimitInfo(
            limit=config.requests_per_minute,
            remaining=config.requests_per_minute - current_count - 1,
            reset_time=next_window,
        )

    async def _check_sliding_window(
        self, identifier: str, config: RateLimitConfig, request: Request | None
    ) -> RateLimitInfo:
        """Sliding window rate limiting."""
        now = time.time()
        window = self._sliding_windows[identifier]

        # Remove old entries (older than 1 minute)
        cutoff = now - 60
        while window and window[0] < cutoff:
            window.popleft()

        # Check limit
        if len(window) >= config.requests_per_minute:
            # Calculate retry after
            oldest_request = window[0]
            retry_after = int(oldest_request + 60 - now)

            # Log rate limit exceeded
            if request:
                self.security_logger.rate_limit_exceeded(
                    limit_type="requests_per_minute_sliding",
                    request=request,
                    current_rate=len(window),
                    limit=config.requests_per_minute,
                )

            raise RateLimitError(
                message=(
                    f"Rate limit exceeded: {len(window)}/{config.requests_per_minute} "
                    "requests per minute"
                ),
                retry_after=retry_after,
                limit_type="requests_per_minute_sliding",
            )

        # Add current request
        window.append(now)

        # Calculate reset time
        reset_time = datetime.fromtimestamp(now + 60)

        return RateLimitInfo(
            limit=config.requests_per_minute,
            remaining=config.requests_per_minute - len(window),
            reset_time=reset_time,
        )

    async def _check_token_bucket(
        self, identifier: str, config: RateLimitConfig, request: Request | None
    ) -> RateLimitInfo:
        """Token bucket rate limiting."""
        now = time.time()

        # Initialize bucket if not exists
        if identifier not in self._token_buckets:
            self._token_buckets[identifier] = {
                "tokens": config.burst_limit,
                "last_refill": now,
                "capacity": config.burst_limit,
                "refill_rate": config.requests_per_minute / 60.0,  # tokens per second
            }

        bucket = self._token_buckets[identifier]

        # Refill tokens based on time passed
        time_passed = now - bucket["last_refill"]
        tokens_to_add = time_passed * bucket["refill_rate"]
        bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

        # Check if we have tokens
        if bucket["tokens"] < 1:
            # Calculate retry after
            retry_after = int((1 - bucket["tokens"]) / bucket["refill_rate"])

            # Log rate limit exceeded
            if request:
                self.security_logger.rate_limit_exceeded(
                    limit_type="token_bucket",
                    request=request,
                    current_rate=0,
                    limit=config.burst_limit,
                )

            raise RateLimitError(
                message="Rate limit exceeded: no tokens available",
                retry_after=retry_after,
                limit_type="token_bucket",
            )

        # Consume token
        bucket["tokens"] -= 1

        # Calculate reset time (when bucket will be full)
        tokens_needed = bucket["capacity"] - bucket["tokens"]
        seconds_to_full = tokens_needed / bucket["refill_rate"]
        reset_time = datetime.fromtimestamp(now + seconds_to_full)

        return RateLimitInfo(
            limit=bucket["capacity"], remaining=int(bucket["tokens"]), reset_time=reset_time
        )

    async def _cleanup_fixed_windows(self, identifier: str) -> None:
        """Clean up old fixed window entries."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=1)  # Keep last hour

        windows_to_remove = []
        for window_key in self._fixed_windows[identifier]:
            # Extract timestamp from window key
            try:
                window_time = datetime.strptime(window_key.split(":", 2)[2], "%Y-%m-%d-%H-%M")
                if window_time < cutoff:
                    windows_to_remove.append(window_key)
            except (ValueError, IndexError):
                # Invalid window key, remove it
                windows_to_remove.append(window_key)

        for window_key in windows_to_remove:
            del self._fixed_windows[identifier][window_key]

    async def get_rate_limit_headers(
        self, identifier: str, config: RateLimitConfig
    ) -> dict[str, str]:
        """Get rate limit headers for response."""
        try:
            info = await self.check_rate_limit(identifier, config)
            return {
                "X-RateLimit-Limit": str(info.limit),
                "X-RateLimit-Remaining": str(info.remaining),
                "X-RateLimit-Reset": str(int(info.reset_time.timestamp())),
            }
        except RateLimitError as e:
            return {
                "X-RateLimit-Limit": str(config.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + (e.retry_after or 60))),
                "Retry-After": str(e.retry_after or 60),
            }


class EndpointRateLimiter:
    """Endpoint-specific rate limiting."""

    def __init__(self) -> None:
        self.rate_limiter = RateLimiter()

        # Default configurations for different endpoint types
        self.endpoint_configs = {
            "auth": RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                burst_limit=5,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
            ),
            "api": RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                burst_limit=10,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
            ),
            "upload": RateLimitConfig(
                requests_per_minute=5,
                requests_per_hour=50,
                burst_limit=2,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
            ),
            "query": RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_limit=5,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
            ),
        }

    async def check_endpoint_rate_limit(
        self,
        endpoint_type: str,
        identifier: str,
        request: Request | None = None,
        custom_config: RateLimitConfig | None = None,
    ) -> RateLimitInfo:
        """Check rate limit for specific endpoint type."""
        config = custom_config or self.endpoint_configs.get(
            endpoint_type, self.endpoint_configs["api"]
        )

        return await self.rate_limiter.check_rate_limit(
            f"{endpoint_type}:{identifier}", config, request
        )

    def get_endpoint_config(self, endpoint_type: str) -> RateLimitConfig:
        """Get rate limit configuration for endpoint type."""
        return self.endpoint_configs.get(endpoint_type, self.endpoint_configs["api"])


# Global rate limiter instances
_rate_limiter = RateLimiter()
_endpoint_rate_limiter = EndpointRateLimiter()


# Utility functions
async def check_rate_limit(
    identifier: str, config: RateLimitConfig, request: Request | None = None
) -> RateLimitInfo:
    """Check rate limit using global rate limiter."""
    return await _rate_limiter.check_rate_limit(identifier, config, request)


async def check_endpoint_rate_limit(
    endpoint_type: str,
    identifier: str,
    request: Request | None = None,
    custom_config: RateLimitConfig | None = None,
) -> RateLimitInfo:
    """Check endpoint-specific rate limit."""
    return await _endpoint_rate_limiter.check_endpoint_rate_limit(
        endpoint_type, identifier, request, custom_config
    )


async def get_rate_limit_headers(identifier: str, config: RateLimitConfig) -> dict[str, str]:
    """Get rate limit headers for response."""
    return await _rate_limiter.get_rate_limit_headers(identifier, config)
