"""
Unified authentication middleware for GraphRAG API Service.

This module provides a unified authentication system that supports both
JWT tokens and API keys with proper security logging and rate limiting.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery

from ..config import get_settings
from ..exceptions import AuthenticationError, AuthorizationError, QuotaExceededError
from ..security import get_security_logger
from .api_keys import APIKeyManager, APIKeyScope
from .jwt_auth import JWTConfig, JWTManager
from .master_key import get_master_key_validator


class AuthMethod(str, Enum):
    """Authentication methods."""

    JWT = "jwt"
    API_KEY = "api_key"  # pragma: allowlist secret
    NONE = "none"


class AuthenticatedUser:
    """Authenticated user information."""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list[str],
        permissions: list[str],
        auth_method: AuthMethod,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        api_key_id: str | None = None,
        is_master_admin: bool = False,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions
        self.auth_method = auth_method
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.api_key_id = api_key_id
        self.is_master_admin = is_master_admin

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def has_scope(self, scope: APIKeyScope) -> bool:
        """Check if user has specific API key scope."""
        return scope.value in self.permissions

    def is_master_administrator(self) -> bool:
        """Check if user is a master administrator."""
        return self.is_master_admin or APIKeyScope.MASTER_ADMIN.value in self.permissions

    def can_manage_all_keys(self) -> bool:
        """Check if user can manage all API keys."""
        return (
            self.is_master_admin
            or APIKeyScope.MANAGE_ALL_KEYS.value in self.permissions
            or APIKeyScope.MASTER_ADMIN.value in self.permissions
        )

    def can_perform_system_admin(self) -> bool:
        """Check if user can perform system administration."""
        return (
            self.is_master_admin
            or APIKeyScope.SYSTEM_ADMIN.value in self.permissions
            or APIKeyScope.MASTER_ADMIN.value in self.permissions
        )


class UnifiedAuthenticator:
    """Unified authentication system supporting JWT and API keys."""

    def __init__(self) -> None:
        self.security_logger = get_security_logger()
        self.jwt_manager: JWTManager | None = None
        self.api_key_manager: APIKeyManager | None = None
        self.master_key_validator = get_master_key_validator()

        # Security schemes
        self.bearer_security = HTTPBearer(auto_error=False)
        self.api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
        self.api_key_query = APIKeyQuery(name="api_key", auto_error=False)

    async def get_jwt_manager(self) -> JWTManager:
        """Get JWT manager instance."""
        if not self.jwt_manager:
            settings = get_settings()
            config = JWTConfig(
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
                refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
            )
            self.jwt_manager = JWTManager(config)
        return self.jwt_manager

    async def get_api_key_manager(self) -> APIKeyManager:
        """Get API key manager instance."""
        if not self.api_key_manager:
            self.api_key_manager = APIKeyManager()
        return self.api_key_manager

    async def authenticate_jwt(
        self, request: Request, credentials: HTTPAuthorizationCredentials
    ) -> AuthenticatedUser:
        """Authenticate using JWT token."""
        try:
            jwt_manager = await self.get_jwt_manager()

            # Check if token is blacklisted
            if jwt_manager.is_token_blacklisted(credentials.credentials):
                raise AuthenticationError("Token has been revoked")

            # Verify token
            payload = jwt_manager.verify_token(credentials.credentials)

            # Log successful authentication
            self.security_logger.authentication_attempt(
                success=True, user_id=payload.get("sub"), method="jwt", request=request
            )

            return AuthenticatedUser(
                user_id=payload["sub"],
                username=payload["username"],
                email=payload["email"],
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                auth_method=AuthMethod.JWT,
                tenant_id=payload.get("tenant_id"),
            )

        except Exception as e:
            self.security_logger.authentication_attempt(
                success=False, method="jwt", request=request, failure_reason=str(e)
            )
            raise AuthenticationError(f"JWT authentication failed: {str(e)}") from e

    async def authenticate_api_key(self, request: Request, api_key: str) -> AuthenticatedUser:
        """Authenticate using API key."""
        try:
            api_key_manager = await self.get_api_key_manager()

            # Validate API key
            key_data = await api_key_manager.validate_api_key(api_key)
            if not key_data:
                raise AuthenticationError("Invalid API key")

            # Check if key is active and not expired
            if not key_data.is_active:
                raise AuthenticationError("API key is inactive")

            if key_data.expires_at and key_data.expires_at < datetime.now(UTC):
                raise AuthenticationError("API key has expired")

            # Validate rate limits
            client_ip = getattr(request.client, "host", None)
            await api_key_manager.validate_rate_limit(key_data, client_ip)

            # Log successful authentication
            self.security_logger.api_key_usage(
                api_key_id=key_data.id,
                success=True,
                request=request,
                permissions_used=[scope.value for scope in key_data.scopes],
            )

            # Get user data (would typically come from database)
            user_data = await self._get_user_from_api_key(key_data)

            return AuthenticatedUser(
                user_id=key_data.user_id,
                username=user_data.get("username", f"api_user_{key_data.user_id}"),
                email=user_data.get("email", f"api_user_{key_data.user_id}@api.local"),
                roles=user_data.get("roles", ["api_user"]),
                permissions=[scope.value for scope in key_data.scopes],
                auth_method=AuthMethod.API_KEY,
                tenant_id=key_data.tenant_id,
                workspace_id=key_data.workspace_id,
                api_key_id=key_data.id,
            )

        except (AuthenticationError, QuotaExceededError):
            raise
        except Exception as e:
            self.security_logger.api_key_usage(api_key_id="unknown", success=False, request=request)
            raise AuthenticationError(f"API key authentication failed: {str(e)}") from e

    async def authenticate_master_key(self, request: Request, api_key: str) -> AuthenticatedUser:
        """Authenticate using master API key."""
        try:
            # Check if this is a master key format
            if not api_key.startswith("grak_master_"):
                raise AuthenticationError("Not a master key")

            # Validate master key
            if not self.master_key_validator.validate_master_key(api_key):
                raise AuthenticationError("Invalid master key")

            # Get master key permissions
            master_permissions = self.master_key_validator.get_master_permissions()

            # Log successful master key authentication
            self.security_logger.authentication_attempt(
                success=True, user_id="master_admin", method="master_key", request=request
            )

            return AuthenticatedUser(
                user_id="master_admin",
                username="Master Administrator",
                email="master@graphrag.local",
                roles=["master_admin", "system_admin"],
                permissions=master_permissions,
                auth_method=AuthMethod.API_KEY,
                is_master_admin=True,
            )

        except Exception as e:
            self.security_logger.authentication_attempt(
                success=False, method="master_key", request=request, failure_reason=str(e)
            )
            raise AuthenticationError(f"Master key authentication failed: {str(e)}") from e

    async def authenticate_request(
        self,
        request: Request,
        bearer_token: HTTPAuthorizationCredentials | None = None,
        api_key_header: str | None = None,
        api_key_query: str | None = None,
    ) -> AuthenticatedUser:
        """Authenticate request using available credentials.

        Tries master key first, then API key, then falls back to JWT.
        """
        # Try API key authentication first (includes master key check)
        api_key = api_key_header or api_key_query
        if api_key:
            # Check if this is a master key
            if api_key.startswith("grak_master_"):
                return await self.authenticate_master_key(request, api_key)
            else:
                return await self.authenticate_api_key(request, api_key)

        # Try JWT authentication
        if bearer_token:
            return await self.authenticate_jwt(request, bearer_token)

        # No authentication provided
        raise AuthenticationError("Authentication required")

    async def _get_user_from_api_key(self, key_data: Any) -> dict[str, Any]:
        """Get user data associated with API key."""
        # This would typically query the database
        # For now, return mock data
        return {
            "username": f"api_user_{key_data.user_id}",
            "email": f"api_user_{key_data.user_id}@api.local",
            "roles": ["api_user"],
            "full_name": f"API User {key_data.user_id}",
        }


# Global authenticator instance
_authenticator = UnifiedAuthenticator()


# FastAPI Dependencies


async def get_current_user(
    request: Request,
    bearer_token: HTTPAuthorizationCredentials | None = Depends(_authenticator.bearer_security),
    api_key_header: str | None = Depends(_authenticator.api_key_header),
    api_key_query: str | None = Depends(_authenticator.api_key_query),
) -> AuthenticatedUser:
    """Get current authenticated user from any supported auth method."""
    return await _authenticator.authenticate_request(
        request=request,
        bearer_token=bearer_token,
        api_key_header=api_key_header,
        api_key_query=api_key_query,
    )


async def get_current_user_optional(
    request: Request,
    bearer_token: HTTPAuthorizationCredentials | None = Depends(_authenticator.bearer_security),
    api_key_header: str | None = Depends(_authenticator.api_key_header),
    api_key_query: str | None = Depends(_authenticator.api_key_query),
) -> AuthenticatedUser | None:
    """Get current authenticated user, returning None if not authenticated."""
    try:
        return await _authenticator.authenticate_request(
            request=request,
            bearer_token=bearer_token,
            api_key_header=api_key_header,
            api_key_query=api_key_query,
        )
    except AuthenticationError:
        return None


def require_permission(permission: str) -> Any:
    """Require specific permission for endpoint access."""

    async def permission_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.has_permission(permission):
            raise AuthorizationError(
                f"Permission '{permission}' required",
                required_permission=permission,
                resource_id=current_user.workspace_id,
            )
        return current_user

    return permission_checker


def require_role(role: str) -> Any:
    """Require specific role for endpoint access."""

    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.has_role(role):
            raise AuthorizationError(f"Role '{role}' required", required_permission=f"role:{role}")
        return current_user

    return role_checker


def require_scope(scope: APIKeyScope) -> Any:
    """Require specific API key scope for endpoint access."""

    async def scope_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.has_scope(scope):
            raise AuthorizationError(
                f"Scope '{scope.value}' required", required_permission=scope.value
            )
        return current_user

    return scope_checker


def require_master_admin() -> Any:
    """Require master administrator privileges for endpoint access."""

    async def master_admin_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.is_master_administrator():
            raise AuthorizationError(
                "Master administrator privileges required", required_permission="master:admin"
            )
        return current_user

    return master_admin_checker


def require_key_management() -> Any:
    """Require API key management privileges for endpoint access."""

    async def key_management_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.can_manage_all_keys():
            raise AuthorizationError(
                "API key management privileges required",
                required_permission="master:manage_all_keys",
            )
        return current_user

    return key_management_checker


def require_system_admin() -> Any:
    """Require system administrator privileges for endpoint access."""

    async def system_admin_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user.can_perform_system_admin():
            raise AuthorizationError(
                "System administrator privileges required",
                required_permission="master:system_admin",
            )
        return current_user

    return system_admin_checker
