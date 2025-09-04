"""
Unit tests for custom exception hierarchy.

Tests the structured exception system for proper error handling,
status codes, and error message formatting.
"""

from fastapi import status

from src.graphrag_api_service.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ExternalServiceError,
    GraphRAGServiceError,
    ProcessingError,
    QuotaExceededError,
    RateLimitError,
    ResourceNotFoundError,
    SecurityError,
    ValidationError,
    insufficient_permissions,
    invalid_workspace_id,
    path_traversal_attempt,
    storage_quota_exceeded,
    workspace_not_found,
)


class TestGraphRAGServiceError:
    """Test base exception class."""

    def test_base_exception_creation(self) -> None:
        """Test basic exception creation."""
        error = GraphRAGServiceError(
            message="Test error", error_code="TEST_ERROR", status_code=400, details={"key": "value"}
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.status_code == 400
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_to_dict_conversion(self) -> None:
        """Test exception to dictionary conversion."""
        error = GraphRAGServiceError(
            message="Test error", error_code="TEST_ERROR", status_code=400, details={"key": "value"}
        )

        result = error.to_dict()
        expected = {
            "error": "TEST_ERROR",
            "message": "Test error",
            "status_code": 400,
            "details": {"key": "value"},
        }

        assert result == expected

    def test_default_values(self) -> None:
        """Test exception with default values."""
        error = GraphRAGServiceError("Test error")

        assert error.message == "Test error"
        assert error.error_code == "GRAPHRAG_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details == {}


class TestValidationError:
    """Test validation error class."""

    def test_validation_error_creation(self) -> None:
        """Test validation error creation."""
        error = ValidationError(message="Invalid input", field="username", value="invalid_user")

        assert error.message == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.details["field"] == "username"
        assert error.details["invalid_value"] == "invalid_user"

    def test_validation_error_without_field(self) -> None:
        """Test validation error without field information."""
        error = ValidationError("General validation error")

        assert error.message == "General validation error"
        assert "field" not in error.details
        assert "invalid_value" not in error.details


class TestAuthenticationError:
    """Test authentication error class."""

    def test_authentication_error_default(self) -> None:
        """Test authentication error with default message."""
        error = AuthenticationError()

        assert error.message == "Authentication failed"
        assert error.error_code == "AUTHENTICATION_ERROR"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentication_error_custom(self) -> None:
        """Test authentication error with custom message."""
        error = AuthenticationError(message="Invalid token", details={"token_type": "JWT"})

        assert error.message == "Invalid token"
        assert error.details["token_type"] == "JWT"


class TestAuthorizationError:
    """Test authorization error class."""

    def test_authorization_error_with_permission(self) -> None:
        """Test authorization error with permission details."""
        error = AuthorizationError(
            message="Access denied", required_permission="read:workspace", resource_id="ws_123"
        )

        assert error.message == "Access denied"
        assert error.error_code == "AUTHORIZATION_ERROR"
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.details["required_permission"] == "read:workspace"
        assert error.details["resource_id"] == "ws_123"


class TestResourceNotFoundError:
    """Test resource not found error class."""

    def test_resource_not_found_with_details(self) -> None:
        """Test resource not found error with resource details."""
        error = ResourceNotFoundError(
            message="Workspace not found", resource_type="workspace", resource_id="ws_123"
        )

        assert error.message == "Workspace not found"
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.details["resource_type"] == "workspace"
        assert error.details["resource_id"] == "ws_123"


class TestQuotaExceededError:
    """Test quota exceeded error class."""

    def test_quota_exceeded_with_metrics(self) -> None:
        """Test quota exceeded error with usage metrics."""
        error = QuotaExceededError(
            message="Storage quota exceeded",
            quota_type="storage",
            current_usage=1024.5,
            quota_limit=1000.0,
        )

        assert error.message == "Storage quota exceeded"
        assert error.error_code == "QUOTA_EXCEEDED"
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.details["quota_type"] == "storage"
        assert error.details["current_usage"] == 1024.5
        assert error.details["quota_limit"] == 1000.0


class TestSecurityError:
    """Test security error class."""

    def test_security_error_with_violation_type(self) -> None:
        """Test security error with violation type."""
        error = SecurityError(message="Path traversal detected", violation_type="path_traversal")

        assert error.message == "Path traversal detected"
        assert error.error_code == "SECURITY_ERROR"
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.details["violation_type"] == "path_traversal"


class TestConvenienceFunctions:
    """Test convenience functions for common errors."""

    def test_workspace_not_found(self) -> None:
        """Test workspace not found convenience function."""
        error = workspace_not_found("ws_123")

        assert isinstance(error, ResourceNotFoundError)
        assert error.message == "Workspace 'ws_123' not found"
        assert error.details["resource_type"] == "workspace"
        assert error.details["resource_id"] == "ws_123"

    def test_insufficient_permissions(self) -> None:
        """Test insufficient permissions convenience function."""
        error = insufficient_permissions("read:workspace", "ws_123")

        assert isinstance(error, AuthorizationError)
        assert error.message == "Insufficient permissions: 'read:workspace' required"
        assert error.details["required_permission"] == "read:workspace"
        assert error.details["resource_id"] == "ws_123"

    def test_invalid_workspace_id(self) -> None:
        """Test invalid workspace ID convenience function."""
        error = invalid_workspace_id("../../../etc/passwd")

        assert isinstance(error, ValidationError)
        assert error.message == "Invalid workspace ID format"
        assert error.details["field"] == "workspace_id"
        assert error.details["invalid_value"] == "../../../etc/passwd"
        assert "expected_format" in error.details

    def test_storage_quota_exceeded(self) -> None:
        """Test storage quota exceeded convenience function."""
        error = storage_quota_exceeded(1024.5, 1000.0)

        assert isinstance(error, QuotaExceededError)
        assert "1024.5MB" in error.message
        assert "1000.0MB" in error.message
        assert error.details["quota_type"] == "storage"
        assert error.details["current_usage"] == 1024.5
        assert error.details["quota_limit"] == 1000.0

    def test_path_traversal_attempt(self) -> None:
        """Test path traversal attempt convenience function."""
        error = path_traversal_attempt("../../../etc/passwd")

        assert isinstance(error, SecurityError)
        assert error.message == "Path traversal attempt detected"
        assert error.details["violation_type"] == "path_traversal"
        assert error.details["attempted_path"] == "../../../etc/passwd"


class TestErrorChaining:
    """Test error handling and chaining."""

    def test_exception_inheritance(self) -> None:
        """Test that all custom exceptions inherit from base."""
        errors = [
            ValidationError("test"),
            AuthenticationError("test"),
            AuthorizationError("test"),
            ResourceNotFoundError("test"),
            QuotaExceededError("test"),
            ConfigurationError("test"),
            ExternalServiceError("test"),
            ProcessingError("test"),
            SecurityError("test"),
            RateLimitError("test"),
        ]

        for error in errors:
            assert isinstance(error, GraphRAGServiceError)
            assert isinstance(error, Exception)

    def test_error_status_codes(self) -> None:
        """Test that errors have appropriate HTTP status codes."""
        error_status_map = {
            ValidationError("test"): status.HTTP_422_UNPROCESSABLE_ENTITY,
            AuthenticationError("test"): status.HTTP_401_UNAUTHORIZED,
            AuthorizationError("test"): status.HTTP_403_FORBIDDEN,
            ResourceNotFoundError("test"): status.HTTP_404_NOT_FOUND,
            QuotaExceededError("test"): status.HTTP_429_TOO_MANY_REQUESTS,
            SecurityError("test"): status.HTTP_403_FORBIDDEN,
            RateLimitError("test"): status.HTTP_429_TOO_MANY_REQUESTS,
        }

        for error, expected_status in error_status_map.items():
            assert error.status_code == expected_status
