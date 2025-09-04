"""
Master key management and validation for GraphRAG API Service.

This module provides master key validation, authentication, and administrative
capabilities that extend the existing authentication infrastructure.
"""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from ..config import get_settings, validate_master_key_format
from ..security import get_security_logger
from .api_keys import APIKeyScope


class MasterKeyInfo(BaseModel):
    """Master key information model."""

    is_valid: bool
    key_hash: str
    created_at: datetime
    last_used_at: datetime | None = None
    usage_count: int = 0
    permissions: list[APIKeyScope]


class MasterKeyValidator:
    """Master key validation and management service."""

    def __init__(self) -> None:
        self.security_logger = get_security_logger()
        self._usage_stats: dict[str, datetime | int | None] = {
            "usage_count": 0,
            "last_used_at": None,
            "created_at": datetime.now(UTC),
        }

    @property
    def settings(self):
        """Get current settings dynamically to support testing."""
        return get_settings()

    def validate_master_key(self, provided_key: str) -> bool:
        """Validate provided master key against configured master key.

        Args:
            provided_key: The key to validate

        Returns:
            bool: True if key is valid
        """
        if not provided_key:
            return False

        # Check if master key is configured
        if not self.settings.master_api_key:
            self.security_logger.security_violation(
                violation_type="master_key_not_configured",
                description="Master key authentication attempted but no master key configured",
            )
            return False

        # Validate format
        if not validate_master_key_format(provided_key):
            self.security_logger.security_violation(
                violation_type="invalid_master_key_format",
                description="Invalid master key format provided",
            )
            return False

        # Constant-time comparison to prevent timing attacks
        expected_hash = hashlib.sha256(self.settings.master_api_key.encode()).hexdigest()
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()

        is_valid = secrets.compare_digest(expected_hash, provided_hash)

        if is_valid:
            self._update_usage_stats()
            self.security_logger.authentication_attempt(
                success=True, user_id="master_admin", method="master_key"
            )
        else:
            self.security_logger.authentication_attempt(
                success=False,
                user_id="unknown",
                method="master_key",
                failure_reason="Invalid master key",
            )

        return is_valid

    def get_master_key_info(self) -> MasterKeyInfo:
        """Get master key information (excluding the actual key).

        Returns:
            MasterKeyInfo: Master key metadata
        """
        if not self.settings.master_api_key:
            return MasterKeyInfo(
                is_valid=False, key_hash="", created_at=datetime.now(UTC), permissions=[]
            )

        key_hash = hashlib.sha256(self.settings.master_api_key.encode()).hexdigest()[:16]

        created_at = self._usage_stats["created_at"]
        last_used_at = self._usage_stats["last_used_at"]
        usage_count = self._usage_stats["usage_count"]

        # Type safety checks
        if not isinstance(created_at, datetime):
            created_at = datetime.now(UTC)
        if last_used_at is not None and not isinstance(last_used_at, datetime):
            last_used_at = None
        if not isinstance(usage_count, int):
            usage_count = 0

        return MasterKeyInfo(
            is_valid=True,
            key_hash=key_hash,
            created_at=created_at,
            last_used_at=last_used_at,
            usage_count=usage_count,
            permissions=[
                APIKeyScope.MASTER_ADMIN,
                APIKeyScope.MANAGE_ALL_KEYS,
                APIKeyScope.SYSTEM_ADMIN,
                APIKeyScope.ADMIN_AUDIT,
                APIKeyScope.ADMIN_BATCH_OPS,
                # Master key has all permissions
                APIKeyScope.READ_WORKSPACES,
                APIKeyScope.WRITE_WORKSPACES,
                APIKeyScope.DELETE_WORKSPACES,
                APIKeyScope.READ_GRAPH,
                APIKeyScope.WRITE_GRAPH,
                APIKeyScope.READ_SYSTEM,
                APIKeyScope.READ_USERS,
                APIKeyScope.WRITE_USERS,
                APIKeyScope.MANAGE_API_KEYS,
            ],
        )

    def get_master_permissions(self) -> list[str]:
        """Get all permissions available to master key.

        Returns:
            list[str]: List of permission strings
        """
        master_info = self.get_master_key_info()
        return [scope.value for scope in master_info.permissions]

    def is_master_key_configured(self) -> bool:
        """Check if master key is properly configured.

        Returns:
            bool: True if master key is configured and valid
        """
        return self.settings.master_api_key is not None and validate_master_key_format(
            self.settings.master_api_key
        )

    def _update_usage_stats(self) -> None:
        """Update master key usage statistics."""
        current_count = self._usage_stats["usage_count"]
        if isinstance(current_count, int):
            self._usage_stats["usage_count"] = current_count + 1
        else:
            self._usage_stats["usage_count"] = 1
        self._usage_stats["last_used_at"] = datetime.now(UTC)

    def generate_new_master_key(self) -> str:
        """Generate a new master key for rotation.

        Returns:
            str: New master key

        Note:
            This generates a key but does not update the configuration.
            The key must be manually set in the environment.
        """
        from ..config import generate_master_api_key

        new_key = generate_master_api_key()

        # Log key generation (without the actual key)
        self.security_logger.security_violation(
            violation_type="master_key_generated",
            description="New master key generated for rotation",
            severity="medium",
        )

        return new_key

    def validate_admin_operation(self, operation: str, user_permissions: list[str]) -> bool:
        """Validate if user can perform administrative operation.

        Args:
            operation: Operation being attempted
            user_permissions: User's current permissions

        Returns:
            bool: True if operation is allowed
        """
        # Master admin can do everything
        if APIKeyScope.MASTER_ADMIN.value in user_permissions:
            return True

        # Map operations to required permissions
        operation_permissions = {
            "list_all_keys": [APIKeyScope.MANAGE_ALL_KEYS.value, APIKeyScope.SYSTEM_ADMIN.value],
            "create_user_key": [APIKeyScope.MANAGE_ALL_KEYS.value],
            "revoke_any_key": [APIKeyScope.MANAGE_ALL_KEYS.value],
            "batch_operations": [APIKeyScope.ADMIN_BATCH_OPS.value],
            "system_admin": [APIKeyScope.SYSTEM_ADMIN.value],
            "audit_access": [APIKeyScope.ADMIN_AUDIT.value],
        }

        required_perms = operation_permissions.get(operation, [])
        return any(perm in user_permissions for perm in required_perms)


class AdminAuditLog(BaseModel):
    """Administrative operation audit log model."""

    operation_id: str
    admin_user_id: str
    operation_type: str
    affected_resources: list[str]
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime
    success: bool
    error_message: str | None = None


class AdminAuditLogger:
    """Administrative operation audit logging service."""

    def __init__(self) -> None:
        self.security_logger = get_security_logger()
        self._audit_logs: list[AdminAuditLog] = []

    def log_admin_operation(
        self,
        operation_id: str,
        admin_user_id: str,
        operation_type: str,
        affected_resources: list[str],
        success: bool,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log administrative operation for audit trail.

        Args:
            operation_id: Unique operation identifier
            admin_user_id: ID of admin performing operation
            operation_type: Type of operation performed
            affected_resources: List of affected resource IDs
            success: Whether operation succeeded
            before_state: State before operation
            after_state: State after operation
            ip_address: Admin's IP address
            user_agent: Admin's user agent
            error_message: Error message if operation failed
        """
        audit_entry = AdminAuditLog(
            operation_id=operation_id,
            admin_user_id=admin_user_id,
            operation_type=operation_type,
            affected_resources=affected_resources,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(UTC),
            success=success,
            error_message=error_message,
        )

        # Store audit log
        self._audit_logs.append(audit_entry)

        # Log to security logger
        self.security_logger.authentication_attempt(
            success=success, user_id=admin_user_id, method="admin_operation"
        )

        # Log detailed admin operation
        self.security_logger.suspicious_activity(
            activity_type="admin_operation",
            description=f"Admin operation: {operation_type}",
            user_id=admin_user_id,
            operation_type=operation_type,
            affected_resources=affected_resources,
            success=success,
        )

    def get_audit_logs(
        self,
        admin_user_id: str | None = None,
        operation_type: str | None = None,
        limit: int = 100,
    ) -> list[AdminAuditLog]:
        """Get audit logs with optional filtering.

        Args:
            admin_user_id: Filter by admin user ID
            operation_type: Filter by operation type
            limit: Maximum number of logs to return

        Returns:
            list[AdminAuditLog]: Filtered audit logs
        """
        logs = self._audit_logs

        if admin_user_id:
            logs = [log for log in logs if log.admin_user_id == admin_user_id]

        if operation_type:
            logs = [log for log in logs if log.operation_type == operation_type]

        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]


# Global instances
_master_key_validator = MasterKeyValidator()
_admin_audit_logger = AdminAuditLogger()


def get_master_key_validator() -> MasterKeyValidator:
    """Get the global master key validator instance."""
    return _master_key_validator


def get_admin_audit_logger() -> AdminAuditLogger:
    """Get the global admin audit logger instance."""
    return _admin_audit_logger
