# src/graphrag_api_service/auth/api_keys.py
# API Key Management System for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""API key generation, validation, and management system."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class APIKey(BaseModel):
    """API key model."""

    id: str
    name: str
    key_hash: str
    prefix: str
    user_id: str
    tenant_id: str | None = None
    permissions: list[str]
    rate_limit: int = 1000  # requests per hour
    is_active: bool = True
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    usage_count: int = 0


class APIKeyRequest(BaseModel):
    """API key creation request."""

    name: str
    permissions: list[str]
    rate_limit: int = 1000
    expires_in_days: int | None = None


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
        self, user_id: str, request: APIKeyRequest, tenant_id: str | None = None
    ) -> APIKeyResponse:
        """Create a new API key.

        Args:
            user_id: User ID creating the key
            request: API key creation request
            tenant_id: Optional tenant ID

        Returns:
            API key response with the actual key
        """
        key, prefix, key_hash = self.generate_api_key()
        key_id = f"key_{len(self.api_keys) + 1}"

        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

        api_key = APIKey(
            id=key_id,
            name=request.name,
            key_hash=key_hash,
            prefix=prefix,
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        self.api_keys[key_id] = api_key
        self.key_hash_to_id[key_hash] = key_id
        self.usage_tracking[key_id] = []

        logger.info(f"Created API key: {request.name} for user: {user_id}")

        return APIKeyResponse(
            id=key_id,
            name=request.name,
            key=key,  # Only returned once
            prefix=prefix,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            expires_at=expires_at,
        )

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
            logger.warning(f"API key {api_key.name} has expired")
            return None

        # Check rate limit
        if not await self._check_rate_limit(key_id, api_key.rate_limit):
            logger.warning(f"Rate limit exceeded for API key: {api_key.name}")
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
        self, key_id: str, user_id: str, user_permissions: Optional[list[str]] = None
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
                f"User {user_id} attempted to revoke API key {key_id} without permission"
            )
            return False

        api_key.is_active = False
        logger.info(f"Revoked API key: {api_key.name} by user: {user_id}")

        return True

    def _is_admin_user(self, user_permissions: Optional[list[str]] = None) -> bool:
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
