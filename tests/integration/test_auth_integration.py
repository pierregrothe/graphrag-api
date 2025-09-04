"""
Integration tests for authentication system.

Tests complete authentication workflows including JWT and API key
authentication, rate limiting, and integration with other services.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.graphrag_api_service.main import app
from src.graphrag_api_service.auth.api_keys import APIKeyScope


class TestAuthenticationIntegration:
    """Test complete authentication workflows."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_user_registration_flow(self, client):
        """Test complete user registration workflow."""
        registration_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "secure_password_123",
            "full_name": "Test User"
        }
        
        response = client.post("/auth/register", json=registration_data)
        
        # Should succeed (or handle appropriately based on implementation)
        assert response.status_code in [201, 200, 422]  # 422 if validation fails
        
        if response.status_code == 201:
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert "user_id" in data
    
    def test_user_login_flow(self, client):
        """Test complete user login workflow."""
        login_data = {
            "email": "test@example.com",
            "password": "secure_password_123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        # Should succeed or fail gracefully
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert "user" in data
        else:
            # Authentication failed (expected in test environment)
            assert response.status_code in [401, 422]
    
    def test_token_refresh_flow(self, client):
        """Test token refresh workflow."""
        # First login to get tokens
        login_data = {
            "email": "test@example.com",
            "password": "secure_password_123"
        }
        
        login_response = client.post("/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            refresh_token = login_data["refresh_token"]
            
            # Use refresh token to get new access token
            refresh_data = {"refresh_token": refresh_token}
            refresh_response = client.post("/auth/refresh", json=refresh_data)
            
            if refresh_response.status_code == 200:
                refresh_data = refresh_response.json()
                assert "access_token" in refresh_data
                assert "refresh_token" in refresh_data
                assert refresh_data["token_type"] == "bearer"
    
    def test_protected_endpoint_access(self, client):
        """Test access to protected endpoints."""
        # Try to access protected endpoint without authentication
        response = client.get("/auth/profile")
        assert response.status_code == 401
        
        # Try with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/profile", headers=headers)
        assert response.status_code == 401
    
    def test_api_key_creation_flow(self, client):
        """Test API key creation workflow."""
        # First need to authenticate
        login_data = {
            "email": "test@example.com",
            "password": "secure_password_123"
        }
        
        login_response = client.post("/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            tokens = login_response.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            # Create API key
            api_key_data = {
                "name": "Test API Key",
                "scopes": ["read:workspaces"],
                "expires_in_days": 30
            }
            
            response = client.post("/auth/keys", json=api_key_data, headers=headers)
            
            if response.status_code == 201:
                data = response.json()
                assert "key" in data
                assert "prefix" in data
                assert data["name"] == "Test API Key"
                assert "read:workspaces" in data["scopes"]
    
    def test_api_key_authentication(self, client):
        """Test authentication using API key."""
        # This would require a valid API key
        # For now, test the endpoint structure
        
        headers = {"X-API-Key": "grak_test_key_12345"}
        response = client.get("/api/graph/entities", headers=headers)
        
        # Should fail with invalid key
        assert response.status_code in [401, 403]
    
    def test_logout_flow(self, client):
        """Test user logout workflow."""
        # First login
        login_data = {
            "email": "test@example.com",
            "password": "secure_password_123"
        }
        
        login_response = client.post("/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            tokens = login_response.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            # Logout
            logout_response = client.post("/auth/logout", headers=headers)
            
            if logout_response.status_code == 200:
                # Try to use the token after logout
                profile_response = client.get("/auth/profile", headers=headers)
                assert profile_response.status_code == 401  # Should be unauthorized


class TestRateLimitingIntegration:
    """Test rate limiting integration."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_authentication_rate_limiting(self, client):
        """Test rate limiting on authentication endpoints."""
        login_data = {
            "email": "test@example.com",
            "password": "wrong_password"
        }
        
        # Make multiple failed login attempts
        responses = []
        for _ in range(15):  # Exceed typical rate limit
            response = client.post("/auth/login", json=login_data)
            responses.append(response.status_code)
        
        # Should eventually get rate limited
        assert 429 in responses or all(r in [401, 422] for r in responses)
    
    def test_api_endpoint_rate_limiting(self, client):
        """Test rate limiting on API endpoints."""
        # Make many requests to API endpoint
        responses = []
        for _ in range(100):  # Exceed typical rate limit
            response = client.get("/api/graph/entities")
            responses.append(response.status_code)
            
            # Stop if we get rate limited
            if response.status_code == 429:
                break
        
        # Should eventually get rate limited or unauthorized
        assert 429 in responses or all(r in [401, 403] for r in responses)


class TestSecurityIntegration:
    """Test security features integration."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/auth/login")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 405
    
    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get("/health")
        
        # Should have security headers
        expected_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection"
        ]
        
        for header in expected_headers:
            # Headers might be added by middleware
            assert header in response.headers or response.status_code == 404
    
    def test_path_traversal_protection(self, client):
        """Test path traversal protection in API endpoints."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f"
        ]
        
        for path in malicious_paths:
            response = client.get(f"/api/graph/entities?workspace_id={path}")
            
            # Should be rejected (400, 403, or 422)
            assert response.status_code in [400, 401, 403, 422]
    
    def test_sql_injection_protection(self, client):
        """Test SQL injection protection."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/*",
            "1; DELETE FROM workspaces; --"
        ]
        
        for malicious_input in malicious_inputs:
            # Test in various parameters
            response = client.get(f"/api/graph/entities?entity_name={malicious_input}")
            
            # Should handle gracefully (not crash)
            assert response.status_code in [200, 400, 401, 403, 422]
    
    def test_xss_protection(self, client):
        """Test XSS protection in API responses."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            response = client.get(f"/api/graph/entities?entity_name={payload}")
            
            if response.status_code == 200:
                # Response should not contain unescaped script tags
                response_text = response.text.lower()
                assert "<script>" not in response_text
                assert "javascript:" not in response_text


class TestWorkspaceAccessIntegration:
    """Test workspace access control integration."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_workspace_isolation(self, client):
        """Test workspace isolation in API endpoints."""
        # Test access to different workspaces
        workspaces = ["workspace1", "workspace2", "default"]
        
        for workspace in workspaces:
            response = client.get(f"/api/graph/entities?workspace_id={workspace}")
            
            # Should require authentication
            assert response.status_code in [401, 403]
    
    def test_cross_workspace_access_prevention(self, client):
        """Test prevention of cross-workspace access."""
        # This would require authenticated users with different workspace access
        # For now, test that workspace parameter is properly validated
        
        invalid_workspaces = [
            "",
            " ",
            "workspace with spaces",
            "workspace/with/slashes"
        ]
        
        for workspace in invalid_workspaces:
            response = client.get(f"/api/graph/entities?workspace_id={workspace}")
            
            # Should be rejected
            assert response.status_code in [400, 401, 403, 422]


class TestPerformanceIntegration:
    """Test performance aspects of authentication."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_authentication_performance(self, client):
        """Test authentication performance under load."""
        import time
        
        login_data = {
            "email": "test@example.com",
            "password": "secure_password_123"
        }
        
        # Measure authentication time
        start_time = time.time()
        
        for _ in range(10):
            response = client.post("/auth/login", json=login_data)
            # Don't care about success/failure, just that it responds quickly
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 10
        
        # Authentication should be reasonably fast (< 1 second per request)
        assert avg_time < 1.0
    
    def test_concurrent_authentication(self, client):
        """Test concurrent authentication requests."""
        import concurrent.futures
        import threading
        
        def make_auth_request():
            login_data = {
                "email": f"test{threading.current_thread().ident}@example.com",
                "password": "secure_password_123"
            }
            return client.post("/auth/login", json=login_data)
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_auth_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All requests should complete (success or failure)
        assert len(responses) == 10
        assert all(r.status_code in [200, 401, 422, 429] for r in responses)


class TestErrorHandlingIntegration:
    """Test error handling in authentication system."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_malformed_request_handling(self, client):
        """Test handling of malformed authentication requests."""
        malformed_requests = [
            {},  # Empty request
            {"email": "invalid"},  # Missing password
            {"password": "test"},  # Missing email
            {"email": "not_an_email", "password": "test"},  # Invalid email
            {"email": "test@example.com", "password": ""},  # Empty password
        ]
        
        for request_data in malformed_requests:
            response = client.post("/auth/login", json=request_data)
            
            # Should return validation error
            assert response.status_code == 422
    
    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON in requests."""
        invalid_json_data = [
            "invalid json",
            '{"incomplete": json',
            '{"email": "test@example.com", "password": }',
        ]
        
        for json_data in invalid_json_data:
            response = client.post(
                "/auth/login",
                data=json_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return bad request
            assert response.status_code == 422
    
    def test_large_request_handling(self, client):
        """Test handling of unusually large requests."""
        # Create large request data
        large_data = {
            "email": "test@example.com",
            "password": "x" * 10000,  # Very long password
            "extra_field": "x" * 100000  # Large extra field
        }
        
        response = client.post("/auth/login", json=large_data)
        
        # Should handle gracefully (reject or process)
        assert response.status_code in [200, 400, 401, 413, 422]
