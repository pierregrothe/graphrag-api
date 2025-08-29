# src/graphrag_api_service/auth/jwt_auth.py
# JWT Authentication System for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""JWT-based authentication system with role-based access control."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """Token data model."""

    user_id: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]
    tenant_id: str | None = None
    expires_at: datetime


class UserCredentials(BaseModel):
    """User credentials model."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class JWTConfig:
    """JWT configuration."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: str = "graphrag-api",
        audience: str = "graphrag-users",
    ):
        """Initialize JWT configuration.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
            issuer: Token issuer
            audience: Token audience
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience


class JWTManager:
    """JWT token management."""

    def __init__(self, config: JWTConfig):
        """Initialize JWT manager.

        Args:
            config: JWT configuration
        """
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(self, token_data: TokenData) -> str:
        """Create an access token.

        Args:
            token_data: Token data

        Returns:
            Encoded JWT token
        """
        expire = datetime.now(UTC) + timedelta(
            minutes=self.config.access_token_expire_minutes
        )

        payload = {
            "sub": token_data.user_id,
            "username": token_data.username,
            "email": token_data.email,
            "roles": token_data.roles,
            "permissions": token_data.permissions,
            "tenant_id": token_data.tenant_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": "access",
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token.

        Args:
            user_id: User ID

        Returns:
            Encoded JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": "refresh",
        }

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def refresh_access_token(self, refresh_token: str, user_data: TokenData) -> str:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: Valid refresh token
            user_data: Updated user data

        Returns:
            New access token

        Raises:
            HTTPException: If refresh token is invalid
        """
        payload = self.verify_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        return self.create_access_token(user_data)

    def hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)


class RoleBasedAccessControl:
    """Role-based access control system."""

    def __init__(self):
        """Initialize RBAC system."""
        self.roles: dict[str, list[str]] = {
            "admin": [
                "read:all",
                "write:all",
                "delete:all",
                "manage:users",
                "manage:workspaces",
                "manage:system",
            ],
            "user": ["read:own", "write:own", "read:workspaces", "write:workspaces"],
            "viewer": ["read:own", "read:workspaces"],
            "api_user": ["read:api", "write:api"],
        }

    def get_permissions(self, roles: list[str]) -> list[str]:
        """Get permissions for given roles.

        Args:
            roles: List of role names

        Returns:
            List of permissions
        """
        permissions = set()
        for role in roles:
            if role in self.roles:
                permissions.update(self.roles[role])
        return list(permissions)

    def has_permission(self, user_permissions: list[str], required_permission: str) -> bool:
        """Check if user has required permission.

        Args:
            user_permissions: User's permissions
            required_permission: Required permission

        Returns:
            True if user has permission
        """
        # Check for exact match
        if required_permission in user_permissions:
            return True

        # Check for wildcard permissions
        for permission in user_permissions:
            if permission.endswith(":all"):
                permission_type = permission.split(":")[0]
                if required_permission.startswith(f"{permission_type}:"):
                    return True

        return False

    def check_tenant_access(
        self, user_tenant: str | None, resource_tenant: str | None
    ) -> bool:
        """Check if user has access to resource based on tenant.

        Args:
            user_tenant: User's tenant ID
            resource_tenant: Resource's tenant ID

        Returns:
            True if user has access
        """
        # If no tenant restrictions, allow access
        if not resource_tenant:
            return True

        # If user has no tenant, deny access to tenant-specific resources
        if not user_tenant:
            return False

        # Allow access if tenants match
        return user_tenant == resource_tenant


class AuthenticationService:
    """Authentication service combining JWT and RBAC."""

    def __init__(self, jwt_config: JWTConfig):
        """Initialize authentication service.

        Args:
            jwt_config: JWT configuration
        """
        self.jwt_manager = JWTManager(jwt_config)
        self.rbac = RoleBasedAccessControl()
        self.users: dict[str, dict[str, Any]] = {}  # In-memory user store (replace with database)

    async def authenticate_user(self, credentials: UserCredentials) -> TokenData | None:
        """Authenticate a user with credentials.

        Args:
            credentials: User credentials

        Returns:
            Token data if authentication successful
        """
        user = self.users.get(credentials.username)
        if not user:
            return None

        if not self.jwt_manager.verify_password(credentials.password, user["password_hash"]):
            return None

        permissions = self.rbac.get_permissions(user["roles"])

        return TokenData(
            user_id=user["id"],
            username=user["username"],
            email=user["email"],
            roles=user["roles"],
            permissions=permissions,
            tenant_id=user.get("tenant_id"),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=self.jwt_manager.config.access_token_expire_minutes),
        )

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: list[str],
        tenant_id: str | None = None,
    ) -> str:
        """Create a new user.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            roles: User roles
            tenant_id: Optional tenant ID

        Returns:
            User ID
        """
        user_id = f"user_{len(self.users) + 1}"
        password_hash = self.jwt_manager.hash_password(password)

        self.users[username] = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "roles": roles,
            "tenant_id": tenant_id,
            "created_at": datetime.now(UTC),
            "is_active": True,
        }

        logger.info(f"Created user: {username} with roles: {roles}")
        return user_id

    async def login(self, credentials: UserCredentials) -> TokenResponse:
        """Login user and return tokens.

        Args:
            credentials: User credentials

        Returns:
            Token response

        Raises:
            HTTPException: If authentication fails
        """
        token_data = await self.authenticate_user(credentials)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        access_token = self.jwt_manager.create_access_token(token_data)
        refresh_token = self.jwt_manager.create_refresh_token(token_data.user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.jwt_manager.config.access_token_expire_minutes * 60,
        )

    def verify_permission(self, token_data: TokenData, required_permission: str) -> bool:
        """Verify if user has required permission.

        Args:
            token_data: User token data
            required_permission: Required permission

        Returns:
            True if user has permission
        """
        return self.rbac.has_permission(token_data.permissions, required_permission)
