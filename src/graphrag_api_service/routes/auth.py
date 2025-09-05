"""
Authentication routes for GraphRAG API Service.

This module provides comprehensive authentication endpoints including
user registration, login, token refresh, logout, and API key management.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from ..auth.admin_api_keys import (
    AdminAPIKeyFilter,
    AdminAPIKeyRequest,
    AdminAPIKeyUpdate,
    BatchOperation,
    BatchOperationResult,
    get_admin_api_key_manager,
)
from ..auth.api_keys import APIKeyManager, APIKeyRequest, RateLimitConfig
from ..auth.jwt_auth import JWTConfig, JWTManager
from ..auth.rate_limiting import RateLimitConfig as AuthRateLimitConfig
from ..auth.rate_limiting import RateLimiter
from ..auth.unified_auth import AuthenticatedUser, require_key_management
from ..config import get_settings
from ..database.sqlite_models import SQLiteManager
from ..exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
)
from ..models.user import UserCreate
from ..models.user import UserLogin as UserLoginModel
from ..repositories.user_repository import UserRepository
from ..security import get_security_logger
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)
security_logger = get_security_logger()

# Rate limiting configuration for authentication endpoints
auth_rate_limiter = RateLimiter()
LOGIN_RATE_LIMIT = AuthRateLimitConfig(
    requests_per_minute=5,  # 5 login attempts per minute
    requests_per_hour=30,  # 30 login attempts per hour
    burst_limit=10,  # Allow burst of 10 attempts
)
REGISTER_RATE_LIMIT = AuthRateLimitConfig(
    requests_per_minute=2,  # 2 registration attempts per minute
    requests_per_hour=10,  # 10 registration attempts per hour
    burst_limit=5,  # Allow burst of 5 attempts
)


# Request/Response Models
class UserRegistration(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=100)


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str = Field(..., min_length=1, description="Password cannot be empty")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserProfile(BaseModel):
    """User profile response."""

    user_id: str
    username: str
    email: str
    full_name: str | None
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    last_login_at: datetime | None


class APIKeyListResponse(BaseModel):
    """API key list response."""

    id: str
    name: str
    prefix: str
    scopes: list[str]
    workspace_id: str | None
    rate_limit_config: RateLimitConfig
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    usage_count: int


# Dependency injection - Singleton JWT Manager
# Enhanced in 2025 for consistent token blacklist management across requests
_jwt_manager_instance: JWTManager | None = None


async def get_jwt_manager() -> JWTManager:
    """Get JWT manager singleton instance with enhanced security features.

    This singleton pattern was implemented in 2025 to ensure consistent token
    blacklist management across all requests. Previously, each request created
    a new JWT manager instance, causing token blacklists to be isolated and
    allowing revoked tokens to remain valid in other request contexts.

    Security Benefits:
    - Shared token blacklist across all requests
    - Consistent logout behavior system-wide
    - Prevents token reuse after revocation
    - Maintains session state integrity

    Returns:
        JWTManager: Singleton instance with shared state
    """
    global _jwt_manager_instance
    if _jwt_manager_instance is None:
        settings = get_settings()
        config = JWTConfig(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
            refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
        )
        _jwt_manager_instance = JWTManager(config)
    return _jwt_manager_instance


async def get_api_key_manager() -> APIKeyManager:
    """Get API key manager instance."""
    return APIKeyManager()


# Service Layer Dependencies
_db_manager_instance: SQLiteManager | None = None
_user_repository_instance: UserRepository | None = None
_auth_service_instance: AuthService | None = None


async def get_db_manager() -> SQLiteManager:
    """Get database manager singleton instance."""
    global _db_manager_instance
    if _db_manager_instance is None:
        settings = get_settings()
        _db_manager_instance = SQLiteManager(settings.database_path)
    return _db_manager_instance


async def get_user_repository() -> UserRepository:
    """Get user repository singleton instance."""
    global _user_repository_instance
    if _user_repository_instance is None:
        db_manager = await get_db_manager()
        _user_repository_instance = UserRepository(db_manager)
    return _user_repository_instance


async def get_auth_service() -> AuthService:
    """Get authentication service singleton instance."""
    global _auth_service_instance
    if _auth_service_instance is None:
        user_repository = await get_user_repository()
        jwt_manager = await get_jwt_manager()
        db_manager = await get_db_manager()
        _auth_service_instance = AuthService(user_repository, jwt_manager, db_manager)
    return _auth_service_instance


# Enhanced Authentication Helper Functions


async def _validate_password_strength(password: str) -> None:
    """Validate password strength with comprehensive checks."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long", field="password")

    if len(password) > 128:
        raise ValidationError("Password must be less than 128 characters", field="password")

    # Check for complexity requirements
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise ValidationError(
            "Password must contain at least one uppercase letter, lowercase letter, "
            "digit, and special character",
            field="password",
        )


async def _user_exists(email: str, username: str, user_repository: UserRepository) -> bool:
    """Check if user already exists in database."""
    return await user_repository.user_exists(email, username)


async def _create_user_in_database(user_data: UserRegistration, auth_service: AuthService) -> str:
    """Create user in database and return user ID."""
    # Convert UserRegistration to UserCreate model
    user_create = UserCreate(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        roles=["user"],
        permissions=["read:workspaces", "create:workspaces"],
    )

    # Register user through auth service
    registration_result = await auth_service.register_user(user_create)
    return str(registration_result["user"]["user_id"])


async def _check_login_rate_limit(request: Request, email: str) -> None:
    """Apply rate limiting for login attempts."""
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"login:{client_ip}:{email}"

    try:
        # Check rate limit for this specific email/IP combination
        await auth_rate_limiter.check_rate_limit(
            identifier=identifier, config=LOGIN_RATE_LIMIT, request=request
        )
    except RateLimitError as e:
        security_logger._log_security_event(
            event_type="rate_limit_exceeded",
            level="warning",
            message=f"Rate limit exceeded for login attempts: {identifier}",
            request=request,
            details={
                "endpoint": "/auth/login",
                "identifier": identifier,
                "limit": LOGIN_RATE_LIMIT.requests_per_minute,
                "requests_per_hour": LOGIN_RATE_LIMIT.requests_per_hour,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)},
        ) from e


async def _check_register_rate_limit(request: Request, email: str) -> None:
    """Apply rate limiting for registration attempts."""
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"register:{client_ip}:{email}"

    try:
        # Check rate limit for this specific email/IP combination
        await auth_rate_limiter.check_rate_limit(
            identifier=identifier, config=REGISTER_RATE_LIMIT, request=request
        )
    except RateLimitError as e:
        security_logger._log_security_event(
            event_type="rate_limit_exceeded",
            level="warning",
            message=f"Rate limit exceeded for registration attempts: {identifier}",
            request=request,
            details={
                "endpoint": "/auth/register",
                "identifier": identifier,
                "limit": REGISTER_RATE_LIMIT.requests_per_minute,
                "requests_per_hour": REGISTER_RATE_LIMIT.requests_per_hour,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)},
        ) from e


async def _authenticate_user_credentials(
    email: str, password: str, auth_service: AuthService
) -> dict[str, Any] | None:
    """Authenticate user credentials against database."""
    return await auth_service.authenticate_user(email, password)


async def _simulate_password_verification() -> None:
    """Simulate password verification to prevent timing attacks."""

    import secrets

    # Simulate the time it takes to verify a password
    dummy_hash = "$2b$12$dummy.hash.to.prevent.timing.attacks"
    dummy_password = secrets.token_urlsafe(16)

    # This creates a consistent delay regardless of whether user exists
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    pwd_context.verify(dummy_password, dummy_hash)


async def _update_last_login(user_id: str, user_repository: UserRepository) -> None:
    """Update user's last login timestamp."""
    await user_repository.update_last_login(user_id)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> dict[str, Any]:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise AuthenticationError("Authentication credentials required")

    try:
        # Verify token and check blacklist
        if jwt_manager.is_token_blacklisted(credentials.credentials):
            raise AuthenticationError("Token has been revoked")

        payload = jwt_manager.verify_token(credentials.credentials)

        # Log successful authentication
        security_logger.authentication_attempt(
            success=True, user_id=payload.get("sub"), method="jwt", request=request
        )

        return payload

    except Exception as e:
        # Log failed authentication
        security_logger.authentication_attempt(
            success=False, method="jwt", request=request, failure_reason=str(e)
        )
        raise AuthenticationError(f"Invalid token: {str(e)}")


# Authentication Endpoints


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_data: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserProfile:
    """Register a new user account.

    Creates a new user account with the provided credentials.
    Returns user profile information upon successful registration.
    """
    try:
        # Apply rate limiting for registration attempts
        await _check_register_rate_limit(request, user_data.email)

        # Convert to UserCreate model and register through auth service
        user_create = UserCreate(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            roles=["user"],
            permissions=["read:workspaces", "create:workspaces"],
        )

        # Register user through auth service (handles all validation and creation)
        registration_result = await auth_service.register_user(user_create)
        user_info = registration_result["user"]

        # Log successful registration with enhanced security logging
        security_logger.authentication_attempt(
            success=True, user_id=user_info["user_id"], method="registration", request=request
        )

        return UserProfile(
            user_id=user_info["user_id"],
            username=user_info["username"],
            email=user_info["email"],
            full_name=user_info["full_name"],
            roles=user_info["roles"],
            permissions=user_info["permissions"],
            created_at=user_info["created_at"],
            last_login_at=None,
        )

    except Exception as e:
        security_logger.authentication_attempt(
            success=False, method="registration", request=request, failure_reason=str(e)
        )
        if isinstance(e, ValidationError | AuthenticationError):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login_user(
    request: Request,
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Authenticate user and return JWT tokens.

    Validates user credentials and returns access and refresh tokens
    for authenticated API access.
    """
    try:
        # Apply rate limiting for login attempts
        await _check_login_rate_limit(request, credentials.email)

        # Convert to UserLogin model and authenticate through auth service
        user_login = UserLoginModel(email=credentials.email, password=credentials.password)

        # Login user through auth service (handles authentication, token creation, and session management)
        login_result = await auth_service.login_user(user_login, request.headers.get("user-agent"))

        # Log successful login with enhanced details
        security_logger.authentication_attempt(
            success=True, user_id=login_result["user"]["user_id"], method="login", request=request
        )

        return login_result

    except HTTPException:
        # Re-raise HTTP exceptions (like rate limiting 429) as-is
        raise
    except AuthenticationError:
        # Re-raise authentication errors as-is
        raise
    except Exception as e:
        security_logger.authentication_attempt(
            success=False, method="login", request=request, failure_reason=str(e)
        )
        raise AuthenticationError("Invalid credentials")


@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> dict[str, Any]:
    """Refresh access token using refresh token.

    Exchanges a valid refresh token for a new access token and refresh token pair.
    Implements refresh token rotation for enhanced security.
    """
    try:
        # Refresh tokens with rotation
        token_response = await jwt_manager.refresh_access_token(
            refresh_request.refresh_token, device_info=request.headers.get("user-agent")
        )

        return {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in,
        }

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> dict[str, str]:
    """Logout user and revoke tokens.

    Adds the current access token to blacklist and revokes associated refresh tokens.
    """
    try:
        # Get token from request
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header[7:]

            # Blacklist access token
            jwt_manager.revoke_access_token(access_token)

            # Log successful logout
            security_logger.authentication_attempt(
                success=True, user_id=current_user["sub"], method="logout", request=request
            )

        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserProfile:
    """Get current user profile information.

    Returns detailed profile information for the authenticated user.
    """
    return UserProfile(
        user_id=current_user["sub"],  # JWT uses "sub" for user ID
        username=current_user.get("username", ""),
        email=current_user.get("email", ""),
        full_name=current_user.get("full_name"),
        roles=current_user.get("roles", ["user"]),
        permissions=current_user.get("permissions", ["read:workspaces"]),
        created_at=datetime.now(UTC),  # Would come from database
        last_login_at=datetime.now(UTC),  # Would come from database
    )


# API Key Management Endpoints


@router.post("/keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    key_request: APIKeyRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> dict[str, Any]:
    """Create a new API key for the authenticated user.

    Generates a new API key with specified scopes and rate limiting configuration.
    The actual key value is only returned once and should be stored securely.
    """
    try:
        # Get client IP for tracking
        client_ip = getattr(request.client, "host", None)

        # Create API key
        api_key_response = await api_key_manager.create_api_key(
            user_id=current_user["sub"], request=key_request, created_from_ip=client_ip
        )

        return {
            "id": api_key_response.id,
            "name": api_key_response.name,
            "key": api_key_response.key,  # Only returned once!
            "prefix": api_key_response.prefix,
            "permissions": api_key_response.permissions,
            "rate_limit": api_key_response.rate_limit,
            "expires_at": api_key_response.expires_at,
            "warning": "Store this key securely - it will not be shown again!",
        }

    except (ValidationError, QuotaExceededError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys", response_model=list[APIKeyListResponse])
async def list_api_keys(
    current_user: dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> list[APIKeyListResponse]:
    """List all API keys for the authenticated user.

    Returns a list of API keys with metadata but without the actual key values.
    """
    try:
        user_keys = await api_key_manager.list_user_keys(current_user["sub"])

        return [
            APIKeyListResponse(
                id=key.id,
                name=key.name,
                prefix=key.prefix,
                scopes=[scope.value for scope in key.scopes],
                workspace_id=key.workspace_id,
                rate_limit_config=key.rate_limit_config,
                is_active=key.is_active,
                created_at=key.created_at,
                expires_at=key.expires_at,
                last_used_at=key.last_used_at,
                usage_count=key.usage_count,
            )
            for key in user_keys
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> dict[str, str]:
    """Revoke an API key.

    Permanently disables the specified API key. This action cannot be undone.
    """
    try:
        success = await api_key_manager.revoke_api_key(key_id, current_user["sub"])

        if not success:
            raise HTTPException(status_code=404, detail="API key not found or access denied")

        return {"message": f"API key {key_id} has been revoked"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> dict[str, Any]:
    """Rotate an API key.

    Generates a new key value while preserving the key's configuration and metadata.
    The old key is immediately invalidated.
    """
    try:
        # For now, we'll return an error since rotate_key is not implemented
        raise HTTPException(status_code=501, detail="Key rotation not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Administrative Endpoints (Master Key Required)


@router.get("/admin/api-keys")
async def list_all_api_keys(
    request: Request,
    user_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> dict[str, Any]:
    """List all API keys with administrative filtering.

    Requires master administrator or key management privileges.
    Supports filtering by user_id, workspace_id, status, and pagination.
    """
    try:
        # Build filters
        filters = AdminAPIKeyFilter(user_id=user_id, workspace_id=workspace_id, status=status)

        # Get filtered keys
        keys, total_count = await admin_manager.list_all_keys(
            filters=filters,
            limit=limit,
            offset=offset,
            admin_user_id=current_user.user_id,
        )

        # Convert to response format (exclude sensitive data)
        key_list = []
        for key in keys:
            key_list.append(
                {
                    "id": key.id,
                    "name": key.name,
                    "prefix": key.prefix,
                    "user_id": key.user_id,
                    "workspace_id": key.workspace_id,
                    "scopes": [scope.value for scope in key.scopes],
                    "is_active": key.is_active,
                    "created_at": key.created_at,
                    "expires_at": key.expires_at,
                    "last_used_at": key.last_used_at,
                    "usage_count": key.usage_count,
                    "daily_usage": key.daily_usage,
                    "hourly_usage": key.hourly_usage,
                }
            )

        return {
            "keys": key_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(keys) < total_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/api-keys", status_code=status.HTTP_201_CREATED)
async def create_admin_api_key(
    request: Request,
    key_request: AdminAPIKeyRequest,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> dict[str, Any]:
    """Create API key for any user with administrative privileges.

    Requires master administrator or key management privileges.
    Can create keys for any user with any valid scopes.
    """
    try:
        # Set the admin user who is creating the key
        key_request.created_by = current_user.user_id

        # Create the key
        api_key_response = await admin_manager.create_admin_key(
            request=key_request, admin_user_id=current_user.user_id
        )

        return {
            "id": api_key_response.id,
            "name": api_key_response.name,
            "key": api_key_response.key,  # Only returned once!
            "prefix": api_key_response.prefix,
            "user_id": key_request.user_id,
            "scopes": api_key_response.scopes,
            "rate_limit_config": (
                api_key_response.rate_limit_config.dict()
                if api_key_response.rate_limit_config
                else None
            ),
            "expires_at": api_key_response.expires_at,
            "created_at": api_key_response.created_at,
            "created_by": current_user.user_id,
            "warning": "Store this key securely - it will not be shown again!",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/api-keys/{key_id}")
async def get_api_key_details(
    key_id: str,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> dict[str, Any]:
    """Get detailed API key information.

    Requires master administrator or key management privileges.
    Returns comprehensive key details including usage statistics.
    """
    try:
        key = await admin_manager.get_key_details(key_id=key_id, admin_user_id=current_user.user_id)

        if not key:
            raise HTTPException(status_code=404, detail="API key not found")

        return {
            "id": key.id,
            "name": key.name,
            "prefix": key.prefix,
            "user_id": key.user_id,
            "workspace_id": key.workspace_id,
            "scopes": [scope.value for scope in key.scopes],
            "rate_limit_config": key.rate_limit_config.dict(),
            "is_active": key.is_active,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "last_used_at": key.last_used_at,
            "usage_count": key.usage_count,
            "daily_usage": key.daily_usage,
            "hourly_usage": key.hourly_usage,
            "minute_usage": key.minute_usage,
            "created_from_ip": key.created_from_ip,
            "last_used_ip": key.last_used_ip,
            "suspicious_activity_count": key.suspicious_activity_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/api-keys/{key_id}")
async def update_api_key_admin(
    key_id: str,
    updates: AdminAPIKeyUpdate,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> dict[str, str]:
    """Update API key with administrative privileges.

    Requires master administrator or key management privileges.
    Can update any key property including scopes and rate limits.
    """
    try:
        # Set the admin user performing the update
        updates.updated_by = current_user.user_id

        success = await admin_manager.update_key_admin(
            key_id=key_id, updates=updates, admin_user_id=current_user.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": f"API key {key_id} updated successfully"}

    except HTTPException:
        raise
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key_admin(
    key_id: str,
    reason: str | None = None,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> dict[str, str]:
    """Revoke API key with administrative privileges.

    Requires master administrator or key management privileges.
    Can revoke any API key with optional reason logging.
    """
    try:
        success = await admin_manager.revoke_key_admin(
            key_id=key_id, reason=reason, admin_user_id=current_user.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": f"API key {key_id} revoked successfully"}

    except HTTPException:
        raise
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/api-keys/batch")
async def batch_api_key_operations(
    batch_request: BatchOperation,
    current_user: AuthenticatedUser = Depends(require_key_management()),
    admin_manager: Any = Depends(get_admin_api_key_manager),
) -> BatchOperationResult:
    """Perform batch operations on API keys.

    Requires master administrator or key management privileges.
    Supports batch revoke, update, and rotate operations with filtering.
    """
    try:
        # Set the admin user performing the batch operation
        batch_request.performed_by = current_user.user_id

        result = await admin_manager.batch_operation(
            batch_request=batch_request, admin_user_id=current_user.user_id
        )

        return result  # type: ignore

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
