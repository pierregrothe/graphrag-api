# src/graphrag_api_service/auth/database_auth.py
# Database-backed authentication service
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Database-backed authentication service for GraphRAG API."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database.models import Role, User
from .jwt_auth import JWTConfig, JWTManager, RoleBasedAccessControl, TokenData, UserCredentials

logger = logging.getLogger(__name__)


class DatabaseAuthenticationService:
    """Database-backed authentication service."""

    def __init__(self, jwt_config: JWTConfig, session_factory: Any) -> None:
        """Initialize database authentication service.

        Args:
            jwt_config: JWT configuration
            session_factory: Async session factory for database access
        """
        self.jwt_manager = JWTManager(jwt_config)
        self.rbac = RoleBasedAccessControl()
        self.session_factory = session_factory

    async def authenticate_user(self, credentials: UserCredentials) -> TokenData | None:
        """Authenticate a user with credentials.

        Args:
            credentials: User credentials

        Returns:
            Token data if authentication successful
        """
        async with self.session_factory() as session:
            # Get user with roles
            stmt = (
                select(User)
                .options(selectinload(User.roles))
                .where(User.username == credentials.username, User.is_active.is_(True))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning("Authentication failed: user not found - %s", credentials.username)
                return None

            if not self.jwt_manager.verify_password(credentials.password, user.password_hash):
                logger.warning("Authentication failed: invalid password - %s", credentials.username)
                return None

            # Update last login time
            user.last_login_at = datetime.now(UTC)
            await session.commit()

            # Get user permissions from roles
            permissions = []
            for role in user.roles:
                permissions.extend(role.permissions)

            # Create token data with expiration
            expires_at = datetime.now(UTC) + timedelta(
                minutes=self.jwt_manager.config.access_token_expire_minutes
            )

            token_data = TokenData(
                user_id=str(user.id),
                username=user.username,
                email=user.email,
                roles=[role.name for role in user.roles],
                permissions=list(set(permissions)),  # Remove duplicates
                tenant_id=user.tenant_id if hasattr(user, "tenant_id") else None,
                expires_at=expires_at,
            )

            logger.info("User authenticated successfully: %s", user.username)
            return token_data

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: list[str] | None = None,
        full_name: str | None = None,
        tenant_id: str | None = None,
    ) -> User:
        """Create a new user.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            roles: List of role names
            full_name: Full name
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Created user

        Raises:
            ValueError: If user already exists or roles don't exist
        """
        async with self.session_factory() as session:
            # Check if user already exists
            existing_user = await session.execute(
                select(User).where((User.username == username) | (User.email == email))
            )
            if existing_user.scalar_one_or_none():
                raise ValueError(
                    f"User with username '{username}' or email '{email}' already exists"
                )

            # Get roles
            user_roles = []
            if roles:
                role_stmt = select(Role).where(Role.name.in_(roles))
                role_result = await session.execute(role_stmt)
                user_roles = role_result.scalars().all()

                # Check if all roles exist
                found_role_names = {role.name for role in user_roles}
                missing_roles = set(roles) - found_role_names
                if missing_roles:
                    raise ValueError(f"Roles not found: {missing_roles}")

            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=self.jwt_manager.hash_password(password),
                full_name=full_name,
                tenant_id=tenant_id,
                is_active=True,
                is_verified=True,  # Auto-verify for now
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            # Add roles
            user.roles.extend(user_roles)

            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info("Created user: %s with roles: %s", username, roles)
            return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None if not found
        """
        async with self.session_factory() as session:
            stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
            result = await session.execute(stmt)
            user: User | None = result.scalar_one_or_none()
            return user

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User or None if not found
        """
        async with self.session_factory() as session:
            stmt = select(User).options(selectinload(User.roles)).where(User.username == username)
            result = await session.execute(stmt)
            user: User | None = result.scalar_one_or_none()
            return user

    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password.

        Args:
            user_id: User ID
            new_password: New plain text password

        Returns:
            True if password updated successfully
        """
        async with self.session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return False

            user.password_hash = self.jwt_manager.hash_password(new_password)
            user.updated_at = datetime.now(UTC)
            await session.commit()

            logger.info("Updated password for user: %s", user.username)
            return True

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            True if user deactivated successfully
        """
        async with self.session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                return False

            user.is_active = False
            user.updated_at = datetime.now(UTC)
            await session.commit()

            logger.info("Deactivated user: %s", user.username)
            return True

    async def create_default_roles(self) -> None:
        """Create default roles if they don't exist."""
        async with self.session_factory() as session:
            # Define default roles
            default_roles = [
                {
                    "name": "admin",
                    "description": "Administrator with full permissions",
                    "permissions": ["manage:all", "read:all", "write:all", "delete:all"],
                },
                {
                    "name": "user",
                    "description": "Regular user with basic permissions",
                    "permissions": ["read:own", "write:own"],
                },
                {"name": "viewer", "description": "Read-only user", "permissions": ["read:own"]},
            ]

            for role_data in default_roles:
                # Check if role exists
                existing = await session.execute(select(Role).where(Role.name == role_data["name"]))
                if existing.scalar_one_or_none():
                    continue

                # Create role
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(role)

            await session.commit()
            logger.info("Default roles created successfully")

    def generate_token(self, token_data: TokenData) -> str:
        """Generate JWT token for user.

        Args:
            token_data: Token data

        Returns:
            JWT token string
        """
        return self.jwt_manager.create_access_token(token_data)

    def verify_token(self, token: str) -> TokenData | None:
        """Verify JWT token.

        Args:
            token: JWT token string

        Returns:
            Token data if valid, None otherwise
        """
        try:
            payload = self.jwt_manager.verify_token(token)
            if payload:
                # Convert dict to TokenData - ensure required fields are not None
                user_id = payload.get("user_id")
                username = payload.get("username")
                email = payload.get("email")
                exp_str = payload.get("exp")

                # Validate required fields
                if not all([user_id, username, email, exp_str]):
                    return None

                # Type assert after validation - we know these are not None
                assert isinstance(user_id, str)
                assert isinstance(username, str)
                assert isinstance(email, str)

                # Convert exp timestamp to datetime
                if isinstance(exp_str, int | float):
                    expires_at = datetime.fromtimestamp(exp_str, tz=UTC)
                else:
                    expires_at = datetime.fromisoformat(str(exp_str))

                return TokenData(
                    user_id=user_id,
                    username=username,
                    email=email,
                    roles=payload.get("roles", []),
                    permissions=payload.get("permissions", []),
                    tenant_id=payload.get("tenant_id"),
                    expires_at=expires_at,
                )
            return None
        except Exception:
            return None
