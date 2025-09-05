# src/graphrag_api_service/services/auth_service.py
# Authentication service for business logic
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Authentication service providing business logic for user authentication and management."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..auth.jwt_auth import JWTManager, TokenData
from ..database.sqlite_models import SQLiteManager
from ..exceptions import AuthenticationError, ValidationError
from ..models.user import User, UserCreate, UserLogin, UserPasswordUpdate, UserUpdate
from ..repositories.user_repository import UserRepository
from ..services.interfaces import AuthenticationServiceProtocol, BaseService
from ..utils.security import (
    InputSanitizer,
    PasswordValidator,
    validate_password_strength,
)

logger = logging.getLogger(__name__)


class AuthService(BaseService, AuthenticationServiceProtocol):
    """Authentication service implementing business logic for user authentication.

    This service provides high-level authentication operations including user
    registration, login, token management, and session handling. It integrates
    with the existing JWT system and provides a clean interface for auth operations.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_manager: JWTManager,
        db_manager: SQLiteManager,
    ):
        """Initialize authentication service.

        Args:
            user_repository: User repository for data access
            jwt_manager: JWT manager for token operations
            db_manager: Database manager for session operations
        """
        super().__init__("AuthService")
        self.user_repository = user_repository
        self.jwt_manager = jwt_manager
        self.db_manager = db_manager
        self.password_validator = PasswordValidator()
        self.input_sanitizer = InputSanitizer()

    async def register_user(self, user_data: UserCreate) -> dict[str, Any]:
        """Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Dictionary containing user info and tokens

        Raises:
            ValidationError: If registration data is invalid
            AuthenticationError: If registration fails
        """
        try:
            self.logger.info(f"Registering new user: {user_data.username}")

            # Validate and sanitize input
            await self._validate_registration_data(user_data)

            # Validate password strength
            validate_password_strength(user_data.password)

            # Create user through repository
            new_user = await self.user_repository.create_user(user_data)

            # Generate tokens for the new user
            token_data = TokenData(
                user_id=new_user.user_id,
                username=new_user.username,
                email=new_user.email,
                roles=new_user.roles,
                permissions=new_user.permissions,
                expires_at=datetime.now(UTC),
                tenant_id=None,
            )

            access_token = self.jwt_manager.create_access_token(token_data)
            refresh_token = self.jwt_manager.create_refresh_token(new_user.user_id)

            # Create user session
            session_id = self.db_manager.create_user_session(
                user_id=new_user.user_id,
                refresh_token=refresh_token,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )

            self.logger.info(f"Successfully registered user: {new_user.username}")

            return {
                "user": {
                    "user_id": new_user.user_id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "roles": new_user.roles,
                    "permissions": new_user.permissions,
                    "is_active": new_user.is_active,
                    "created_at": new_user.created_at,
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_manager.config.access_token_expire_minutes * 60,
                "session_id": session_id,
            }

        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            self.logger.error(f"Registration failed for {user_data.username}: {e}")
            raise AuthenticationError(f"Registration failed: {str(e)}")

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            User data dictionary if authentication successful, None otherwise
        """
        try:
            self.logger.debug(f"Authenticating user: {email}")

            # Sanitize email
            email = self.input_sanitizer.sanitize_email(email)

            # Authenticate through repository
            user = await self.user_repository.authenticate_user(email, password)

            if user and user.is_active:
                # Update last login
                await self.user_repository.update_last_login(user.user_id)

                self.logger.info(f"Successfully authenticated user: {email}")

                return {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.roles,
                    "permissions": user.permissions,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "tenant_id": None,
                }

            self.logger.warning(f"Authentication failed for: {email}")
            return None

        except Exception as e:
            self.logger.error(f"Authentication error for {email}: {e}")
            return None

    async def login_user(
        self, login_data: UserLogin, device_info: str | None = None
    ) -> dict[str, Any]:
        """Login user and create session.

        Args:
            login_data: User login credentials
            device_info: Optional device information

        Returns:
            Dictionary containing user info and tokens

        Raises:
            AuthenticationError: If login fails
        """
        try:
            self.logger.info(f"User login attempt: {login_data.email}")

            # Authenticate user
            user_data = await self.authenticate_user(login_data.email, login_data.password)

            if not user_data:
                raise AuthenticationError("Invalid email or password")

            # Create token data
            token_data = TokenData(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                roles=user_data["roles"],
                permissions=user_data["permissions"],
                expires_at=datetime.now(UTC),
                tenant_id=user_data.get("tenant_id"),
            )

            # Generate tokens
            access_token = self.jwt_manager.create_access_token(token_data)
            refresh_token = self.jwt_manager.create_refresh_token(
                user_data["user_id"], device_info=device_info
            )

            # Create user session
            session_id = self.db_manager.create_user_session(
                user_id=user_data["user_id"],
                refresh_token=refresh_token,
                device_info=device_info,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )

            self.logger.info(f"Successfully logged in user: {login_data.email}")

            return {
                "user": user_data,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_manager.config.access_token_expire_minutes * 60,
                "session_id": session_id,
            }

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Login failed for {login_data.email}: {e}")
            raise AuthenticationError(f"Login failed: {str(e)}")

    async def refresh_access_token(
        self, refresh_token: str, device_info: str | None = None
    ) -> dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token
            device_info: Optional device information

        Returns:
            Dictionary containing new tokens

        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            self.logger.debug("Refreshing access token")

            # Validate refresh token
            session_data = self.db_manager.validate_refresh_token(refresh_token)

            if not session_data:
                raise AuthenticationError("Invalid or expired refresh token")

            # Get user data
            user = await self.user_repository.get_user_by_id(session_data["user_id"])

            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")

            # Create new token data
            token_data = TokenData(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                roles=user.roles,
                permissions=user.permissions,
                expires_at=datetime.now(UTC),
                tenant_id=None,
            )

            # Generate new tokens
            new_access_token = self.jwt_manager.create_access_token(token_data)
            new_refresh_token = self.jwt_manager.create_refresh_token(
                user.user_id, device_info=device_info
            )

            # Create new session (old one is automatically invalidated)
            session_id = self.db_manager.create_user_session(
                user_id=user.user_id,
                refresh_token=new_refresh_token,
                device_info=device_info,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )

            self.logger.info(f"Successfully refreshed token for user: {user.user_id}")

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_manager.config.access_token_expire_minutes * 60,
                "session_id": session_id,
            }

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    async def logout_user(self, user_id: str, session_id: str | None = None) -> bool:
        """Logout user and revoke session.

        Args:
            user_id: User ID
            session_id: Optional specific session to revoke

        Returns:
            True if logout successful
        """
        try:
            self.logger.info(f"Logging out user: {user_id}")

            if session_id:
                # Revoke specific session
                success = self.db_manager.revoke_user_session(session_id)
            else:
                # Revoke all user sessions
                revoked_count = self.db_manager.revoke_all_user_sessions(user_id)
                success = revoked_count > 0

            if success:
                self.logger.info(f"Successfully logged out user: {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Logout failed for user {user_id}: {e}")
            return False

    async def create_access_token(self, user_data: dict[str, Any]) -> str:
        """Create JWT access token for user.

        Args:
            user_data: User data dictionary

        Returns:
            JWT access token
        """
        try:
            token_data = TokenData(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                roles=user_data.get("roles", ["user"]),
                permissions=user_data.get("permissions", ["read:workspaces"]),
                expires_at=datetime.now(UTC),
                tenant_id=user_data.get("tenant_id"),
            )

            return self.jwt_manager.create_access_token(token_data)

        except Exception as e:
            self.logger.error(f"Failed to create access token: {e}")
            raise AuthenticationError(f"Token creation failed: {str(e)}")

    async def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Check if token is blacklisted
            if self.jwt_manager.is_token_blacklisted(token):
                return None

            # Verify token
            payload = self.jwt_manager.verify_token(token)

            return payload

        except Exception as e:
            self.logger.debug(f"Token verification failed: {e}")
            return None

    async def authenticate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Authenticate user with API key.

        Args:
            api_key: API key to authenticate

        Returns:
            User data if authentication successful, None otherwise
        """
        try:
            # This would integrate with the existing API key system
            # For now, return None as API key auth is handled elsewhere
            self.logger.debug("API key authentication not implemented in auth service")
            return None

        except Exception as e:
            self.logger.error(f"API key authentication failed: {e}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: UserUpdate) -> User:
        """Update user profile.

        Args:
            user_id: User ID
            profile_data: Profile update data

        Returns:
            Updated user model

        Raises:
            ValidationError: If update data is invalid
            AuthenticationError: If user not found
        """
        try:
            self.logger.info(f"Updating profile for user: {user_id}")

            # Validate and sanitize input
            await self._validate_profile_update(profile_data)

            # Update through repository
            updated_user = await self.user_repository.update_user(user_id, profile_data)

            self.logger.info(f"Successfully updated profile for user: {user_id}")

            return updated_user

        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            self.logger.error(f"Profile update failed for user {user_id}: {e}")
            raise AuthenticationError(f"Profile update failed: {str(e)}")

    async def change_password(self, user_id: str, password_data: UserPasswordUpdate) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            password_data: Password change data

        Returns:
            True if password changed successfully

        Raises:
            ValidationError: If password data is invalid
            AuthenticationError: If current password is incorrect
        """
        try:
            self.logger.info(f"Changing password for user: {user_id}")

            # Get current user
            user = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            # Verify current password
            if not self.db_manager.verify_password(
                password_data.current_password, user.password_hash
            ):
                raise AuthenticationError("Current password is incorrect")

            # Validate new password strength
            validate_password_strength(password_data.new_password)

            # Update password
            success = await self.user_repository.update_password(
                user_id, password_data.new_password
            )

            if success:
                # Revoke all user sessions to force re-login
                self.db_manager.revoke_all_user_sessions(user_id)
                self.logger.info(f"Successfully changed password for user: {user_id}")

            return success

        except (ValidationError, AuthenticationError):
            raise
        except Exception as e:
            self.logger.error(f"Password change failed for user {user_id}: {e}")
            raise AuthenticationError(f"Password change failed: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """Perform service health check.

        Returns:
            Health check results
        """
        try:
            # Test database connectivity
            await self.user_repository.get_user_by_id("health_check_test")

            # Test JWT manager
            test_token_data = TokenData(
                user_id="test",
                username="test",
                email="test@example.com",
                roles=["user"],
                permissions=["read:workspaces"],
                expires_at=datetime.now(UTC),
            )
            test_token = self.jwt_manager.create_access_token(test_token_data)
            self.jwt_manager.verify_token(test_token)

            return {
                "status": "healthy",
                "service": "AuthService",
                "timestamp": datetime.now(UTC).isoformat(),
                "checks": {
                    "database": "ok",
                    "jwt_manager": "ok",
                    "user_repository": "ok",
                },
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "AuthService",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            }

    async def _validate_registration_data(self, user_data: UserCreate) -> None:
        """Validate user registration data.

        Args:
            user_data: User registration data

        Raises:
            ValidationError: If data is invalid
        """
        # Sanitize and validate username
        try:
            user_data.username = self.input_sanitizer.sanitize_username(user_data.username)
        except ValidationError as e:
            raise ValidationError(f"Invalid username: {str(e)}")

        # Sanitize and validate email
        try:
            user_data.email = self.input_sanitizer.sanitize_email(user_data.email)
        except ValidationError as e:
            raise ValidationError(f"Invalid email: {str(e)}")

        # Sanitize full name if provided
        if user_data.full_name:
            user_data.full_name = self.input_sanitizer.sanitize_string(user_data.full_name, 100)

    async def _validate_profile_update(self, profile_data: UserUpdate) -> None:
        """Validate profile update data.

        Args:
            profile_data: Profile update data

        Raises:
            ValidationError: If data is invalid
        """
        # Sanitize and validate username if provided
        if profile_data.username is not None:
            try:
                profile_data.username = self.input_sanitizer.sanitize_username(
                    profile_data.username
                )
            except ValidationError as e:
                raise ValidationError(f"Invalid username: {str(e)}")

        # Sanitize and validate email if provided
        if profile_data.email is not None:
            try:
                profile_data.email = self.input_sanitizer.sanitize_email(profile_data.email)
            except ValidationError as e:
                raise ValidationError(f"Invalid email: {str(e)}")

        # Sanitize full name if provided
        if profile_data.full_name is not None:
            profile_data.full_name = self.input_sanitizer.sanitize_string(
                profile_data.full_name, 100
            )
