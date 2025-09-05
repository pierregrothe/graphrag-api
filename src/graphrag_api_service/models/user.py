# src/graphrag_api_service/models/user.py
# User model for authentication system
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""User model for GraphRAG API Service authentication system."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class User(BaseModel):
    """User model for authentication and authorization.

    This model represents a user in the GraphRAG API Service with all necessary
    fields for authentication, authorization, and user management.
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # Primary key
    user_id: str = Field(description="Unique user identifier (UUID)")

    # Authentication fields
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique username (alphanumeric, underscore, hyphen only)",
    )

    email: EmailStr = Field(..., description="User's email address (unique)")

    password_hash: str = Field(
        ..., description="Bcrypt hashed password", exclude=True  # Never include in serialization
    )

    # User profile fields
    full_name: str | None = Field(None, max_length=100, description="User's full name")

    # Status and permissions
    is_active: bool = Field(default=True, description="Whether the user account is active")

    is_admin: bool = Field(default=False, description="Whether the user has admin privileges")

    roles: list[str] = Field(default_factory=lambda: ["user"], description="User roles for RBAC")

    permissions: list[str] = Field(
        default_factory=lambda: ["read:workspaces"], description="User permissions"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Account creation timestamp"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )

    last_login_at: datetime | None = Field(None, description="Last login timestamp")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")

    def update_last_login(self) -> None:
        """Update the last login timestamp to current time."""
        self.last_login_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def add_role(self, role: str) -> None:
        """Add a role to the user if not already present."""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.now(UTC)

    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.now(UTC)

    def add_permission(self, permission: str) -> None:
        """Add a permission to the user if not already present."""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.now(UTC)

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the user."""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.now(UTC)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or self.is_admin

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.updated_at = datetime.now(UTC)


class UserCreate(BaseModel):
    """Model for creating a new user."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$", description="Unique username"
    )

    email: EmailStr = Field(..., description="User's email address")

    password: str = Field(
        ..., min_length=8, max_length=128, description="Plain text password (will be hashed)"
    )

    full_name: str | None = Field(None, max_length=100, description="User's full name")

    roles: list[str] = Field(default_factory=lambda: ["user"], description="Initial user roles")

    permissions: list[str] = Field(
        default_factory=lambda: ["read:workspaces"], description="Initial user permissions"
    )

    is_admin: bool = Field(
        default=False, description="Whether the user should have admin privileges"
    )


class UserUpdate(BaseModel):
    """Model for updating user information."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Updated username",
    )

    email: EmailStr | None = Field(None, description="Updated email address")

    full_name: str | None = Field(None, max_length=100, description="Updated full name")

    is_active: bool | None = Field(None, description="Updated active status")

    roles: list[str] | None = Field(None, description="Updated user roles")

    permissions: list[str] | None = Field(None, description="Updated user permissions")


class UserResponse(BaseModel):
    """Model for user API responses (excludes sensitive data)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class UserLogin(BaseModel):
    """Model for user login credentials."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(..., description="User's email address")

    password: str = Field(..., min_length=1, description="User's password")


class UserPasswordUpdate(BaseModel):
    """Model for updating user password."""

    current_password: str = Field(..., description="Current password for verification")

    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
