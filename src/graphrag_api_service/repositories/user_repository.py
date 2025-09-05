# src/graphrag_api_service/repositories/user_repository.py
# User repository for data access operations
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""User repository for handling user data access operations."""

import json
import logging

from ..database.sqlite_models import SQLiteManager
from ..exceptions import ResourceNotFoundError, ValidationError
from ..models.user import User, UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data access operations.

    This repository provides a clean interface for user data operations,
    abstracting the database implementation details and providing consistent
    error handling and logging.
    """

    def __init__(self, db_manager: SQLiteManager):
        """Initialize user repository.

        Args:
            db_manager: SQLite database manager instance
        """
        self.db_manager = db_manager
        self.logger = logger

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username to search for

        Returns:
            User model if found, None otherwise

        Raises:
            ValidationError: If username is invalid
        """
        try:
            if not username or not username.strip():
                raise ValidationError("Username cannot be empty")

            user_data = self.db_manager.get_user_by_username(username.strip())

            if user_data:
                return User(**user_data)

            return None

        except Exception as e:
            self.logger.error(f"Error getting user by username {username}: {e}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to retrieve user: {str(e)}")

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            User model if found, None otherwise

        Raises:
            ValidationError: If email is invalid
        """
        try:
            if not email or not email.strip():
                raise ValidationError("Email cannot be empty")

            user_data = self.db_manager.get_user_by_email(email.strip().lower())

            if user_data:
                return User(**user_data)

            return None

        except Exception as e:
            self.logger.error(f"Error getting user by email {email}: {e}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to retrieve user: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID to search for

        Returns:
            User model if found, None otherwise

        Raises:
            ValidationError: If user_id is invalid
        """
        try:
            if not user_id or not user_id.strip():
                raise ValidationError("User ID cannot be empty")

            user_data = self.db_manager.get_user_by_id(user_id.strip())

            if user_data:
                return User(**user_data)

            return None

        except Exception as e:
            self.logger.error(f"Error getting user by ID {user_id}: {e}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to retrieve user: {str(e)}")

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user.

        Args:
            user_create: User creation data

        Returns:
            Created user model

        Raises:
            ValidationError: If user data is invalid or user already exists
        """
        try:
            # Check if user already exists
            if await self.user_exists(user_create.email, user_create.username):
                raise ValidationError("User with this email or username already exists")

            # Create user in database
            user_data = self.db_manager.create_user(
                username=user_create.username,
                email=user_create.email,
                password=user_create.password,
                full_name=user_create.full_name,
                roles=user_create.roles,
                permissions=user_create.permissions,
                is_admin=user_create.is_admin,
            )

            self.logger.info(f"Created user: {user_create.username} ({user_create.email})")

            return User(**user_data)

        except Exception as e:
            self.logger.error(f"Error creating user {user_create.username}: {e}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to create user: {str(e)}")

    async def update_user(self, user_id: str, user_update: UserUpdate) -> User:
        """Update user information.

        Args:
            user_id: ID of user to update
            user_update: User update data

        Returns:
            Updated user model

        Raises:
            ResourceNotFoundError: If user not found
            ValidationError: If update data is invalid
        """
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise ResourceNotFoundError(f"User with ID {user_id} not found")

            # Prepare update data (only include non-None fields)
            update_data = {}
            if user_update.username is not None:
                update_data["username"] = user_update.username
            if user_update.email is not None:
                update_data["email"] = user_update.email.lower()
            if user_update.full_name is not None:
                update_data["full_name"] = user_update.full_name
            if user_update.is_active is not None:
                update_data["is_active"] = str(1 if user_update.is_active else 0)
            if user_update.roles is not None:
                update_data["roles"] = json.dumps(user_update.roles)
            if user_update.permissions is not None:
                update_data["permissions"] = json.dumps(user_update.permissions)

            if not update_data:
                # No updates provided, return existing user
                return existing_user

            # Check for conflicts if username or email is being updated
            if "username" in update_data or "email" in update_data:
                email_to_check = update_data.get("email", existing_user.email)
                username_to_check = update_data.get("username", existing_user.username)

                # Check if another user has this email/username
                existing_by_email = await self.get_user_by_email(email_to_check)
                existing_by_username = await self.get_user_by_username(username_to_check)

                if existing_by_email and existing_by_email.user_id != user_id:
                    raise ValidationError("Email already in use by another user")
                if existing_by_username and existing_by_username.user_id != user_id:
                    raise ValidationError("Username already in use by another user")

            # Update user in database
            success = self.db_manager.update_user(user_id, update_data)

            if not success:
                raise ValidationError("Failed to update user in database")

            # Return updated user
            updated_user = await self.get_user_by_id(user_id)
            if not updated_user:
                raise ValidationError("User not found after update")

            self.logger.info(f"Updated user: {user_id}")

            return updated_user

        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {e}")
            if isinstance(e, ResourceNotFoundError | ValidationError):
                raise
            raise ValidationError(f"Failed to update user: {str(e)}")

    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by deactivating).

        Args:
            user_id: ID of user to delete

        Returns:
            True if user was deleted successfully

        Raises:
            ResourceNotFoundError: If user not found
        """
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise ResourceNotFoundError(f"User with ID {user_id} not found")

            # Soft delete user
            success = self.db_manager.delete_user(user_id)

            if success:
                self.logger.info(f"Deleted user: {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {e}")
            if isinstance(e, ResourceNotFoundError):
                raise
            raise ValidationError(f"Failed to delete user: {str(e)}")

    async def user_exists(self, email: str, username: str | None = None) -> bool:
        """Check if user exists by email or username.

        Args:
            email: Email address to check
            username: Optional username to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            return self.db_manager.user_exists(email.lower(), username)

        except Exception as e:
            self.logger.error(f"Error checking user existence for {email}: {e}")
            return False

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            User model if authentication successful, None otherwise
        """
        try:
            user_data = self.db_manager.authenticate_user(email.lower(), password)

            if user_data:
                return User(**user_data)

            return None

        except Exception as e:
            self.logger.error(f"Error authenticating user {email}: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            True if update successful
        """
        try:
            return self.db_manager.update_last_login(user_id)

        except Exception as e:
            self.logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def update_password(self, user_id: str, new_password: str) -> bool:
        """Update user password.

        Args:
            user_id: User ID
            new_password: New password (plain text)

        Returns:
            True if update successful

        Raises:
            ResourceNotFoundError: If user not found
        """
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise ResourceNotFoundError(f"User with ID {user_id} not found")

            success = self.db_manager.update_user_password(user_id, new_password)

            if success:
                self.logger.info(f"Updated password for user: {user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error updating password for user {user_id}: {e}")
            if isinstance(e, ResourceNotFoundError):
                raise
            raise ValidationError(f"Failed to update password: {str(e)}")
