"""
Authentication routes for GraphRAG API Service.

This module provides comprehensive authentication endpoints including
user registration, login, token refresh, logout, and API key management.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from ..auth.api_keys import APIKeyManager, APIKeyRequest, APIKeyScope, RateLimitConfig
from ..auth.admin_api_keys import (
    get_admin_api_key_manager,
    AdminAPIKeyRequest,
    AdminAPIKeyFilter,
    AdminAPIKeyUpdate,
    BatchOperation,
    BatchOperationResult
)
from ..auth.jwt_auth import JWTManager, JWTConfig, TokenData
from ..auth.unified_auth import require_master_admin, require_key_management, require_system_admin
from ..config import get_settings
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    QuotaExceededError
)
from ..security import get_security_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)
security_logger = get_security_logger()


# Request/Response Models
class UserRegistration(BaseModel):
    """User registration request."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """User login request."""
    
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str


class UserProfile(BaseModel):
    """User profile response."""
    
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login_at: Optional[datetime]


class APIKeyListResponse(BaseModel):
    """API key list response."""
    
    id: str
    name: str
    prefix: str
    scopes: List[str]
    workspace_id: Optional[str]
    rate_limit_config: RateLimitConfig
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int


# Dependency injection
async def get_jwt_manager() -> JWTManager:
    """Get JWT manager instance."""
    settings = get_settings()
    config = JWTConfig(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days
    )
    return JWTManager(config)


async def get_api_key_manager() -> APIKeyManager:
    """Get API key manager instance."""
    return APIKeyManager()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    jwt_manager: JWTManager = Depends(get_jwt_manager)
) -> Dict[str, Any]:
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
            success=True,
            user_id=payload.get("sub"),
            method="jwt",
            request=request
        )
        
        return payload
        
    except Exception as e:
        # Log failed authentication
        security_logger.authentication_attempt(
            success=False,
            method="jwt",
            request=request,
            failure_reason=str(e)
        )
        raise AuthenticationError(f"Invalid token: {str(e)}")


# Authentication Endpoints

@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_data: UserRegistration,
    jwt_manager: JWTManager = Depends(get_jwt_manager)
) -> UserProfile:
    """Register a new user account.
    
    Creates a new user account with the provided credentials.
    Returns user profile information upon successful registration.
    """
    try:
        # Validate password strength
        if len(user_data.password) < 8:
            raise ValidationError("Password must be at least 8 characters long", field="password")
        
        # Hash password
        password_hash = jwt_manager.hash_password(user_data.password)
        
        # Create user (this would typically interact with database)
        user_id = f"user_{datetime.utcnow().timestamp()}"
        
        # Log successful registration
        security_logger.authentication_attempt(
            success=True,
            user_id=user_id,
            method="registration",
            request=request
        )
        
        return UserProfile(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            roles=["user"],
            permissions=["read:workspaces"],
            created_at=datetime.utcnow(),
            last_login_at=None
        )
        
    except Exception as e:
        security_logger.authentication_attempt(
            success=False,
            method="registration",
            request=request,
            failure_reason=str(e)
        )
        if isinstance(e, (ValidationError, AuthenticationError)):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login_user(
    request: Request,
    credentials: UserLogin,
    jwt_manager: JWTManager = Depends(get_jwt_manager)
) -> Dict[str, Any]:
    """Authenticate user and return JWT tokens.
    
    Validates user credentials and returns access and refresh tokens
    for authenticated API access.
    """
    try:
        # This would typically verify against database
        # For now, simulate user authentication
        user_id = f"user_{credentials.email.split('@')[0]}"
        
        # Create token data
        token_data = TokenData(
            user_id=user_id,
            username=credentials.email.split('@')[0],
            email=credentials.email,
            roles=["user"],
            permissions=["read:workspaces", "write:workspaces"],
            expires_at=datetime.utcnow()
        )
        
        # Create tokens
        access_token = jwt_manager.create_access_token(token_data)
        refresh_token = jwt_manager.create_refresh_token(
            user_id, 
            device_info=request.headers.get("user-agent")
        )
        
        # Log successful login
        security_logger.authentication_attempt(
            success=True,
            user_id=user_id,
            method="login",
            request=request
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_manager.config.access_token_expire_minutes * 60,
            "user": {
                "user_id": user_id,
                "username": token_data.username,
                "email": token_data.email,
                "roles": token_data.roles
            }
        }
        
    except Exception as e:
        security_logger.authentication_attempt(
            success=False,
            method="login",
            request=request,
            failure_reason=str(e)
        )
        raise AuthenticationError("Invalid credentials")


@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager)
) -> Dict[str, Any]:
    """Refresh access token using refresh token.
    
    Exchanges a valid refresh token for a new access token and refresh token pair.
    Implements refresh token rotation for enhanced security.
    """
    try:
        # Refresh tokens with rotation
        token_response = await jwt_manager.refresh_access_token(
            refresh_request.refresh_token,
            device_info=request.headers.get("user-agent")
        )
        
        return {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in
        }
        
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    jwt_manager: JWTManager = Depends(get_jwt_manager)
) -> Dict[str, str]:
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
                success=True,
                user_id=current_user.get("sub"),
                method="logout",
                request=request
            )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserProfile:
    """Get current user profile information.
    
    Returns detailed profile information for the authenticated user.
    """
    return UserProfile(
        user_id=current_user["sub"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        roles=current_user.get("roles", []),
        permissions=current_user.get("permissions", []),
        created_at=datetime.utcnow(),  # Would come from database
        last_login_at=datetime.utcnow()  # Would come from database
    )


# API Key Management Endpoints

@router.post("/keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    key_request: APIKeyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
) -> Dict[str, Any]:
    """Create a new API key for the authenticated user.

    Generates a new API key with specified scopes and rate limiting configuration.
    The actual key value is only returned once and should be stored securely.
    """
    try:
        # Get client IP for tracking
        client_ip = getattr(request.client, 'host', None)

        # Create API key
        api_key_response = await api_key_manager.create_api_key(
            user_id=current_user["sub"],
            request=key_request,
            created_from_ip=client_ip
        )

        return {
            "id": api_key_response.id,
            "name": api_key_response.name,
            "key": api_key_response.key,  # Only returned once!
            "prefix": api_key_response.prefix,
            "scopes": api_key_response.scopes,
            "rate_limit_config": api_key_response.rate_limit_config.dict(),
            "expires_at": api_key_response.expires_at,
            "created_at": api_key_response.created_at,
            "warning": "Store this key securely - it will not be shown again!"
        }

    except (ValidationError, QuotaExceededError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys", response_model=List[APIKeyListResponse])
async def list_api_keys(
    current_user: Dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
) -> List[APIKeyListResponse]:
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
                usage_count=key.usage_count
            )
            for key in user_keys
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
) -> Dict[str, str]:
    """Revoke an API key.

    Permanently disables the specified API key. This action cannot be undone.
    """
    try:
        success = await api_key_manager.revoke_key(key_id, current_user["sub"])

        if not success:
            raise HTTPException(
                status_code=404,
                detail="API key not found or access denied"
            )

        return {"message": f"API key {key_id} has been revoked"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
) -> Dict[str, Any]:
    """Rotate an API key.

    Generates a new key value while preserving the key's configuration and metadata.
    The old key is immediately invalidated.
    """
    try:
        new_key_response = await api_key_manager.rotate_key(key_id, current_user["sub"])

        if not new_key_response:
            raise HTTPException(
                status_code=404,
                detail="API key not found or access denied"
            )

        return {
            "id": new_key_response.id,
            "name": new_key_response.name,
            "key": new_key_response.key,  # New key value
            "prefix": new_key_response.prefix,
            "message": "API key rotated successfully",
            "warning": "Store this new key securely - the old key is now invalid!"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Administrative Endpoints (Master Key Required)

@router.get("/admin/api-keys")
async def list_all_api_keys(
    request: Request,
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> Dict[str, Any]:
    """List all API keys with administrative filtering.

    Requires master administrator or key management privileges.
    Supports filtering by user_id, workspace_id, status, and pagination.
    """
    try:
        # Build filters
        filters = AdminAPIKeyFilter(
            user_id=user_id,
            workspace_id=workspace_id,
            status=status
        )

        # Get filtered keys
        keys, total_count = await admin_manager.list_all_keys(
            filters=filters,
            limit=limit,
            offset=offset,
            admin_user_id=current_user.user_id
        )

        # Convert to response format (exclude sensitive data)
        key_list = []
        for key in keys:
            key_list.append({
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
                "hourly_usage": key.hourly_usage
            })

        return {
            "keys": key_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(keys) < total_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/api-keys", status_code=status.HTTP_201_CREATED)
async def create_admin_api_key(
    request: Request,
    key_request: AdminAPIKeyRequest,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> Dict[str, Any]:
    """Create API key for any user with administrative privileges.

    Requires master administrator or key management privileges.
    Can create keys for any user with any valid scopes.
    """
    try:
        # Set the admin user who is creating the key
        key_request.created_by = current_user.user_id

        # Create the key
        api_key_response = await admin_manager.create_admin_key(
            request=key_request,
            admin_user_id=current_user.user_id
        )

        return {
            "id": api_key_response.id,
            "name": api_key_response.name,
            "key": api_key_response.key,  # Only returned once!
            "prefix": api_key_response.prefix,
            "user_id": key_request.user_id,
            "scopes": api_key_response.scopes,
            "rate_limit_config": api_key_response.rate_limit_config.dict() if api_key_response.rate_limit_config else None,
            "expires_at": api_key_response.expires_at,
            "created_at": api_key_response.created_at,
            "created_by": current_user.user_id,
            "warning": "Store this key securely - it will not be shown again!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/api-keys/{key_id}")
async def get_api_key_details(
    key_id: str,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> Dict[str, Any]:
    """Get detailed API key information.

    Requires master administrator or key management privileges.
    Returns comprehensive key details including usage statistics.
    """
    try:
        key = await admin_manager.get_key_details(
            key_id=key_id,
            admin_user_id=current_user.user_id
        )

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
            "suspicious_activity_count": key.suspicious_activity_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/api-keys/{key_id}")
async def update_api_key_admin(
    key_id: str,
    updates: AdminAPIKeyUpdate,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> Dict[str, str]:
    """Update API key with administrative privileges.

    Requires master administrator or key management privileges.
    Can update any key property including scopes and rate limits.
    """
    try:
        # Set the admin user performing the update
        updates.updated_by = current_user.user_id

        success = await admin_manager.update_key_admin(
            key_id=key_id,
            updates=updates,
            admin_user_id=current_user.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": f"API key {key_id} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key_admin(
    key_id: str,
    reason: Optional[str] = None,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> Dict[str, str]:
    """Revoke API key with administrative privileges.

    Requires master administrator or key management privileges.
    Can revoke any API key with optional reason logging.
    """
    try:
        success = await admin_manager.revoke_key_admin(
            key_id=key_id,
            reason=reason,
            admin_user_id=current_user.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": f"API key {key_id} revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/api-keys/batch")
async def batch_api_key_operations(
    batch_request: BatchOperation,
    current_user = Depends(require_key_management()),
    admin_manager = Depends(get_admin_api_key_manager)
) -> BatchOperationResult:
    """Perform batch operations on API keys.

    Requires master administrator or key management privileges.
    Supports batch revoke, update, and rotate operations with filtering.
    """
    try:
        # Set the admin user performing the batch operation
        batch_request.performed_by = current_user.user_id

        result = await admin_manager.batch_operation(
            batch_request=batch_request,
            admin_user_id=current_user.user_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
