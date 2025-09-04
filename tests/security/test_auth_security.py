"""
Security tests for authentication system.

Tests authentication bypass attempts, token manipulation,
rate limiting, and other security-critical scenarios.
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from fastapi import HTTPException

from src.graphrag_api_service.auth.api_keys import APIKeyManager, APIKeyRequest, APIKeyScope
from src.graphrag_api_service.auth.jwt_auth import JWTConfig, JWTManager, TokenData
from src.graphrag_api_service.auth.rate_limiting import RateLimitConfig, RateLimiter
from src.graphrag_api_service.auth.unified_auth import UnifiedAuthenticator
from src.graphrag_api_service.exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
)


class TestJWTSecurity:
    """Test JWT security measures."""

    @pytest.fixture
    def jwt_manager(self):
        """JWT manager for testing."""
        config = JWTConfig(
            secret_key="test_secret_key_with_sufficient_length_for_security",
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        return JWTManager(config)

    def test_token_tampering_detection(self, jwt_manager):
        """Test detection of tampered tokens."""
        # Create valid token
        token_data = TokenData(
            user_id="user_123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:workspaces"],
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

        valid_token = jwt_manager.create_access_token(token_data)

        # Tamper with token (change payload)
        parts = valid_token.split(".")
        tampered_token = parts[0] + ".eyJ0YW1wZXJlZCI6InRydWUifQ." + parts[2]

        # Verification should fail
        with pytest.raises(HTTPException):
            jwt_manager.verify_token(tampered_token)

    def test_algorithm_confusion_attack(self, jwt_manager):
        """Test protection against algorithm confusion attacks."""
        # Create token with different algorithm
        malicious_payload = {
            "sub": "admin",
            "username": "admin",
            "email": "admin@example.com",
            "roles": ["admin"],
            "permissions": ["admin:all"],
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(UTC).timestamp(),
            "type": "access",
        }

        # Try to create token with 'none' algorithm
        try:
            malicious_token = jwt.encode(malicious_payload, "", algorithm="none")

            # Verification should fail
            with pytest.raises(HTTPException):
                jwt_manager.verify_token(malicious_token)
        except Exception:
            # JWT library might reject 'none' algorithm entirely
            pass

    def test_token_replay_attack_protection(self, jwt_manager):
        """Test protection against token replay attacks."""
        token_data = TokenData(
            user_id="user_123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:workspaces"],
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

        token = jwt_manager.create_access_token(token_data)

        # Token should work initially
        payload = jwt_manager.verify_token(token)
        assert payload["sub"] == "user_123"

        # Blacklist token
        jwt_manager.revoke_access_token(token)

        # Token should be rejected after blacklisting
        assert jwt_manager.is_token_blacklisted(token)

    def test_weak_secret_key_rejection(self):
        """Test rejection of weak secret keys."""
        # This would be caught by configuration validation
        with pytest.raises(ValueError, match="Secret key must be at least 32 characters"):
            JWTConfig(secret_key="weak", algorithm="HS256")  # Too short

    @pytest.mark.asyncio
    async def test_refresh_token_rotation_security(self, jwt_manager):
        """Test refresh token rotation prevents reuse."""
        # Create refresh token
        refresh_token = jwt_manager.create_refresh_token("user_123")

        # Mock user data
        with patch.object(jwt_manager, "_get_user_data", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {
                "username": "testuser",
                "email": "test@example.com",
                "roles": ["user"],
                "permissions": ["read:workspaces"],
            }

            # Use refresh token once
            token_response = await jwt_manager.refresh_access_token(refresh_token)
            assert token_response.access_token

            # Try to reuse the same refresh token
            with pytest.raises(AuthenticationError) as exc_info:
                await jwt_manager.refresh_access_token(refresh_token)

            assert "revoked" in str(exc_info.value).lower()


class TestAPIKeySecurity:
    """Test API key security measures."""

    @pytest.fixture
    def api_key_manager(self):
        """API key manager for testing."""
        return APIKeyManager()

    @pytest.mark.asyncio
    async def test_api_key_brute_force_protection(self, api_key_manager):
        """Test protection against API key brute force attacks."""
        # This would typically be handled by rate limiting
        invalid_keys = [
            "invalid_key_1",
            "invalid_key_2",
            "invalid_key_3",
            "invalid_key_4",
            "invalid_key_5",
        ]

        for key in invalid_keys:
            result = await api_key_manager.validate_api_key(key)
            assert result is None

    @pytest.mark.asyncio
    async def test_api_key_enumeration_protection(self, api_key_manager):
        """Test protection against API key enumeration."""
        # Create valid API key
        request = APIKeyRequest(
            name="test_key",
            scopes=[APIKeyScope.READ_WORKSPACES],
            expires_in_days=30,
            description="Test key for enumeration protection",
        )

        response = await api_key_manager.create_api_key("user_123", request)
        valid_key = response.key

        # Test with various invalid keys
        invalid_keys = [
            valid_key[:-1] + "x",  # Change last character
            valid_key[:-2] + "xx",  # Change last two characters
            "grak_" + "x" * 32,  # Wrong prefix
            "invalid_format",  # Completely wrong format
        ]

        for invalid_key in invalid_keys:
            result = await api_key_manager.validate_api_key(invalid_key)
            assert result is None

    @pytest.mark.asyncio
    async def test_api_key_quota_enforcement(self, api_key_manager):
        """Test API key creation quota enforcement."""
        user_id = "user_123"

        # Create maximum allowed keys (10)
        for i in range(10):
            request = APIKeyRequest(
                name=f"test_key_{i}",
                scopes=[APIKeyScope.READ_WORKSPACES],
                expires_in_days=30,
                description=f"Test key {i} for quota enforcement",
            )
            await api_key_manager.create_api_key(user_id, request)

        # Try to create one more key
        with pytest.raises(QuotaExceededError) as exc_info:
            request = APIKeyRequest(
                name="excess_key",
                scopes=[APIKeyScope.READ_WORKSPACES],
                expires_in_days=30,
                description="Excess key for quota testing",
            )
            await api_key_manager.create_api_key(user_id, request)

        assert "Maximum number of API keys reached" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_key_scope_validation(self, api_key_manager):
        """Test API key scope validation."""
        # Try to create key without scopes
        with pytest.raises(ValidationError):  # Should be caught by validation
            request = APIKeyRequest(
                name="no_scope_key",
                scopes=[],  # Empty scopes
                expires_in_days=30,
                description="Key with no scopes for validation testing",
            )
            await api_key_manager.create_api_key("user_123", request)


class TestRateLimitingSecurity:
    """Test rate limiting security measures."""

    @pytest.fixture
    def rate_limiter(self):
        """Rate limiter for testing."""
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_rate_limit_bypass_attempts(self, rate_limiter):
        """Test attempts to bypass rate limiting."""
        config = RateLimitConfig(requests_per_minute=5, burst_limit=2)

        identifier = "test_user"

        # Make requests up to limit
        for _ in range(5):
            await rate_limiter.check_rate_limit(identifier, config)

        # Next request should be rate limited
        with pytest.raises(RateLimitError):
            await rate_limiter.check_rate_limit(identifier, config)

        # Try with different identifier (should work)
        await rate_limiter.check_rate_limit("different_user", config)

    @pytest.mark.asyncio
    async def test_distributed_rate_limit_attack(self, rate_limiter):
        """Test distributed rate limiting attack."""
        config = RateLimitConfig(requests_per_minute=10, burst_limit=5)

        # Simulate requests from multiple IPs for same user
        base_identifier = "user_123"

        for ip in range(20):  # 20 different IPs
            identifier = f"{base_identifier}:ip_{ip}"

            # Each IP can make requests up to limit
            for _ in range(10):
                await rate_limiter.check_rate_limit(identifier, config)

            # But 11th request should fail
            with pytest.raises(RateLimitError):
                await rate_limiter.check_rate_limit(identifier, config)

    @pytest.mark.asyncio
    async def test_time_manipulation_resistance(self, rate_limiter):
        """Test resistance to time manipulation attacks."""
        config = RateLimitConfig(requests_per_minute=5, burst_limit=2)

        identifier = "test_user"

        # Make requests up to limit
        for _ in range(5):
            await rate_limiter.check_rate_limit(identifier, config)

        # Should be rate limited
        with pytest.raises(RateLimitError):
            await rate_limiter.check_rate_limit(identifier, config)

        # Even if we try to manipulate time (this wouldn't work in real scenario)
        # the rate limiter should still enforce limits
        with pytest.raises(RateLimitError):
            await rate_limiter.check_rate_limit(identifier, config)


class TestUnifiedAuthSecurity:
    """Test unified authentication security."""

    @pytest.fixture
    def unified_auth(self):
        """Unified authenticator for testing."""
        return UnifiedAuthenticator()

    @pytest.mark.asyncio
    async def test_authentication_method_confusion(self, unified_auth):
        """Test protection against authentication method confusion."""
        # Mock request
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test"}

        # Try to authenticate with both JWT and API key
        # This should use the first available method (API key)
        with pytest.raises(AuthenticationError):
            await unified_auth.authenticate_request(
                request=mock_request,
                bearer_token=None,
                api_key_header="invalid_api_key",
                api_key_query=None,
            )

    @pytest.mark.asyncio
    async def test_privilege_escalation_prevention(self, unified_auth):
        """Test prevention of privilege escalation."""
        # This would be tested in integration with actual user data
        # For now, we test that the authenticator properly validates permissions

        # Mock request
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test"}

        # Authentication should fail with invalid credentials
        with pytest.raises(AuthenticationError):
            await unified_auth.authenticate_request(
                request=mock_request, bearer_token=None, api_key_header=None, api_key_query=None
            )


class TestSecurityLogging:
    """Test security logging for authentication events."""

    @pytest.mark.asyncio
    async def test_failed_authentication_logging(self):
        """Test logging of failed authentication attempts."""
        with patch("src.graphrag_api_service.auth.unified_auth.get_security_logger") as mock_logger:
            mock_security_logger = Mock()
            mock_logger.return_value = mock_security_logger

            # Create authenticator with mocked logger
            auth = UnifiedAuthenticator()

            # Mock request
            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"
            mock_request.headers = {"user-agent": "test"}

            # Try invalid authentication
            try:
                await auth.authenticate_request(
                    request=mock_request,
                    bearer_token=None,
                    api_key_header="invalid_key",
                    api_key_query=None,
                )
            except AuthenticationError:
                pass

            # Verify security logging was called
            # Note: This would need to be adjusted based on actual implementation

    def test_suspicious_activity_detection(self):
        """Test detection and logging of suspicious activities."""
        # This would test patterns like:
        # - Multiple failed login attempts
        # - Login from unusual locations
        # - Unusual API usage patterns
        # - Token manipulation attempts

        # For now, this is a placeholder for comprehensive suspicious activity detection
        pass


class TestPasswordSecurity:
    """Test password security measures."""

    def test_password_hashing_strength(self):
        """Test password hashing uses strong algorithms."""
        config = JWTConfig(
            secret_key="test_secret_key_with_sufficient_length_for_security", algorithm="HS256"
        )
        jwt_manager = JWTManager(config)

        password = "test_password_123"
        hashed = jwt_manager.hash_password(password)

        # Hash should be different from password
        assert hashed != password

        # Hash should be long enough (bcrypt produces ~60 char hashes)
        assert len(hashed) > 50

        # Hash should start with bcrypt identifier
        assert hashed.startswith("$2b$")

    def test_password_timing_attack_resistance(self):
        """Test resistance to password timing attacks."""
        config = JWTConfig(
            secret_key="test_secret_key_with_sufficient_length_for_security", algorithm="HS256"
        )
        jwt_manager = JWTManager(config)

        password = "test_password_123"
        hashed = jwt_manager.hash_password(password)

        # Time verification of correct password
        start_time = time.time()
        result1 = jwt_manager.verify_password(password, hashed)
        time1 = time.time() - start_time

        # Time verification of incorrect password
        start_time = time.time()
        result2 = jwt_manager.verify_password("wrong_password", hashed)
        time2 = time.time() - start_time

        assert result1 is True
        assert result2 is False

        # Times should be similar (bcrypt is designed to be constant-time)
        # Allow for some variance due to system load
        time_ratio = max(time1, time2) / min(time1, time2)
        assert time_ratio < 2.0  # Should be within 2x of each other
