"""
Security logging module for GraphRAG API Service.

This module provides structured security logging for authentication events,
authorization failures, suspicious activities, and security violations.
Enhanced with comprehensive security monitoring and alerting capabilities.
"""

import json
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import Request


class SecurityLogger:
    """Structured security event logger.

    Provides methods for logging security-related events with consistent
    formatting and metadata for security monitoring and analysis.
    Enhanced with real-time threat detection and alerting.
    """

    def __init__(self, logger_name: str = "graphrag.security"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Ensure security logs are always written
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Security monitoring state
        self.failed_attempts: dict[str, list[float]] = defaultdict(list)
        self.suspicious_ips: set[str] = set()
        self.blocked_ips: set[str] = set()
        self.security_alerts: list[dict[str, Any]] = []

        # Thresholds for security monitoring
        self.max_failed_attempts = 5
        self.failed_attempts_window = 300  # 5 minutes
        self.suspicious_threshold = 10
        self.critical_threshold = 20

    def _log_security_event(
        self,
        event_type: str,
        level: str,
        message: str,
        request: Request | None = None,
        user_id: str | None = None,
        **kwargs: Any,
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
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            **kwargs,
        }

        # Extract request metadata if available
        if request:
            event_data.update(
                {
                    "ip_address": getattr(request.client, "host", None),
                    "user_agent": request.headers.get("user-agent"),
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "headers": {
                        key: value
                        for key, value in request.headers.items()
                        if key.lower() not in ["authorization", "cookie", "x-api-key"]
                    },
                }
            )

        # Log with appropriate level
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(json.dumps(event_data, default=str))

    def authentication_attempt(
        self,
        success: bool,
        user_id: str | None = None,
        method: str = "jwt",
        request: Request | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """Log authentication attempt with enhanced threat detection.

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

        # Enhanced threat detection for failed attempts
        if not success and request:
            client_ip = getattr(request.client, "host", "unknown")
            self._track_failed_attempt(client_ip, request)

        self._log_security_event(
            event_type="authentication",
            level=level,
            message=message,
            request=request,
            user_id=user_id,
            success=success,
            method=method,
            failure_reason=failure_reason,
        )

    def authorization_failure(
        self,
        user_id: str,
        required_permission: str,
        resource_id: str | None = None,
        request: Request | None = None,
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
            resource_id=resource_id,
        )

    def security_violation(
        self,
        violation_type: str,
        description: str,
        request: Request | None = None,
        user_id: str | None = None,
        severity: str = "high",
        **details: Any,
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
            **details,
        )

    def path_traversal_attempt(
        self, attempted_path: str, request: Request | None = None, user_id: str | None = None
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
            attempted_path=attempted_path,
        )

    def suspicious_activity(
        self,
        activity_type: str,
        description: str,
        request: Request | None = None,
        user_id: str | None = None,
        **details: Any,
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
            **details,
        )

    def rate_limit_exceeded(
        self,
        limit_type: str,
        request: Request | None = None,
        user_id: str | None = None,
        current_rate: float | None = None,
        limit: float | None = None,
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
            limit=limit,
        )

    def api_key_usage(
        self,
        api_key_id: str,
        success: bool,
        request: Request | None = None,
        permissions_used: list | None = None,
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
            permissions_used=permissions_used,
        )

    def workspace_access(
        self,
        workspace_id: str,
        user_id: str,
        action: str,
        success: bool,
        request: Request | None = None,
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
            success=success,
        )

    def _track_failed_attempt(self, client_ip: str, request: Request) -> None:
        """Track failed authentication attempts for threat detection."""
        current_time = time.time()

        # Add failed attempt
        self.failed_attempts[client_ip].append(current_time)

        # Clean up old attempts (outside window)
        cutoff_time = current_time - self.failed_attempts_window
        self.failed_attempts[client_ip] = [
            t for t in self.failed_attempts[client_ip] if t > cutoff_time
        ]

        # Check for suspicious activity
        attempt_count = len(self.failed_attempts[client_ip])

        if attempt_count >= self.critical_threshold:
            self._generate_security_alert(
                "critical_threat_detected",
                f"Critical threat: {attempt_count} failed attempts from {client_ip}",
                client_ip,
                request,
                severity="critical",
            )
            self.blocked_ips.add(client_ip)

        elif attempt_count >= self.suspicious_threshold:
            self._generate_security_alert(
                "suspicious_activity",
                f"Suspicious activity: {attempt_count} failed attempts from {client_ip}",
                client_ip,
                request,
                severity="high",
            )
            self.suspicious_ips.add(client_ip)

        elif attempt_count >= self.max_failed_attempts:
            self._generate_security_alert(
                "multiple_failed_attempts",
                f"Multiple failed attempts: {attempt_count} from {client_ip}",
                client_ip,
                request,
                severity="medium",
            )

    def _generate_security_alert(
        self,
        alert_type: str,
        message: str,
        client_ip: str,
        request: Request | None = None,
        severity: str = "medium",
    ) -> None:
        """Generate a security alert for monitoring systems."""
        alert = {
            "timestamp": datetime.now(UTC).isoformat(),
            "alert_type": alert_type,
            "message": message,
            "client_ip": client_ip,
            "severity": severity,
            "user_agent": request.headers.get("User-Agent") if request else None,
            "path": request.url.path if request else None,
        }

        self.security_alerts.append(alert)

        # Keep only recent alerts (last 1000)
        if len(self.security_alerts) > 1000:
            self.security_alerts = self.security_alerts[-1000:]

        # Log the alert
        level = "critical" if severity == "critical" else "error"
        self._log_security_event(
            event_type="security_alert",
            level=level,
            message=message,
            request=request,
            alert_type=alert_type,
            severity=severity,
            client_ip=client_ip,
        )

    def get_security_status(self) -> dict[str, Any]:
        """Get current security status and statistics."""
        current_time = time.time()
        cutoff_time = current_time - 3600  # Last hour

        # Count recent failed attempts
        recent_failures = 0
        active_threats = 0

        for ip, attempts in self.failed_attempts.items():
            recent_attempts = [t for t in attempts if t > cutoff_time]
            recent_failures += len(recent_attempts)

            if len(recent_attempts) >= self.suspicious_threshold:
                active_threats += 1

        # Count recent alerts
        recent_alerts = [
            alert
            for alert in self.security_alerts
            if datetime.fromisoformat(alert["timestamp"].replace("Z", "+00:00")).timestamp()
            > cutoff_time
        ]

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "failed_attempts_last_hour": recent_failures,
            "active_threats": active_threats,
            "suspicious_ips": len(self.suspicious_ips),
            "blocked_ips": len(self.blocked_ips),
            "recent_alerts": len(recent_alerts),
            "alert_breakdown": (
                {
                    alert["severity"]: len(
                        [a for a in recent_alerts if a["severity"] == alert["severity"]]
                    )
                    for alert in recent_alerts
                }
                if recent_alerts
                else {}
            ),
            "top_threat_ips": sorted(
                [(ip, len(attempts)) for ip, attempts in self.failed_attempts.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }

    def is_ip_blocked(self, client_ip: str) -> bool:
        """Check if an IP address is blocked."""
        return client_ip in self.blocked_ips

    def is_ip_suspicious(self, client_ip: str) -> bool:
        """Check if an IP address is marked as suspicious."""
        return client_ip in self.suspicious_ips

    def unblock_ip(self, client_ip: str) -> bool:
        """Unblock an IP address (admin function)."""
        if client_ip in self.blocked_ips:
            self.blocked_ips.remove(client_ip)
            self.suspicious_ips.discard(client_ip)
            self.failed_attempts.pop(client_ip, None)

            self._log_security_event(
                event_type="admin_action",
                level="info",
                message=f"IP address unblocked: {client_ip}",
                admin_action="unblock_ip",
                target_ip=client_ip,
            )
            return True
        return False

    def reset_security_state(self) -> None:
        """Reset all security monitoring state (admin function)."""
        self.failed_attempts.clear()
        self.suspicious_ips.clear()
        self.blocked_ips.clear()
        self.security_alerts.clear()

        self._log_security_event(
            event_type="admin_action",
            level="warning",
            message="Security monitoring state reset",
            admin_action="reset_security_state",
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
