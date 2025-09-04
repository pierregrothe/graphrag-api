"""
Unit tests for enhanced JWT authentication system.

Tests the JWT token management with refresh token rotation,
blacklisting, and security logging integration.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.graphrag_api_service.auth.jwt_auth import (
    JWTConfig,
    JWTManager,
    RefreshTokenData,
    TokenData,
    TokenResponse,
)
from src.graphrag_api_service.exceptions import AuthenticationError


class TestEnhancedJWTManager:
    """Test enhanced JWT manager functionality."""

    @pytest.fixture
    def jwt_config(self):
        """JWT configuration for testing."""
        return JWTConfig(
            secret_key="test_secret_key_with_sufficient_length_for_security",
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
            issuer="test_issuer",
            audience="test_audience",
        )

    @pytest.fixture
    def jwt_manager(self, jwt_config):
        """JWT manager instance for testing."""
        return JWTManager(jwt_config)

    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing."""
        return TokenData(
            user_id="user_123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:workspaces"],
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

    def test_create_access_token(self, jwt_manager, sample_token_data):
        """Test access token creation."""
        token = jwt_manager.create_access_token(sample_token_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = jwt_manager.verify_token(token)
        assert payload["sub"] == "user_123"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, jwt_manager):
        """Test refresh token creation with tracking."""
        device_info = "Mozilla/5.0 Test Browser"
        refresh_token = jwt_manager.create_refresh_token("user_123", device_info)

        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

        # Verify token can be decoded
        payload = jwt_manager.verify_token(refresh_token)
        assert payload["sub"] == "user_123"
        assert payload["type"] == "refresh"
        assert "jti" in payload  # JWT ID for tracking

        # Verify refresh token data is stored
        token_id = payload["jti"]
        assert token_id in jwt_manager._refresh_tokens

        refresh_data = jwt_manager._refresh_tokens[token_id]
        assert refresh_data.user_id == "user_123"
        assert refresh_data.device_info == device_info
        assert not refresh_data.is_revoked

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, jwt_manager):
        """Test successful token refresh with rotation."""
        # Create initial refresh token
        refresh_token = jwt_manager.create_refresh_token("user_123")

        # Mock user data retrieval
        with patch.object(jwt_manager, "_get_user_data", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"],
                "permissions": ["read:workspaces"],
            }

            # Refresh token
            token_response = await jwt_manager.refresh_access_token(refresh_token)

            assert isinstance(token_response, TokenResponse)
            assert token_response.access_token
            assert token_response.refresh_token
            assert token_response.token_type == "bearer"
            assert token_response.expires_in > 0

            # Verify old refresh token is revoked
            old_payload = jwt_manager.verify_token(refresh_token)
            old_token_id = old_payload["jti"]
            assert jwt_manager._refresh_tokens[old_token_id].is_revoked

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, jwt_manager):
        """Test token refresh with invalid refresh token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthenticationError) as exc_info:
            await jwt_manager.refresh_access_token(invalid_token)

        assert "Invalid refresh token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_access_token_revoked_token(self, jwt_manager):
        """Test token refresh with revoked refresh token."""
        # Create and immediately revoke refresh token
        refresh_token = jwt_manager.create_refresh_token("user_123")
        await jwt_manager.revoke_refresh_token(refresh_token)

        with pytest.raises(AuthenticationError) as exc_info:
            await jwt_manager.refresh_access_token(refresh_token)

        assert "Refresh token revoked" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, jwt_manager):
        """Test refresh token revocation."""
        refresh_token = jwt_manager.create_refresh_token("user_123")

        # Revoke token
        success = await jwt_manager.revoke_refresh_token(refresh_token)
        assert success

        # Verify token is marked as revoked
        payload = jwt_manager.verify_token(refresh_token)
        token_id = payload["jti"]
        assert jwt_manager._refresh_tokens[token_id].is_revoked

    def test_revoke_access_token(self, jwt_manager, sample_token_data):
        """Test access token blacklisting."""
        access_token = jwt_manager.create_access_token(sample_token_data)

        # Revoke token
        success = jwt_manager.revoke_access_token(access_token)
        assert success

        # Verify token is blacklisted
        assert jwt_manager.is_token_blacklisted(access_token)

    def test_is_token_blacklisted(self, jwt_manager, sample_token_data):
        """Test token blacklist checking."""
        access_token = jwt_manager.create_access_token(sample_token_data)

        # Token should not be blacklisted initially
        assert not jwt_manager.is_token_blacklisted(access_token)

        # Blacklist token
        jwt_manager.revoke_access_token(access_token)

        # Token should now be blacklisted
        assert jwt_manager.is_token_blacklisted(access_token)

    def test_verify_token_with_invalid_token(self, jwt_manager):
        """Test token verification with invalid token."""
        with pytest.raises(HTTPException):  # JWT library will raise HTTPException
            jwt_manager.verify_token("invalid.token.here")

    def test_verify_token_with_expired_token(self, jwt_manager):
        """Test token verification with expired token."""
        from datetime import datetime, timedelta

        import jwt as pyjwt

        # Create an expired token manually by manipulating the JWT payload
        expire = datetime.now(UTC) - timedelta(minutes=1)  # Expired 1 minute ago

        payload = {
            "sub": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"],
            "permissions": ["read:workspaces"],
            "exp": expire,  # This is what JWT library checks
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "iss": jwt_manager.config.issuer,
            "aud": jwt_manager.config.audience,
            "type": "access",
        }

        # Create expired token
        expired_token = pyjwt.encode(
            payload, jwt_manager.config.secret_key, algorithm=jwt_manager.config.algorithm
        )

        # Verification should fail due to expiration
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.verify_token(expired_token)
        assert exc_info.value.status_code == 401

    def test_password_hashing(self, jwt_manager):
        """Test password hashing functionality."""
        password = "test_password_123"

        # Hash password
        hashed = jwt_manager.hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

        # Verify password
        assert jwt_manager.verify_password(password, hashed)
        assert not jwt_manager.verify_password("wrong_password", hashed)

    @pytest.mark.asyncio
    async def test_security_logging_integration(self, jwt_manager):
        """Test security logging integration."""
        with patch("src.graphrag_api_service.auth.jwt_auth.get_security_logger") as mock_logger:
            mock_security_logger = Mock()
            mock_logger.return_value = mock_security_logger

            # Create new JWT manager to get the mocked logger
            jwt_manager_with_mock = JWTManager(jwt_manager.config)

            # Mock user data
            with patch.object(
                jwt_manager_with_mock, "_get_user_data", new_callable=AsyncMock
            ) as mock_get_user:
                mock_get_user.return_value = {
                    "username": "testuser",
                    "email": "test@example.com",
                    "roles": ["user"],
                    "permissions": ["read:workspaces"],
                }

                # Create and refresh token
                refresh_token = jwt_manager_with_mock.create_refresh_token("user_123")
                await jwt_manager_with_mock.refresh_access_token(refresh_token)

                # Verify security logging was called
                mock_security_logger.authentication_attempt.assert_called()
                call_args = mock_security_logger.authentication_attempt.call_args
                assert call_args[1]["success"] is True
                assert call_args[1]["user_id"] == "user_123"
                assert call_args[1]["method"] == "refresh_token"

    def test_token_data_validation(self):
        """Test token data model validation."""
        # Valid token data
        valid_data = TokenData(
            user_id="user_123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:workspaces"],
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

        assert valid_data.user_id == "user_123"
        assert valid_data.username == "testuser"
        assert valid_data.email == "test@example.com"
        assert "user" in valid_data.roles
        assert "read:workspaces" in valid_data.permissions

    def test_refresh_token_data_model(self):
        """Test refresh token data model."""
        token_data = RefreshTokenData(
            token_id="token_123",
            user_id="user_123",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=datetime.now(UTC),
            device_info="Test Device",
        )

        assert token_data.token_id == "token_123"
        assert token_data.user_id == "user_123"
        assert not token_data.is_revoked
        assert token_data.device_info == "Test Device"
        assert token_data.last_used_at is None

    @pytest.mark.asyncio
    async def test_concurrent_token_operations(self, jwt_manager):
        """Test concurrent token operations."""
        import asyncio

        # Create multiple refresh tokens concurrently
        async def create_and_refresh():
            refresh_token = jwt_manager.create_refresh_token("user_123")

            with patch.object(
                jwt_manager, "_get_user_data", new_callable=AsyncMock
            ) as mock_get_user:
                mock_get_user.return_value = {
                    "username": "testuser",
                    "email": "test@example.com",
                    "roles": ["user"],
                    "permissions": ["read:workspaces"],
                }

                return await jwt_manager.refresh_access_token(refresh_token)

        # Run multiple operations concurrently
        tasks = [create_and_refresh() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert len(results) == 5
        for result in results:
            assert isinstance(result, TokenResponse)
            assert result.access_token
            assert result.refresh_token
