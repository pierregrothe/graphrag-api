"""
Security logging module for GraphRAG API Service.

This module provides structured security logging for authentication events,
authorization failures, suspicious activities, and security violations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request

from ..exceptions import SecurityError


class SecurityLogger:
    """Structured security event logger.
    
    Provides methods for logging security-related events with consistent
    formatting and metadata for security monitoring and analysis.
    """
    
    def __init__(self, logger_name: str = "graphrag.security"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Ensure security logs are always written
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log_security_event(
        self,
        event_type: str,
        level: str,
        message: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a structured security event.
        
        Parameters
        ----------
        event_type : str
            Type of security event (authentication, authorization, etc.)
        level : str
            Log level (info, warning, error, critical)
        message : str
            Human-readable event description
        request : Request, optional
            FastAPI request object for extracting metadata
        user_id : str, optional
            User ID associated with the event
        **kwargs
            Additional event-specific data
        """
        event_data = {
            "event_type": event_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            **kwargs
        }
        
        # Extract request metadata if available
        if request:
            event_data.update({
                "ip_address": getattr(request.client, 'host', None),
                "user_agent": request.headers.get("user-agent"),
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": {
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ['authorization', 'cookie', 'x-api-key']
                }
            })
        
        # Log with appropriate level
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(json.dumps(event_data, default=str))
    
    def authentication_attempt(
        self,
        success: bool,
        user_id: Optional[str] = None,
        method: str = "jwt",
        request: Optional[Request] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """Log authentication attempt.
        
        Parameters
        ----------
        success : bool
            Whether authentication was successful
        user_id : str, optional
            User ID (if known)
        method : str
            Authentication method used
        request : Request, optional
            Request object
        failure_reason : str, optional
            Reason for authentication failure
        """
        level = "info" if success else "warning"
        message = f"Authentication {'succeeded' if success else 'failed'}"
        
        self._log_security_event(
            event_type="authentication",
            level=level,
            message=message,
            request=request,
            user_id=user_id,
            success=success,
            method=method,
            failure_reason=failure_reason
        )
    
    def authorization_failure(
        self,
        user_id: str,
        required_permission: str,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log authorization failure.
        
        Parameters
        ----------
        user_id : str
            User ID attempting access
        required_permission : str
            Permission that was required
        resource_id : str, optional
            ID of resource being accessed
        request : Request, optional
            Request object
        """
        message = f"Authorization failed: user lacks '{required_permission}' permission"
        
        self._log_security_event(
            event_type="authorization",
            level="warning",
            message=message,
            request=request,
            user_id=user_id,
            required_permission=required_permission,
            resource_id=resource_id
        )
    
    def security_violation(
        self,
        violation_type: str,
        description: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        severity: str = "high",
        **details
    ) -> None:
        """Log security violation.
        
        Parameters
        ----------
        violation_type : str
            Type of security violation
        description : str
            Description of the violation
        request : Request, optional
            Request object
        user_id : str, optional
            User ID (if known)
        severity : str
            Severity level (low, medium, high, critical)
        **details
            Additional violation details
        """
        level = "critical" if severity == "critical" else "error"
        message = f"Security violation: {description}"
        
        self._log_security_event(
            event_type="security_violation",
            level=level,
            message=message,
            request=request,
            user_id=user_id,
            violation_type=violation_type,
            severity=severity,
            **details
        )
    
    def path_traversal_attempt(
        self,
        attempted_path: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log path traversal attempt.
        
        Parameters
        ----------
        attempted_path : str
            Path that was attempted
        request : Request, optional
            Request object
        user_id : str, optional
            User ID (if known)
        """
        self.security_violation(
            violation_type="path_traversal",
            description="Path traversal attempt detected",
            request=request,
            user_id=user_id,
            severity="high",
            attempted_path=attempted_path
        )
    
    def suspicious_activity(
        self,
        activity_type: str,
        description: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        **details
    ) -> None:
        """Log suspicious activity.
        
        Parameters
        ----------
        activity_type : str
            Type of suspicious activity
        description : str
            Description of the activity
        request : Request, optional
            Request object
        user_id : str, optional
            User ID (if known)
        **details
            Additional activity details
        """
        self._log_security_event(
            event_type="suspicious_activity",
            level="warning",
            message=f"Suspicious activity: {description}",
            request=request,
            user_id=user_id,
            activity_type=activity_type,
            **details
        )
    
    def rate_limit_exceeded(
        self,
        limit_type: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        current_rate: Optional[float] = None,
        limit: Optional[float] = None
    ) -> None:
        """Log rate limit exceeded event.
        
        Parameters
        ----------
        limit_type : str
            Type of rate limit exceeded
        request : Request, optional
            Request object
        user_id : str, optional
            User ID (if known)
        current_rate : float, optional
            Current request rate
        limit : float, optional
            Rate limit threshold
        """
        message = f"Rate limit exceeded: {limit_type}"
        
        self._log_security_event(
            event_type="rate_limit",
            level="warning",
            message=message,
            request=request,
            user_id=user_id,
            limit_type=limit_type,
            current_rate=current_rate,
            limit=limit
        )
    
    def api_key_usage(
        self,
        api_key_id: str,
        success: bool,
        request: Optional[Request] = None,
        permissions_used: Optional[list] = None
    ) -> None:
        """Log API key usage.
        
        Parameters
        ----------
        api_key_id : str
            API key identifier (not the actual key)
        success : bool
            Whether the API key was valid
        request : Request, optional
            Request object
        permissions_used : list, optional
            Permissions that were checked
        """
        level = "info" if success else "warning"
        message = f"API key {'used successfully' if success else 'authentication failed'}"
        
        self._log_security_event(
            event_type="api_key_usage",
            level=level,
            message=message,
            request=request,
            api_key_id=api_key_id,
            success=success,
            permissions_used=permissions_used
        )
    
    def workspace_access(
        self,
        workspace_id: str,
        user_id: str,
        action: str,
        success: bool,
        request: Optional[Request] = None
    ) -> None:
        """Log workspace access attempt.
        
        Parameters
        ----------
        workspace_id : str
            Workspace identifier
        user_id : str
            User attempting access
        action : str
            Action being attempted
        success : bool
            Whether access was granted
        request : Request, optional
            Request object
        """
        level = "info" if success else "warning"
        message = f"Workspace access {'granted' if success else 'denied'}: {action}"
        
        self._log_security_event(
            event_type="workspace_access",
            level=level,
            message=message,
            request=request,
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            success=success
        )


# Global security logger instance
security_logger = SecurityLogger()


def get_security_logger() -> SecurityLogger:
    """Get the global security logger instance.
    
    Returns
    -------
    SecurityLogger
        The global security logger instance
    """
    return security_logger
