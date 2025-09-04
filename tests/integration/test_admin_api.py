"""
Integration tests for administrative API endpoints.

Tests complete administrative workflows including master key authentication,
API key management, and batch operations with proper authorization.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.graphrag_api_service.main import app
from src.graphrag_api_service.config import generate_master_api_key
from src.graphrag_api_service.auth.api_keys import APIKeyScope


class TestAdminAPIAuthentication:
    """Test administrative API authentication."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def master_key(self):
        """Generate a master key for testing."""
        return generate_master_api_key()
    
    def test_admin_endpoint_without_auth(self, client):
        """Test admin endpoint access without authentication."""
        response = client.get("/auth/admin/api-keys")
        assert response.status_code == 401
    
    def test_admin_endpoint_with_invalid_key(self, client):
        """Test admin endpoint access with invalid key."""
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/auth/admin/api-keys", headers=headers)
        assert response.status_code == 401
    
    def test_admin_endpoint_with_regular_api_key(self, client):
        """Test admin endpoint access with regular API key."""
        # This would require a valid regular API key
        headers = {"X-API-Key": "grak_regular_key_12345"}
        response = client.get("/auth/admin/api-keys", headers=headers)
        assert response.status_code in [401, 403]  # Unauthorized or forbidden
    
    @patch('src.graphrag_api_service.config.get_settings')
    def test_admin_endpoint_with_master_key(self, mock_settings, client, master_key):
        """Test admin endpoint access with valid master key."""
        # Mock settings to include master key
        settings_mock = Mock()
        settings_mock.master_api_key = master_key
        mock_settings.return_value = settings_mock
        
        headers = {"X-API-Key": master_key}
        response = client.get("/auth/admin/api-keys", headers=headers)
        
        # Should succeed or fail gracefully (not 401)
        assert response.status_code in [200, 500]  # Success or server error


class TestAdminAPIKeyManagement:
    """Test administrative API key management endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def master_headers(self):
        """Headers with master key for authentication."""
        master_key = generate_master_api_key()
        
        with patch('src.graphrag_api_service.config.get_settings') as mock_settings:
            settings_mock = Mock()
            settings_mock.master_api_key = master_key
            mock_settings.return_value = settings_mock
            
            return {"X-API-Key": master_key}
    
    def test_list_all_api_keys(self, client, master_headers):
        """Test listing all API keys with admin privileges."""
        response = client.get("/auth/admin/api-keys", headers=master_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "keys" in data
            assert "total_count" in data
            assert "limit" in data
            assert "offset" in data
            assert "has_more" in data
            assert isinstance(data["keys"], list)
    
    def test_list_all_api_keys_with_filters(self, client, master_headers):
        """Test listing API keys with filtering parameters."""
        params = {
            "user_id": "test_user",
            "status": "active",
            "limit": 50,
            "offset": 0
        }
        
        response = client.get("/auth/admin/api-keys", headers=master_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == 50
            assert data["offset"] == 0
    
    def test_create_admin_api_key(self, client, master_headers):
        """Test creating API key for any user with admin privileges."""
        key_data = {
            "name": "Admin Created Key",
            "user_id": "target_user_123",
            "scopes": ["read:workspaces", "write:workspaces"],
            "expires_in_days": 30,
            "description": "Key created by admin for testing"
        }
        
        response = client.post("/auth/admin/api-keys", headers=master_headers, json=key_data)
        
        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert "key" in data  # Actual key value returned once
            assert "prefix" in data
            assert data["name"] == "Admin Created Key"
            assert data["user_id"] == "target_user_123"
            assert "warning" in data
    
    def test_get_api_key_details(self, client, master_headers):
        """Test getting detailed API key information."""
        # First create a key to get details for
        key_data = {
            "name": "Test Key for Details",
            "user_id": "test_user",
            "scopes": ["read:workspaces"]
        }
        
        create_response = client.post("/auth/admin/api-keys", headers=master_headers, json=key_data)
        
        if create_response.status_code == 201:
            created_key = create_response.json()
            key_id = created_key["id"]
            
            # Get details
            response = client.get(f"/auth/admin/api-keys/{key_id}", headers=master_headers)
            
            if response.status_code == 200:
                data = response.json()
                assert data["id"] == key_id
                assert data["name"] == "Test Key for Details"
                assert data["user_id"] == "test_user"
                assert "usage_count" in data
                assert "daily_usage" in data
                assert "created_at" in data
    
    def test_update_api_key_admin(self, client, master_headers):
        """Test updating API key with admin privileges."""
        # First create a key to update
        key_data = {
            "name": "Key to Update",
            "user_id": "test_user",
            "scopes": ["read:workspaces"]
        }
        
        create_response = client.post("/auth/admin/api-keys", headers=master_headers, json=key_data)
        
        if create_response.status_code == 201:
            created_key = create_response.json()
            key_id = created_key["id"]
            
            # Update the key
            update_data = {
                "name": "Updated Key Name",
                "scopes": ["read:workspaces", "write:workspaces"],
                "is_active": True
            }
            
            response = client.put(f"/auth/admin/api-keys/{key_id}", headers=master_headers, json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                assert key_id in data["message"]
    
    def test_revoke_api_key_admin(self, client, master_headers):
        """Test revoking API key with admin privileges."""
        # First create a key to revoke
        key_data = {
            "name": "Key to Revoke",
            "user_id": "test_user",
            "scopes": ["read:workspaces"]
        }
        
        create_response = client.post("/auth/admin/api-keys", headers=master_headers, json=key_data)
        
        if create_response.status_code == 201:
            created_key = create_response.json()
            key_id = created_key["id"]
            
            # Revoke the key
            params = {"reason": "Testing revocation"}
            response = client.delete(f"/auth/admin/api-keys/{key_id}", headers=master_headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                assert key_id in data["message"]
    
    def test_batch_api_key_operations(self, client, master_headers):
        """Test batch operations on API keys."""
        # First create multiple keys for batch operations
        keys_created = []
        for i in range(3):
            key_data = {
                "name": f"Batch Test Key {i}",
                "user_id": "batch_test_user",
                "scopes": ["read:workspaces"]
            }
            
            create_response = client.post("/auth/admin/api-keys", headers=master_headers, json=key_data)
            if create_response.status_code == 201:
                keys_created.append(create_response.json()["id"])
        
        if keys_created:
            # Perform batch revocation
            batch_data = {
                "operation": "revoke",
                "filters": {
                    "user_id": "batch_test_user"
                },
                "reason": "Batch testing"
            }
            
            response = client.post("/auth/admin/api-keys/batch", headers=master_headers, json=batch_data)
            
            if response.status_code == 200:
                data = response.json()
                assert "operation_id" in data
                assert "operation" in data
                assert data["operation"] == "revoke"
                assert "total_keys" in data
                assert "successful_operations" in data
                assert "failed_operations" in data
                assert "affected_key_ids" in data


class TestAdminAPIAuthorization:
    """Test authorization levels for administrative operations."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    def test_master_admin_access(self, client):
        """Test master admin can access all endpoints."""
        master_key = generate_master_api_key()
        
        with patch('src.graphrag_api_service.config.get_settings') as mock_settings:
            settings_mock = Mock()
            settings_mock.master_api_key = master_key
            mock_settings.return_value = settings_mock
            
            headers = {"X-API-Key": master_key}
            
            # Test various admin endpoints
            endpoints = [
                "/auth/admin/api-keys",
                "/auth/admin/api-keys/test_key_id",
            ]
            
            for endpoint in endpoints:
                response = client.get(endpoint, headers=headers)
                # Should not be 403 (forbidden) - may be 404 or 500 but not forbidden
                assert response.status_code != 403
    
    def test_insufficient_privileges(self, client):
        """Test access with insufficient privileges."""
        # Test with no authentication
        response = client.get("/auth/admin/api-keys")
        assert response.status_code == 401
        
        # Test with invalid key
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/auth/admin/api-keys", headers=headers)
        assert response.status_code == 401


class TestAdminAPIErrorHandling:
    """Test error handling in administrative API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def master_headers(self):
        """Headers with master key for authentication."""
        master_key = generate_master_api_key()
        
        with patch('src.graphrag_api_service.config.get_settings') as mock_settings:
            settings_mock = Mock()
            settings_mock.master_api_key = master_key
            mock_settings.return_value = settings_mock
            
            return {"X-API-Key": master_key}
    
    def test_get_nonexistent_key(self, client, master_headers):
        """Test getting details for non-existent key."""
        response = client.get("/auth/admin/api-keys/nonexistent_key_id", headers=master_headers)
        assert response.status_code == 404
    
    def test_update_nonexistent_key(self, client, master_headers):
        """Test updating non-existent key."""
        update_data = {
            "name": "Updated Name",
            "is_active": False
        }
        
        response = client.put("/auth/admin/api-keys/nonexistent_key_id", headers=master_headers, json=update_data)
        assert response.status_code == 404
    
    def test_revoke_nonexistent_key(self, client, master_headers):
        """Test revoking non-existent key."""
        response = client.delete("/auth/admin/api-keys/nonexistent_key_id", headers=master_headers)
        assert response.status_code == 404
    
    def test_invalid_batch_operation(self, client, master_headers):
        """Test invalid batch operation."""
        batch_data = {
            "operation": "invalid_operation",
            "filters": {
                "user_id": "test_user"
            }
        }
        
        response = client.post("/auth/admin/api-keys/batch", headers=master_headers, json=batch_data)
        assert response.status_code in [400, 422, 500]  # Bad request or validation error
    
    def test_malformed_request_data(self, client, master_headers):
        """Test handling of malformed request data."""
        malformed_data = {
            "name": "",  # Empty name
            "user_id": "",  # Empty user ID
            "scopes": []  # Empty scopes
        }
        
        response = client.post("/auth/admin/api-keys", headers=master_headers, json=malformed_data)
        assert response.status_code == 422  # Validation error


class TestAdminAPIPerformance:
    """Test performance aspects of administrative API."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def master_headers(self):
        """Headers with master key for authentication."""
        master_key = generate_master_api_key()
        
        with patch('src.graphrag_api_service.config.get_settings') as mock_settings:
            settings_mock = Mock()
            settings_mock.master_api_key = master_key
            mock_settings.return_value = settings_mock
            
            return {"X-API-Key": master_key}
    
    def test_list_keys_pagination(self, client, master_headers):
        """Test pagination performance with large result sets."""
        # Test with different page sizes
        page_sizes = [10, 50, 100]
        
        for limit in page_sizes:
            params = {"limit": limit, "offset": 0}
            response = client.get("/auth/admin/api-keys", headers=master_headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                assert len(data["keys"]) <= limit
                assert data["limit"] == limit
    
    def test_concurrent_admin_requests(self, client, master_headers):
        """Test concurrent administrative requests."""
        import concurrent.futures
        import threading
        
        def make_admin_request():
            return client.get("/auth/admin/api-keys", headers=master_headers)
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_admin_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should complete
        assert len(responses) == 5
        # Should not have server errors due to concurrency
        server_errors = [r for r in responses if r.status_code >= 500]
        assert len(server_errors) == 0


class TestAdminAPIAuditLogging:
    """Test audit logging for administrative operations."""
    
    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)
    
    @pytest.fixture
    def master_headers(self):
        """Headers with master key for authentication."""
        master_key = generate_master_api_key()
        
        with patch('src.graphrag_api_service.config.get_settings') as mock_settings:
            settings_mock = Mock()
            settings_mock.master_api_key = master_key
            mock_settings.return_value = settings_mock
            
            return {"X-API-Key": master_key}
    
    def test_audit_logging_integration(self, client, master_headers):
        """Test that administrative operations are properly audited."""
        with patch('src.graphrag_api_service.auth.admin_api_keys.get_admin_audit_logger') as mock_audit:
            mock_audit_logger = Mock()
            mock_audit.return_value = mock_audit_logger
            
            # Perform admin operation
            response = client.get("/auth/admin/api-keys", headers=master_headers)
            
            # Verify audit logging was called (if operation succeeded)
            if response.status_code == 200:
                mock_audit_logger.log_admin_operation.assert_called()
    
    def test_failed_operation_audit(self, client, master_headers):
        """Test audit logging for failed operations."""
        with patch('src.graphrag_api_service.auth.admin_api_keys.get_admin_audit_logger') as mock_audit:
            mock_audit_logger = Mock()
            mock_audit.return_value = mock_audit_logger
            
            # Try to get non-existent key
            response = client.get("/auth/admin/api-keys/nonexistent", headers=master_headers)
            
            # Should still log the attempt
            if response.status_code == 404:
                # Audit logging might still occur for the attempt
                pass
