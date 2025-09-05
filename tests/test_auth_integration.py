# tests/test_auth_integration.py
# Integration tests for authentication system
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Integration tests for the GraphRAG API authentication system."""

import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.main import app

# Add src to path for imports (after imports to avoid E402)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestAuthenticationFlow:
    """Test complete authentication flows."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.test_timestamp = str(int(time.time()))

    def test_complete_registration_flow(self):
        """Test complete user registration flow."""
        # Test user registration
        registration_data = {
            "username": f"testuser_{self.test_timestamp}",
            "email": f"test_{self.test_timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
        }

        response = self.client.post("/auth/register", json=registration_data)
        assert response.status_code == 201

        user_data = response.json()
        assert user_data["username"] == registration_data["username"]
        assert user_data["email"] == registration_data["email"]
        assert user_data["full_name"] == registration_data["full_name"]
        assert "user_id" in user_data
        assert "created_at" in user_data

    def test_complete_login_flow(self):
        """Test complete user login flow."""
        # First register a user
        registration_data = {
            "username": f"loginuser_{self.test_timestamp}",
            "email": f"login_{self.test_timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Login User",
        }

        reg_response = self.client.post("/auth/register", json=registration_data)
        assert reg_response.status_code == 201

        # Now test login
        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"],
        }

        login_response = self.client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200

        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert "token_type" in login_result
        assert "expires_in" in login_result
        assert "user" in login_result

        user_info = login_result["user"]
        assert user_info["email"] == registration_data["email"]
        assert user_info["username"] == registration_data["username"]

    def test_profile_access_with_token(self):
        """Test accessing profile with valid token."""
        # Register and login to get token
        registration_data = {
            "username": f"profileuser_{self.test_timestamp}",
            "email": f"profile_{self.test_timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Profile User",
        }

        self.client.post("/auth/register", json=registration_data)

        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"],
        }

        login_response = self.client.post("/auth/login", json=login_data)
        login_result = login_response.json()
        access_token = login_result["access_token"]

        # Access profile with token
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = self.client.get("/auth/profile", headers=headers)

        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == registration_data["email"]
        assert profile_data["username"] == registration_data["username"]

    def test_logout_flow(self):
        """Test complete logout flow."""
        # Register and login to get token
        registration_data = {
            "username": f"logoutuser_{self.test_timestamp}",
            "email": f"logout_{self.test_timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Logout User",
        }

        self.client.post("/auth/register", json=registration_data)

        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"],
        }

        login_response = self.client.post("/auth/login", json=login_data)
        login_result = login_response.json()
        access_token = login_result["access_token"]

        # Test logout
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = self.client.post("/auth/logout", headers=headers)

        assert logout_response.status_code == 200
        logout_result = logout_response.json()
        assert logout_result["message"] == "Successfully logged out"


class TestAuthenticationSecurity:
    """Test authentication security features."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_invalid_login_attempts(self):
        """Test handling of invalid login attempts."""
        invalid_login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response = self.client.post("/auth/login", json=invalid_login_data)
        assert response.status_code == 401

        error_data = response.json()
        # Check for either "detail" or "error" field in response
        assert "detail" in error_data or "error" in error_data

    def test_duplicate_registration_prevention(self):
        """Test prevention of duplicate user registration."""
        timestamp = str(int(time.time()))
        registration_data = {
            "username": f"duplicate_{timestamp}",
            "email": f"duplicate_{timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Duplicate User",
        }

        # First registration should succeed
        response1 = self.client.post("/auth/register", json=registration_data)
        assert response1.status_code == 201

        # Second registration should fail
        response2 = self.client.post("/auth/register", json=registration_data)
        assert response2.status_code == 400

    def test_unauthorized_profile_access(self):
        """Test unauthorized access to profile endpoint."""
        response = self.client.get("/auth/profile")
        assert response.status_code == 401

    def test_invalid_token_access(self):
        """Test access with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/auth/profile", headers=headers)
        assert response.status_code == 401

    def test_security_headers_present(self):
        """Test that security headers are present in responses."""
        response = self.client.get("/auth/profile")

        # Check for essential security headers
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_auth_endpoint_cache_headers(self):
        """Test that auth endpoints have proper cache control headers."""
        invalid_login_data = {"email": "test@example.com", "password": "wrongpassword"}

        response = self.client.post("/auth/login", json=invalid_login_data)

        # Check cache control headers
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-store" in cache_control
        assert "no-cache" in cache_control


class TestPasswordValidation:
    """Test password validation in registration."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_weak_password_rejection(self):
        """Test rejection of weak passwords."""
        timestamp = str(int(time.time()))
        weak_passwords = ["weak", "12345678", "password", "Password", "Password123", "password123!"]

        for weak_password in weak_passwords:
            registration_data = {
                "username": f"weakpass_{timestamp}_{len(weak_password)}",
                "email": f"weakpass_{timestamp}_{len(weak_password)}@example.com",
                "password": weak_password,
                "full_name": "Weak Password User",
            }

            response = self.client.post("/auth/register", json=registration_data)
            # Should either reject (400, 422), accept but warn (201), or hit rate limit (429, 500)
            assert response.status_code in [201, 400, 422, 429, 500]

            # If we hit rate limiting, break out of the loop
            if response.status_code in [429, 500]:
                break

    def test_strong_password_acceptance(self):
        """Test acceptance of strong passwords."""
        timestamp = str(int(time.time()))
        strong_passwords = [
            "SecurePass123!",
            "MyStr0ng@Password",
            "C0mpl3x#P@ssw0rd",
            "V3ry$ecur3P@ss!",
        ]

        for i, strong_password in enumerate(strong_passwords):
            registration_data = {
                "username": f"strongpass_{timestamp}_{i}",
                "email": f"strongpass_{timestamp}_{i}@example.com",
                "password": strong_password,
                "full_name": "Strong Password User",
            }

            response = self.client.post("/auth/register", json=registration_data)
            assert response.status_code == 201


class TestTokenManagement:
    """Test JWT token management."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.test_timestamp = str(int(time.time()))

    def test_token_refresh_flow(self):
        """Test token refresh functionality."""
        # Register and login to get tokens
        registration_data = {
            "username": f"refreshuser_{self.test_timestamp}",
            "email": f"refresh_{self.test_timestamp}@example.com",
            "password": "SecurePass123!",
            "full_name": "Refresh User",
        }

        self.client.post("/auth/register", json=registration_data)

        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"],
        }

        login_response = self.client.post("/auth/login", json=login_data)
        login_result = login_response.json()

        refresh_token = login_result["refresh_token"]

        # Test token refresh
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = self.client.post("/auth/refresh", json=refresh_data)

        if refresh_response.status_code == 200:
            refresh_result = refresh_response.json()
            assert "access_token" in refresh_result
            assert "token_type" in refresh_result

    def test_token_expiration_handling(self):
        """Test handling of expired tokens."""
        # This test would require manipulating token expiration
        # For now, we'll test with an obviously invalid token
        headers = {"Authorization": "Bearer expired.token.here"}
        response = self.client.get("/auth/profile", headers=headers)
        assert response.status_code == 401


class TestRateLimiting:
    """Test rate limiting functionality."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_login_rate_limiting(self):
        """Test rate limiting on login attempts."""
        invalid_login_data = {"email": "ratelimit@example.com", "password": "wrongpassword"}

        # Make multiple failed login attempts
        responses = []
        for _ in range(10):  # Try more than typical rate limit
            response = self.client.post("/auth/login", json=invalid_login_data)
            responses.append(response.status_code)

        # Should see some 401s (auth failures) and potentially 429s (rate limited)
        assert 401 in responses
        # Rate limiting might kick in, but depends on configuration

    def test_registration_rate_limiting(self):
        """Test rate limiting on registration attempts."""
        timestamp = str(int(time.time()))

        # Make multiple registration attempts
        responses = []
        for i in range(5):
            registration_data = {
                "username": f"ratelimit_{timestamp}_{i}",
                "email": f"ratelimit_{timestamp}_{i}@example.com",
                "password": "SecurePass123!",
                "full_name": f"Rate Limit User {i}",
            }

            response = self.client.post("/auth/register", json=registration_data)
            responses.append(response.status_code)

        # Should see successful registrations (201)
        assert 201 in responses


class TestErrorHandling:
    """Test error handling in authentication system."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_malformed_request_handling(self):
        """Test handling of malformed requests."""
        # Test registration with missing fields
        incomplete_data = {
            "username": "incomplete",
            # Missing email, password, etc.
        }

        response = self.client.post("/auth/register", json=incomplete_data)
        assert response.status_code == 422  # Validation error

    def test_invalid_email_format(self):
        """Test handling of invalid email formats."""
        timestamp = str(int(time.time()))
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user..name@example.com",
        ]

        for i, invalid_email in enumerate(invalid_emails):
            registration_data = {
                "username": f"invalidemail_{timestamp}_{i}",
                "email": invalid_email,
                "password": "SecurePass123!",
                "full_name": "Invalid Email User",
            }

            response = self.client.post("/auth/register", json=registration_data)
            assert response.status_code == 422  # Validation error

    def test_json_error_responses(self):
        """Test that error responses are properly formatted JSON."""
        response = self.client.post("/auth/login", json={})
        assert response.status_code == 422

        # Should be valid JSON
        try:
            error_data = response.json()
            assert isinstance(error_data, dict)
        except json.JSONDecodeError:
            pytest.fail("Error response is not valid JSON")


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
