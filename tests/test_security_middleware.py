# tests/test_security_middleware.py
# Tests for Security Middleware Components
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for security middleware including CORS, rate limiting, and audit logging."""

import time
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException, Request
from fastapi.responses import Response

from src.graphrag_api_service.security.middleware import (
    SecurityConfig,
    SecurityMiddleware,
    RateLimiter,
    RequestValidator,
    AuditLogger,
)


class TestRateLimiter:
    """Test cases for the rate limiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(requests_per_minute=10, burst_limit=5)

    def test_rate_limiting_allows_initial_requests(self, rate_limiter):
        """Test that initial requests are allowed."""
        client_id = "test_client"
        
        # First few requests should be allowed
        for _ in range(5):
            assert rate_limiter.is_allowed(client_id) is True

    def test_rate_limiting_blocks_burst_requests(self, rate_limiter):
        """Test that burst requests are blocked."""
        client_id = "test_client"
        
        # Fill up the burst limit
        for _ in range(5):
            rate_limiter.is_allowed(client_id)
        
        # Next request should be blocked
        assert rate_limiter.is_allowed(client_id) is False

    def test_rate_limiting_per_minute_limit(self, rate_limiter):
        """Test per-minute rate limiting."""
        client_id = "test_client"
        
        # Simulate requests over time
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000.0
            
            # Fill up the per-minute limit
            for _ in range(10):
                rate_limiter.is_allowed(client_id)
            
            # Next request should be blocked
            assert rate_limiter.is_allowed(client_id) is False

    def test_rate_limiting_resets_after_time(self, rate_limiter):
        """Test that rate limiting resets after time passes."""
        client_id = "test_client"
        
        with patch('time.time') as mock_time:
            # Fill up the limit
            mock_time.return_value = 1000.0
            for _ in range(10):
                rate_limiter.is_allowed(client_id)
            
            # Should be blocked
            assert rate_limiter.is_allowed(client_id) is False
            
            # Move time forward by more than a minute
            mock_time.return_value = 1070.0
            
            # Should be allowed again
            assert rate_limiter.is_allowed(client_id) is True

    def test_remaining_requests_calculation(self, rate_limiter):
        """Test remaining requests calculation."""
        client_id = "test_client"
        
        # Initial remaining should be the full limit
        remaining = rate_limiter.get_remaining_requests(client_id)
        assert remaining == 10
        
        # After some requests, remaining should decrease
        for _ in range(3):
            rate_limiter.is_allowed(client_id)
        
        remaining = rate_limiter.get_remaining_requests(client_id)
        assert remaining == 7


class TestRequestValidator:
    """Test cases for the request validator."""

    @pytest.fixture
    def validator(self):
        """Create a request validator for testing."""
        config = SecurityConfig(
            max_request_size_mb=1,
            required_headers=["x-api-key"],
            blocked_user_agents=["badbot"]
        )
        return RequestValidator(config)

    def test_request_size_validation_passes(self, validator):
        """Test that valid request sizes pass validation."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "1000"  # 1000 bytes
        
        # Should not raise an exception
        validator.validate_request_size(mock_request)

    def test_request_size_validation_fails(self, validator):
        """Test that oversized requests fail validation."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = str(2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_request_size(mock_request)
        
        assert exc_info.value.status_code == 413

    def test_required_headers_validation_passes(self, validator):
        """Test that requests with required headers pass validation."""
        mock_request = MagicMock()
        mock_request.headers.keys.return_value = ["x-api-key", "content-type"]
        
        # Should not raise an exception
        validator.validate_headers(mock_request)

    def test_required_headers_validation_fails(self, validator):
        """Test that requests missing required headers fail validation."""
        mock_request = MagicMock()
        mock_request.headers.keys.return_value = ["content-type"]
        
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_headers(mock_request)
        
        assert exc_info.value.status_code == 400

    def test_user_agent_validation_passes(self, validator):
        """Test that allowed user agents pass validation."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0 (compatible; goodbot)"
        
        # Should not raise an exception
        validator.validate_user_agent(mock_request)

    def test_user_agent_validation_fails(self, validator):
        """Test that blocked user agents fail validation."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "badbot/1.0"
        
        with pytest.raises(HTTPException) as exc_info:
            validator.validate_user_agent(mock_request)
        
        assert exc_info.value.status_code == 403

    def test_input_sanitization(self, validator):
        """Test input data sanitization."""
        # Test string sanitization
        dirty_string = "<script>alert('xss')</script>test"
        clean_string = validator.sanitize_input(dirty_string)
        assert "<script" not in clean_string
        assert "&lt;script" in clean_string

        # Test dict sanitization
        dirty_dict = {"key": "<script>alert('xss')</script>"}
        clean_dict = validator.sanitize_input(dirty_dict)
        assert "<script" not in clean_dict["key"]

        # Test list sanitization
        dirty_list = ["<script>alert('xss')</script>", "clean"]
        clean_list = validator.sanitize_input(dirty_list)
        assert "<script" not in clean_list[0]
        assert clean_list[1] == "clean"


class TestAuditLogger:
    """Test cases for the audit logger."""

    @pytest.fixture
    def audit_logger(self):
        """Create an audit logger for testing."""
        return AuditLogger()

    def test_request_logging(self, audit_logger):
        """Test request logging functionality."""
        audit_logger.log_request(
            request_id="test-123",
            method="GET",
            path="/api/test",
            user_agent="test-agent",
            ip_address="127.0.0.1",
            status_code=200,
            response_time=0.1,
        )
        
        log_entries = audit_logger.get_audit_log(limit=10)
        assert len(log_entries) == 1
        assert log_entries[0].request_id == "test-123"
        assert log_entries[0].method == "GET"
        assert log_entries[0].status_code == 200

    def test_error_request_logging(self, audit_logger):
        """Test error request logging."""
        audit_logger.log_request(
            request_id="error-123",
            method="POST",
            path="/api/error",
            user_agent="test-agent",
            ip_address="127.0.0.1",
            status_code=500,
            response_time=0.5,
            error_message="Internal server error",
        )
        
        log_entries = audit_logger.get_audit_log(limit=10)
        assert len(log_entries) == 1
        assert log_entries[0].status_code == 500
        assert log_entries[0].error_message == "Internal server error"

    def test_security_summary_generation(self, audit_logger):
        """Test security summary generation."""
        # Log various requests
        audit_logger.log_request("req1", "GET", "/api/test", "agent", "127.0.0.1", 200, 0.1)
        audit_logger.log_request("req2", "POST", "/api/test", "agent", "127.0.0.1", 400, 0.2)
        audit_logger.log_request("req3", "GET", "/api/other", "agent", "192.168.1.1", 500, 0.3)
        
        summary = audit_logger.get_security_summary()
        
        assert "total_requests" in summary
        assert "status_code_distribution" in summary
        assert "error_rate" in summary
        assert summary["total_requests"] == 3
        assert summary["error_rate"] > 0  # Should have some errors


class TestSecurityMiddleware:
    """Test cases for the security middleware."""

    @pytest.fixture
    def security_middleware(self):
        """Create a security middleware for testing."""
        config = SecurityConfig(
            rate_limiting_enabled=True,
            requests_per_minute=10,
            security_headers_enabled=True,
        )
        return SecurityMiddleware(config)

    def test_client_ip_extraction(self, security_middleware):
        """Test client IP address extraction."""
        # Test with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "x-forwarded-for": "192.168.1.1, 10.0.0.1",
            "x-real-ip": None
        }.get(key)
        mock_request.client.host = "127.0.0.1"
        
        ip = security_middleware.get_client_ip(mock_request)
        assert ip == "192.168.1.1"

        # Test with X-Real-IP header
        mock_request.headers.get.side_effect = lambda key: {
            "x-forwarded-for": None,
            "x-real-ip": "192.168.1.2"
        }.get(key)
        
        ip = security_middleware.get_client_ip(mock_request)
        assert ip == "192.168.1.2"

        # Test with client.host fallback
        mock_request.headers.get.return_value = None
        
        ip = security_middleware.get_client_ip(mock_request)
        assert ip == "127.0.0.1"

    def test_security_headers_addition(self, security_middleware):
        """Test security headers addition."""
        mock_response = MagicMock()
        mock_response.headers = {}
        
        security_middleware.add_security_headers(mock_response)
        
        assert "Content-Security-Policy" in mock_response.headers
        assert "X-Frame-Options" in mock_response.headers
        assert "X-Content-Type-Options" in mock_response.headers
        assert "X-XSS-Protection" in mock_response.headers

    @pytest.mark.asyncio
    async def test_request_processing_success(self, security_middleware):
        """Test successful request processing."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers.get.side_effect = lambda key: {
            "content-length": "100",
            "user-agent": "test-agent"
        }.get(key)
        mock_request.headers.keys.return_value = []
        mock_request.client.host = "127.0.0.1"
        
        # Should not raise an exception
        await security_middleware.process_request(mock_request)

    @pytest.mark.asyncio
    async def test_request_processing_rate_limit(self, security_middleware):
        """Test request processing with rate limiting."""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers.get.side_effect = lambda key: {
            "content-length": "100",
            "user-agent": "test-agent"
        }.get(key)
        mock_request.headers.keys.return_value = []
        mock_request.client.host = "127.0.0.1"
        
        # Fill up the rate limit
        for _ in range(10):
            await security_middleware.process_request(mock_request)
        
        # Next request should be rate limited
        with pytest.raises(HTTPException) as exc_info:
            await security_middleware.process_request(mock_request)
        
        assert exc_info.value.status_code == 429

    def test_cors_config_creation(self, security_middleware):
        """Test CORS configuration creation."""
        cors_config = security_middleware.get_cors_config()
        assert cors_config is not None
        assert "allow_origins" in cors_config
        assert "allow_methods" in cors_config
