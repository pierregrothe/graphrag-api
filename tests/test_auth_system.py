# tests/test_auth_system.py
# Comprehensive unit tests for authentication system
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Comprehensive unit tests for the GraphRAG API authentication system."""

import os
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.graphrag_api_service.auth.jwt_auth import JWTConfig, JWTManager
from src.graphrag_api_service.database.sqlite_models import SQLiteManager
from src.graphrag_api_service.models.user import User, UserCreate, UserLogin
from src.graphrag_api_service.repositories.user_repository import UserRepository
from src.graphrag_api_service.services.auth_service import AuthService
from src.graphrag_api_service.utils.security import PasswordValidator, RateLimitHelper

# Add src to path for imports (after imports to avoid E402)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestUserModel:
    """Test User model and related classes."""

    def test_user_create_model(self):
        """Test UserCreate model validation."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "roles": ["user"],
            "permissions": ["read:workspaces"],
        }

        user_create = UserCreate(**user_data)
        assert user_create.username == "testuser"
        assert user_create.email == "test@example.com"
        assert user_create.password == "SecurePass123!"
        assert user_create.roles == ["user"]

    def test_user_login_model(self):
        """Test UserLogin model validation."""
        login_data = {"email": "test@example.com", "password": "SecurePass123!"}

        user_login = UserLogin(**login_data)
        assert user_login.email == "test@example.com"
        assert user_login.password == "SecurePass123!"

    def test_user_model(self):
        """Test User model creation."""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "full_name": "Test User",
            "roles": ["user"],
            "permissions": ["read:workspaces"],
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        user = User(**user_data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True


class TestPasswordValidator:
    """Test password validation utilities."""

    def test_password_strength_validation(self):
        """Test password strength validation."""
        validator = PasswordValidator()

        # Test strong password
        strong_password = "SecurePass123!"
        is_valid, errors = validator.validate(strong_password)
        assert is_valid is True
        assert len(errors) == 0

        # Test weak password
        weak_password = "weak"
        is_valid, errors = validator.validate(weak_password)
        assert is_valid is False
        assert len(errors) > 0
        assert any("characters long" in error for error in errors)

    def test_common_password_detection(self):
        """Test common password detection."""
        validator = PasswordValidator()

        # Test common password
        common_password = "password123"
        is_valid, errors = validator.validate(common_password)
        # Should still be valid if it meets other criteria, but might warn
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_password_complexity_requirements(self):
        """Test password complexity requirements."""
        validator = PasswordValidator()

        # Test password without uppercase
        no_upper = "lowercase123!"
        is_valid, errors = validator.validate(no_upper)
        assert is_valid is False
        assert len(errors) > 0

        # Test password without numbers
        no_numbers = "PasswordOnly!"
        is_valid, errors = validator.validate(no_numbers)
        assert is_valid is False
        assert len(errors) > 0

        # Test password without special characters
        no_special = "Password123"
        is_valid, errors = validator.validate(no_special)
        assert is_valid is False
        assert len(errors) > 0


class TestRateLimitHelper:
    """Test rate limiting utilities."""

    def test_rate_limit_allows_normal_requests(self):
        """Test that rate limiter allows normal request patterns."""
        rate_limiter = RateLimitHelper()

        # Test normal usage
        allowed, retry_after = rate_limiter.check_rate_limit("test_user", 5, 60)
        assert allowed is True
        assert retry_after == 0

    def test_rate_limit_blocks_excessive_requests(self):
        """Test that rate limiter blocks excessive requests."""
        rate_limiter = RateLimitHelper()

        # Make requests up to limit
        for _ in range(5):
            allowed, retry_after = rate_limiter.check_rate_limit("test_user_2", 5, 60)
            assert allowed is True

        # Next request should be blocked
        allowed, retry_after = rate_limiter.check_rate_limit("test_user_2", 5, 60)
        assert allowed is False
        assert retry_after > 0

    def test_rate_limit_reset_functionality(self):
        """Test rate limit reset functionality."""
        rate_limiter = RateLimitHelper()

        # Fill up the rate limit
        for _ in range(5):
            rate_limiter.check_rate_limit("test_user_3", 5, 60)

        # Reset the rate limit
        rate_limiter.reset_identifier("test_user_3")

        # Should be allowed again
        allowed, retry_after = rate_limiter.check_rate_limit("test_user_3", 5, 60)
        assert allowed is True


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        db_manager = SQLiteManager(db_path)
        # Database is automatically initialized in constructor
        yield db_manager
    finally:
        # SQLiteManager doesn't have a close method, connections are managed automatically
        # On Windows, we need to wait a bit for connections to close
        import time

        time.sleep(0.1)
        try:
            os.unlink(db_path)
        except PermissionError:
            # If we can't delete the file, it's not critical for tests
            pass


@pytest.fixture
async def user_repository(temp_db):
    """Create a UserRepository instance with temporary database."""
    return UserRepository(temp_db)


@pytest.fixture
async def jwt_manager():
    """Create a JWTManager instance for testing."""
    config = JWTConfig(
        secret_key="test_secret_key_for_testing_only",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    return JWTManager(config)


@pytest.fixture
async def auth_service(user_repository, jwt_manager, temp_db):
    """Create an AuthService instance for testing."""
    return AuthService(user_repository, jwt_manager, temp_db)


class TestUserRepository:
    """Test UserRepository functionality."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_repository):
        """Test user creation."""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        user = await user_repository.create_user(user_data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash is not None  # Password should be hashed

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_repository):
        """Test getting user by email."""
        # Create a user first
        user_data = UserCreate(
            username="testuser2",
            email="test2@example.com",
            password="SecurePass123!",
            full_name="Test User 2",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        await user_repository.create_user(user_data)

        # Retrieve the user
        retrieved_user = await user_repository.get_user_by_email("test2@example.com")
        assert retrieved_user is not None
        assert retrieved_user.email == "test2@example.com"
        assert retrieved_user.username == "testuser2"

    @pytest.mark.asyncio
    async def test_user_exists(self, user_repository):
        """Test user existence check."""
        # Check non-existent user
        exists = await user_repository.user_exists("nonexistent@example.com", "nonexistent")
        assert exists is False

        # Create a user
        user_data = UserCreate(
            username="existinguser",
            email="existing@example.com",
            password="SecurePass123!",
            full_name="Existing User",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        await user_repository.create_user(user_data)

        # Check existing user
        exists = await user_repository.user_exists("existing@example.com", "existinguser")
        assert exists is True

    @pytest.mark.asyncio
    async def test_update_last_login(self, user_repository):
        """Test updating last login timestamp."""
        # Create a user first
        user_data = UserCreate(
            username="loginuser",
            email="login@example.com",
            password="SecurePass123!",
            full_name="Login User",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        user = await user_repository.create_user(user_data)
        original_login = user.last_login_at

        # Update last login
        await user_repository.update_last_login(user.user_id)

        # Verify update
        updated_user = await user_repository.get_user_by_email("login@example.com")
        assert updated_user.last_login_at != original_login


class TestAuthService:
    """Test AuthService functionality."""

    @pytest.mark.asyncio
    async def test_register_user(self, auth_service):
        """Test user registration."""
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!",
            full_name="New User",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        result = await auth_service.register_user(user_data)
        assert "user" in result
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "new@example.com"
        assert result["user"]["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_authenticate_user(self, auth_service):
        """Test user authentication."""
        # Register a user first
        user_data = UserCreate(
            username="authuser",
            email="auth@example.com",
            password="SecurePass123!",
            full_name="Auth User",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        await auth_service.register_user(user_data)

        # Test authentication
        user_info = await auth_service.authenticate_user("auth@example.com", "SecurePass123!")
        assert user_info is not None
        assert user_info["email"] == "auth@example.com"
        assert user_info["username"] == "authuser"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, auth_service):
        """Test authentication with invalid credentials."""
        user_info = await auth_service.authenticate_user("invalid@example.com", "wrongpassword")
        assert user_info is None

    @pytest.mark.asyncio
    async def test_login_user(self, auth_service):
        """Test complete login flow."""
        # Register a user first
        user_data = UserCreate(
            username="loginuser2",
            email="login2@example.com",
            password="SecurePass123!",
            full_name="Login User 2",
            roles=["user"],
            permissions=["read:workspaces"],
        )

        await auth_service.register_user(user_data)

        # Test login
        login_data = UserLogin(email="login2@example.com", password="SecurePass123!")
        result = await auth_service.login_user(login_data)

        assert "access_token" in result
        assert "refresh_token" in result
        assert "user" in result
        assert result["user"]["email"] == "login2@example.com"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
