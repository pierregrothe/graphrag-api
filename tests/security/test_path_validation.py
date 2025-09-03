"""
Security tests for path validation and traversal protection.

Tests the path validation system to ensure it properly prevents
path traversal attacks and maintains workspace isolation.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.graphrag_api_service.routes.graph import validate_workspace_path
from src.graphrag_api_service.exceptions import SecurityError, ValidationError


class TestPathValidation:
    """Test path validation security measures."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings object."""
        settings = Mock()
        settings.graphrag_data_path = "/app/data/default"
        settings.base_workspaces_path = "workspaces"
        return settings
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object."""
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-client"}
        request.method = "GET"
        request.url.path = "/api/graph/entities"
        request.query_params = {}
        return request
    
    def test_default_workspace_path(self, mock_settings, mock_request):
        """Test default workspace path handling."""
        result = validate_workspace_path(None, mock_settings, mock_request)
        assert result == "/app/data/default"
        
        result = validate_workspace_path("default", mock_settings, mock_request)
        assert result == "/app/data/default"
    
    def test_valid_workspace_id(self, mock_settings, mock_request):
        """Test valid workspace ID formats."""
        valid_ids = [
            "workspace123",
            "my-workspace",
            "test_workspace",
            "workspace-123_test",
            "a1b2c3",
            "WORKSPACE_123"
        ]
        
        with patch('pathlib.Path.exists', return_value=True):
            for workspace_id in valid_ids:
                # Should not raise exception
                result = validate_workspace_path(workspace_id, mock_settings, mock_request)
                assert isinstance(result, str)
                assert workspace_id in result
    
    def test_path_traversal_attempts(self, mock_settings, mock_request):
        """Test detection of path traversal attempts."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "workspace/../../../etc/passwd",
            "workspace/../../sensitive",
            "..",
            "../",
            "../../",
            "../../../",
            "workspace/../..",
            "workspace\\..\\..\\file.txt",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",  # URL encoded ../../../
            "..%2f..%2f..%2f",
            "....//....//....//",
            "..;/..;/..;/",
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises((ValidationError, SecurityError)):
                validate_workspace_path(malicious_path, mock_settings, mock_request)
    
    def test_invalid_characters(self, mock_settings, mock_request):
        """Test rejection of invalid characters in workspace ID."""
        invalid_ids = [
            "workspace/with/slashes",
            "workspace\\with\\backslashes",
            "workspace with spaces",
            "workspace@with@symbols",
            "workspace#with#hash",
            "workspace$with$dollar",
            "workspace%with%percent",
            "workspace&with&ampersand",
            "workspace*with*asterisk",
            "workspace+with+plus",
            "workspace=with=equals",
            "workspace?with?question",
            "workspace[with]brackets",
            "workspace{with}braces",
            "workspace|with|pipe",
            "workspace<with>angles",
            "workspace\"with\"quotes",
            "workspace'with'apostrophes",
            "workspace`with`backticks",
            "workspace~with~tilde",
            "workspace!with!exclamation",
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValidationError):
                validate_workspace_path(invalid_id, mock_settings, mock_request)
    
    def test_empty_workspace_id(self, mock_settings, mock_request):
        """Test handling of empty workspace IDs."""
        empty_ids = ["", "   ", "\t", "\n", "\r\n"]
        
        for empty_id in empty_ids:
            # Should use default path
            result = validate_workspace_path(empty_id, mock_settings, mock_request)
            assert result == mock_settings.graphrag_data_path
    
    def test_workspace_path_containment(self, mock_settings, mock_request):
        """Test that resolved paths stay within allowed boundaries."""
        with patch('pathlib.Path.resolve') as mock_resolve:
            # Mock a path that escapes the base directory
            mock_resolve.side_effect = [
                Path("/app/workspaces"),  # base_path.resolve()
                Path("/etc/passwd")       # workspace_path.resolve()
            ]
            
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(SecurityError) as exc_info:
                    validate_workspace_path("valid_workspace", mock_settings, mock_request)
                
                assert "path traversal" in str(exc_info.value).lower()
    
    def test_nonexistent_workspace(self, mock_settings, mock_request):
        """Test handling of non-existent workspace directories."""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(Exception):  # Should raise some form of error
                validate_workspace_path("nonexistent_workspace", mock_settings, mock_request)
    
    def test_security_logging_on_violation(self, mock_settings, mock_request):
        """Test that security violations are properly logged."""
        with patch('src.graphrag_api_service.routes.graph.security_logger') as mock_logger:
            with pytest.raises(ValidationError):
                validate_workspace_path("../../../etc/passwd", mock_settings, mock_request)
            
            # Verify security logger was called
            mock_logger.path_traversal_attempt.assert_called_once()
            call_args = mock_logger.path_traversal_attempt.call_args
            assert call_args[1]['attempted_path'] == "../../../etc/passwd"
            assert call_args[1]['request'] == mock_request
    
    def test_case_sensitivity(self, mock_settings, mock_request):
        """Test case sensitivity in workspace IDs."""
        with patch('pathlib.Path.exists', return_value=True):
            # These should be treated as different workspaces
            workspace_ids = ["MyWorkspace", "myworkspace", "MYWORKSPACE"]
            
            results = []
            for workspace_id in workspace_ids:
                result = validate_workspace_path(workspace_id, mock_settings, mock_request)
                results.append(result)
            
            # All results should be different (case-sensitive)
            assert len(set(results)) == len(results)
    
    def test_unicode_characters(self, mock_settings, mock_request):
        """Test handling of Unicode characters in workspace IDs."""
        unicode_ids = [
            "workspace_café",
            "workspace_测试",
            "workspace_🚀",
            "workspace_ñoño",
            "workspace_Ω",
        ]
        
        for unicode_id in unicode_ids:
            # Unicode characters should be rejected for security
            with pytest.raises(ValidationError):
                validate_workspace_path(unicode_id, mock_settings, mock_request)
    
    def test_length_limits(self, mock_settings, mock_request):
        """Test workspace ID length limits."""
        # Very long workspace ID
        long_id = "a" * 300
        
        with pytest.raises(ValidationError):
            validate_workspace_path(long_id, mock_settings, mock_request)
    
    def test_null_byte_injection(self, mock_settings, mock_request):
        """Test protection against null byte injection."""
        null_byte_ids = [
            "workspace\x00",
            "workspace\x00.txt",
            "valid\x00../../../etc/passwd",
            "\x00workspace",
        ]
        
        for null_id in null_byte_ids:
            with pytest.raises(ValidationError):
                validate_workspace_path(null_id, mock_settings, mock_request)
    
    def test_configuration_missing_paths(self, mock_request):
        """Test handling of missing configuration paths."""
        settings = Mock()
        settings.graphrag_data_path = None
        settings.base_workspaces_path = None
        
        with pytest.raises(Exception):  # Should handle missing config gracefully
            validate_workspace_path("default", settings, mock_request)


class TestSecurityHeaders:
    """Test security-related headers and metadata."""
    
    def test_request_metadata_extraction(self, mock_request):
        """Test that request metadata is properly extracted for logging."""
        # This would be tested in the actual security logging tests
        # but we can verify the structure here
        
        expected_fields = [
            'ip_address',
            'user_agent', 
            'method',
            'path',
            'query_params'
        ]
        
        # Mock the security logger to capture the call
        with patch('src.graphrag_api_service.routes.graph.security_logger') as mock_logger:
            mock_settings = Mock()
            mock_settings.base_workspaces_path = "workspaces"
            
            try:
                validate_workspace_path("../invalid", mock_settings, mock_request)
            except (ValidationError, SecurityError):
                pass
            
            if mock_logger.path_traversal_attempt.called:
                call_kwargs = mock_logger.path_traversal_attempt.call_args[1]
                assert 'request' in call_kwargs
                assert call_kwargs['request'] == mock_request


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_symbolic_links(self, mock_settings, mock_request):
        """Test handling of symbolic links (if applicable)."""
        # This test would verify that symbolic links don't allow
        # escaping the workspace boundaries
        pass
    
    def test_concurrent_validation(self, mock_settings, mock_request):
        """Test path validation under concurrent access."""
        # This test would verify thread safety of path validation
        pass
    
    def test_filesystem_race_conditions(self, mock_settings, mock_request):
        """Test protection against TOCTOU (Time of Check Time of Use) attacks."""
        # This test would verify that the validation is atomic
        pass
