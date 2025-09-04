# src/graphrag_api_service/auth/api_keys.py
# API Key Management System for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""API key generation, validation, and management system."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

from ..exceptions import AuthenticationError, ValidationError, QuotaExceededError
from ..security import get_security_logger

logger = logging.getLogger(__name__)


class APIKeyScope(str, Enum):
    """API key permission scopes."""

    # Workspace permissions
    READ_WORKSPACES = "read:workspaces"
    WRITE_WORKSPACES = "write:workspaces"
    DELETE_WORKSPACES = "delete:workspaces"

    # Graph permissions
    READ_GRAPH = "read:graph"
    WRITE_GRAPH = "write:graph"

    # System permissions
    READ_SYSTEM = "read:system"
    ADMIN_SYSTEM = "admin:system"

    # User permissions
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"

    # API key management
    MANAGE_API_KEYS = "manage:api_keys"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration for API keys."""

    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    requests_per_hour: int = Field(default=1000, ge=1, le=100000)
    requests_per_day: int = Field(default=10000, ge=1, le=1000000)
    burst_limit: int = Field(default=10, ge=1, le=100)


class APIKey(BaseModel):
    """Enhanced API key model with granular permissions and rate limiting."""

    id: str
    name: str
    key_hash: str
    prefix: str
    user_id: str
    workspace_id: Optional[str] = None  # Workspace-specific keys
    tenant_id: Optional[str] = None
    scopes: List[APIKeyScope] = Field(default_factory=list)
    rate_limit_config: RateLimitConfig = Field(default_factory=RateLimitConfig)
    is_active: bool = True
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    # Usage tracking
    daily_usage: int = 0
    hourly_usage: int = 0
    minute_usage: int = 0
    last_reset_daily: Optional[datetime] = None
    last_reset_hourly: Optional[datetime] = None
    last_reset_minute: Optional[datetime] = None

    # Security tracking
    created_from_ip: Optional[str] = None
    last_used_ip: Optional[str] = None
    suspicious_activity_count: int = 0


class APIKeyRequest(BaseModel):
    """Enhanced API key creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[APIKeyScope] = Field(default_factory=list)
    workspace_id: Optional[str] = None
    rate_limit_config: Optional[RateLimitConfig] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650)  # Max 10 years
    description: Optional[str] = Field(None, max_length=500)


class APIKeyResponse(BaseModel):
    """API key creation response."""

    id: str
    name: str
    key: str  # Only returned once during creation
    prefix: str
    permissions: list[str]
    rate_limit: int
    expires_at: datetime | None = None


class APIKeyManager:
    """Manages API key lifecycle and validation."""

    def __init__(self, rbac_system=None):
        """Initialize API key manager.

        Args:
            rbac_system: Optional RBAC system for permission checking
        """
        self.api_keys: dict[str, APIKey] = {}
        self.key_hash_to_id: dict[str, str] = {}
        self.usage_tracking: dict[str, list[datetime]] = {}
        self.rbac = rbac_system

    def generate_api_key(self) -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            Tuple of (full_key, prefix, hash)
        """
        # Generate random key
        key = secrets.token_urlsafe(32)

        # Create prefix for identification
        prefix = f"grag_{key[:8]}"

        # Hash the key for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        return key, prefix, key_hash

    async def create_api_key(
        self,
        user_id: str,
        request: APIKeyRequest,
        tenant_id: Optional[str] = None,
        created_from_ip: Optional[str] = None
    ) -> APIKeyResponse:
        """Create a new API key with enhanced security and scoping.

        Args:
            user_id: User ID creating the key
            request: API key creation request
            tenant_id: Optional tenant ID
            created_from_ip: IP address where key was created

        Returns:
            API key response with the actual key

        Raises:
            ValidationError: If request is invalid
            QuotaExceededError: If user has too many keys
        """
        # Validate scopes
        if not request.scopes:
            raise ValidationError("At least one scope must be specified", field="scopes")

        # Check user's key quota (max 10 keys per user)
        user_keys = [k for k in self.api_keys.values() if k.user_id == user_id and k.is_active]
        if len(user_keys) >= 10:
            raise QuotaExceededError(
                "Maximum number of API keys reached",
                quota_type="api_keys",
                current_usage=len(user_keys),
                quota_limit=10
            )

        key, prefix, key_hash = self.generate_api_key()
        key_id = f"key_{secrets.token_hex(8)}"

        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

        # Use provided rate limit config or default
        rate_limit_config = request.rate_limit_config or RateLimitConfig()

        api_key = APIKey(
            id=key_id,
            name=request.name,
            key_hash=key_hash,
            prefix=prefix,
            user_id=user_id,
            workspace_id=request.workspace_id,
            tenant_id=tenant_id,
            scopes=request.scopes,
            rate_limit_config=rate_limit_config,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
            created_from_ip=created_from_ip,
            last_reset_daily=datetime.now(UTC),
            last_reset_hourly=datetime.now(UTC),
            last_reset_minute=datetime.now(UTC)
        )

        # Store the key
        self.api_keys[key_id] = api_key
        self.key_hash_to_id[key_hash] = key_id

        # Log key creation
        security_logger = get_security_logger()
        security_logger.api_key_usage(
            api_key_id=key_id,
            success=True,
            permissions_used=["create_api_key"]
        )

        return APIKeyResponse(
            id=key_id,
            name=request.name,
            key=key,  # Only returned once
            prefix=prefix,
            scopes=[scope.value for scope in request.scopes],
            rate_limit_config=rate_limit_config,
            expires_at=expires_at,
            created_at=api_key.created_at
        )

    async def validate_rate_limit(self, api_key: APIKey, request_ip: Optional[str] = None) -> bool:
        """Validate rate limits for API key.

        Args:
            api_key: API key to check
            request_ip: IP address of the request

        Returns:
            True if within rate limits

        Raises:
            QuotaExceededError: If rate limit exceeded
        """
        now = datetime.now(UTC)

        # Reset counters if needed
        if api_key.last_reset_minute and (now - api_key.last_reset_minute).seconds >= 60:
            api_key.minute_usage = 0
            api_key.last_reset_minute = now

        if api_key.last_reset_hourly and (now - api_key.last_reset_hourly).seconds >= 3600:
            api_key.hourly_usage = 0
            api_key.last_reset_hourly = now

        if api_key.last_reset_daily and (now - api_key.last_reset_daily).days >= 1:
            api_key.daily_usage = 0
            api_key.last_reset_daily = now

        # Check limits
        config = api_key.rate_limit_config

        if api_key.minute_usage >= config.requests_per_minute:
            raise QuotaExceededError(
                "Rate limit exceeded: requests per minute",
                quota_type="requests_per_minute",
                current_usage=api_key.minute_usage,
                quota_limit=config.requests_per_minute
            )

        if api_key.hourly_usage >= config.requests_per_hour:
            raise QuotaExceededError(
                "Rate limit exceeded: requests per hour",
                quota_type="requests_per_hour",
                current_usage=api_key.hourly_usage,
                quota_limit=config.requests_per_hour
            )

        if api_key.daily_usage >= config.requests_per_day:
            raise QuotaExceededError(
                "Rate limit exceeded: requests per day",
                quota_type="requests_per_day",
                current_usage=api_key.daily_usage,
                quota_limit=config.requests_per_day
            )

        # Update usage counters
        api_key.minute_usage += 1
        api_key.hourly_usage += 1
        api_key.daily_usage += 1
        api_key.usage_count += 1
        api_key.last_used_at = now
        api_key.last_used_ip = request_ip

        return True

    async def validate_api_key(self, key: str) -> APIKey | None:
        """Validate an API key.

        Args:
            key: API key to validate

        Returns:
            API key object if valid, None otherwise
        """
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = self.key_hash_to_id.get(key_hash)

        if not key_id:
            return None

        api_key = self.api_keys.get(key_id)
        if not api_key:
            return None

        # Check if key is active
        if not api_key.is_active:
            return None

        # Check if key has expired
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            logger.warning("API key %s has expired", api_key.name)
            return None

        # Check rate limit
        if not await self._check_rate_limit(key_id, api_key.rate_limit):
            logger.warning("Rate limit exceeded for API key: %s", api_key.name)
            return None

        # Update usage statistics
        api_key.last_used_at = datetime.now(UTC)
        api_key.usage_count += 1

        return api_key

    async def _check_rate_limit(self, key_id: str, rate_limit: int) -> bool:
        """Check if API key is within rate limit.

        Args:
            key_id: API key ID
            rate_limit: Rate limit (requests per hour)

        Returns:
            True if within rate limit
        """
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)

        # Get usage in the last hour
        usage_times = self.usage_tracking.get(key_id, [])
        recent_usage = [t for t in usage_times if t > hour_ago]

        # Update usage tracking
        recent_usage.append(now)
        self.usage_tracking[key_id] = recent_usage

        return len(recent_usage) <= rate_limit

    async def revoke_api_key(
        self, key_id: str, user_id: str, user_permissions: list[str] | None = None
    ) -> bool:
        """Revoke an API key.

        Args:
            key_id: API key ID to revoke
            user_id: User ID requesting revocation
            user_permissions: User's permissions for admin check

        Returns:
            True if successfully revoked
        """
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False

        # Check if user owns the key or is admin
        if api_key.user_id != user_id and not self._is_admin_user(user_permissions):
            logger.warning(
                "User %s attempted to revoke API key %s without permission",
                user_id,
                key_id,
            )
            return False

        api_key.is_active = False
        logger.info("Revoked API key: %s by user: %s", api_key.name, user_id)

        return True

    def _is_admin_user(self, user_permissions: list[str] | None = None) -> bool:
        """Check if user has admin permissions.

        Args:
            user_permissions: User's permissions list

        Returns:
            True if user has admin permissions
        """
        if not user_permissions:
            return False

        # Check if user has admin permissions
        if self.rbac:
            return bool(self.rbac.has_permission(user_permissions, "manage:users"))

        # Fallback: check for admin-like permissions
        admin_permissions = ["manage:users", "manage:all", "delete:all"]
        return any(perm in user_permissions for perm in admin_permissions)

    async def list_user_keys(self, user_id: str) -> list[APIKey]:
        """List API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's API keys
        """
        return [key for key in self.api_keys.values() if key.user_id == user_id]

    async def get_key_usage_stats(self, key_id: str) -> dict[str, Any]:
        """Get usage statistics for an API key.

        Args:
            key_id: API key ID

        Returns:
            Usage statistics
        """
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return {}

        now = datetime.utcnow()
        usage_times = self.usage_tracking.get(key_id, [])

        # Calculate usage in different time periods
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(weeks=1)

        usage_last_hour = len([t for t in usage_times if t > hour_ago])
        usage_last_day = len([t for t in usage_times if t > day_ago])
        usage_last_week = len([t for t in usage_times if t > week_ago])

        return {
            "key_id": key_id,
            "key_name": api_key.name,
            "total_usage": api_key.usage_count,
            "usage_last_hour": usage_last_hour,
            "usage_last_day": usage_last_day,
            "usage_last_week": usage_last_week,
            "last_used_at": api_key.last_used_at,
            "rate_limit": api_key.rate_limit,
            "is_active": api_key.is_active,
            "expires_at": api_key.expires_at,
        }


class APIKeyPermissions:
    """API key permission definitions."""

    # Read permissions
    READ_ENTITIES = "read:entities"
    READ_RELATIONSHIPS = "read:relationships"
    READ_COMMUNITIES = "read:communities"
    READ_WORKSPACES = "read:workspaces"
    READ_SYSTEM = "read:system"

    # Write permissions
    WRITE_ENTITIES = "write:entities"
    WRITE_RELATIONSHIPS = "write:relationships"
    WRITE_COMMUNITIES = "write:communities"
    WRITE_WORKSPACES = "write:workspaces"

    # Admin permissions
    MANAGE_USERS = "manage:users"
    MANAGE_API_KEYS = "manage:api_keys"
    MANAGE_SYSTEM = "manage:system"

    # GraphQL permissions
    GRAPHQL_QUERY = "graphql:query"
    GRAPHQL_MUTATION = "graphql:mutation"
    GRAPHQL_SUBSCRIPTION = "graphql:subscription"

    @classmethod
    def get_all_permissions(cls) -> list[str]:
        """Get all available permissions.

        Returns:
            List of all permissions
        """
        return [
            cls.READ_ENTITIES,
            cls.READ_RELATIONSHIPS,
            cls.READ_COMMUNITIES,
            cls.READ_WORKSPACES,
            cls.READ_SYSTEM,
            cls.WRITE_ENTITIES,
            cls.WRITE_RELATIONSHIPS,
            cls.WRITE_COMMUNITIES,
            cls.WRITE_WORKSPACES,
            cls.MANAGE_USERS,
            cls.MANAGE_API_KEYS,
            cls.MANAGE_SYSTEM,
            cls.GRAPHQL_QUERY,
            cls.GRAPHQL_MUTATION,
            cls.GRAPHQL_SUBSCRIPTION,
        ]

    @classmethod
    def get_read_permissions(cls) -> list[str]:
        """Get read-only permissions.

        Returns:
            List of read permissions
        """
        return [
            cls.READ_ENTITIES,
            cls.READ_RELATIONSHIPS,
            cls.READ_COMMUNITIES,
            cls.READ_WORKSPACES,
            cls.READ_SYSTEM,
            cls.GRAPHQL_QUERY,
        ]

    @classmethod
    def get_write_permissions(cls) -> list[str]:
        """Get write permissions.

        Returns:
            List of write permissions
        """
        return [
            cls.WRITE_ENTITIES,
            cls.WRITE_RELATIONSHIPS,
            cls.WRITE_COMMUNITIES,
            cls.WRITE_WORKSPACES,
            cls.GRAPHQL_MUTATION,
        ]

    @classmethod
    def get_admin_permissions(cls) -> list[str]:
        """Get admin permissions.

        Returns:
            List of admin permissions
        """
        return [
            cls.MANAGE_USERS,
            cls.MANAGE_API_KEYS,
            cls.MANAGE_SYSTEM,
        ]


# Global API key manager
_api_key_manager: APIKeyManager | None = None


def get_api_key_manager(rbac_system=None) -> APIKeyManager:
    """Get the global API key manager.

    Args:
        rbac_system: Optional RBAC system for permission checking

    Returns:
        APIKeyManager instance
    """
    global _api_key_manager

    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(rbac_system)

    return _api_key_manager
