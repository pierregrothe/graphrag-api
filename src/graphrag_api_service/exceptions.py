"""
Custom exception hierarchy for GraphRAG API Service.

This module provides a structured exception system for better error handling,
logging, and client communication across the entire service.
"""

from typing import Any, Dict, Optional
from fastapi import status


class GraphRAGServiceError(Exception):
    """Base exception for all GraphRAG service errors.
    
    Attributes
    ----------
    message : str
        Human-readable error message
    error_code : str
        Machine-readable error code for client handling
    status_code : int
        HTTP status code for API responses
    details : dict, optional
        Additional error context and debugging information
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "GRAPHRAG_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


class ValidationError(GraphRAGServiceError):
    """Data validation and input sanitization errors.
    
    Used for invalid user inputs, malformed requests, and data validation failures.
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


class AuthenticationError(GraphRAGServiceError):
    """Authentication failures and token-related errors.
    
    Used for invalid credentials, expired tokens, and authentication failures.
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(GraphRAGServiceError):
    """Permission and access control errors.
    
    Used for insufficient permissions, access denied, and authorization failures.
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=error_details
        )


class ResourceNotFoundError(GraphRAGServiceError):
    """Resource not found errors.
    
    Used when requested resources (workspaces, entities, etc.) don't exist.
    """
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=error_details
        )


class QuotaExceededError(GraphRAGServiceError):
    """Resource quota and limit exceeded errors.
    
    Used when operations would exceed configured limits or quotas.
    """
    
    def __init__(
        self,
        message: str,
        quota_type: Optional[str] = None,
        current_usage: Optional[float] = None,
        quota_limit: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if quota_type:
            error_details["quota_type"] = quota_type
        if current_usage is not None:
            error_details["current_usage"] = current_usage
        if quota_limit is not None:
            error_details["quota_limit"] = quota_limit
        
        super().__init__(
            message=message,
            error_code="QUOTA_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=error_details
        )


class ConfigurationError(GraphRAGServiceError):
    """Configuration and setup errors.
    
    Used for invalid configurations, missing settings, and setup failures.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class ExternalServiceError(GraphRAGServiceError):
    """External service integration errors.
    
    Used for LLM provider failures, database connection issues, and external API errors.
    """
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        service_error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
        if service_error:
            error_details["service_error"] = service_error
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=error_details
        )


class ProcessingError(GraphRAGServiceError):
    """Data processing and computation errors.
    
    Used for graph processing failures, indexing errors, and computation failures.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        if stage:
            error_details["stage"] = stage
        
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class SecurityError(GraphRAGServiceError):
    """Security-related errors and violations.
    
    Used for path traversal attempts, suspicious activities, and security violations.
    """
    
    def __init__(
        self,
        message: str,
        violation_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if violation_type:
            error_details["violation_type"] = violation_type
        
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=error_details
        )


class RateLimitError(GraphRAGServiceError):
    """Rate limiting and throttling errors.
    
    Used when request rate limits are exceeded.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        if limit_type:
            error_details["limit_type"] = limit_type
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=error_details
        )


# Convenience functions for common error scenarios
def workspace_not_found(workspace_id: str) -> ResourceNotFoundError:
    """Create a workspace not found error."""
    return ResourceNotFoundError(
        message=f"Workspace '{workspace_id}' not found",
        resource_type="workspace",
        resource_id=workspace_id
    )


def insufficient_permissions(required_permission: str, resource_id: str = None) -> AuthorizationError:
    """Create an insufficient permissions error."""
    return AuthorizationError(
        message=f"Insufficient permissions: '{required_permission}' required",
        required_permission=required_permission,
        resource_id=resource_id
    )


def invalid_workspace_id(workspace_id: str) -> ValidationError:
    """Create an invalid workspace ID error."""
    return ValidationError(
        message="Invalid workspace ID format",
        field="workspace_id",
        value=workspace_id,
        details={
            "expected_format": "alphanumeric characters, hyphens, and underscores only",
            "max_length": 255
        }
    )


def storage_quota_exceeded(current_mb: float, limit_mb: float) -> QuotaExceededError:
    """Create a storage quota exceeded error."""
    return QuotaExceededError(
        message=f"Storage quota exceeded: {current_mb:.1f}MB used of {limit_mb:.1f}MB limit",
        quota_type="storage",
        current_usage=current_mb,
        quota_limit=limit_mb
    )


def path_traversal_attempt(attempted_path: str) -> SecurityError:
    """Create a path traversal security error."""
    return SecurityError(
        message="Path traversal attempt detected",
        violation_type="path_traversal",
        details={"attempted_path": attempted_path}
    )
