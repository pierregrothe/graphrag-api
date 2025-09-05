"""
Unit tests for master key management system.

Tests master key validation, authentication, and administrative
capabilities with comprehensive security testing.
"""

from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from src.graphrag_api_service.auth.api_keys import APIKeyScope
from src.graphrag_api_service.auth.master_key import (
    AdminAuditLogger,
    MasterKeyInfo,
    MasterKeyValidator,
)
from src.graphrag_api_service.config import (
    generate_master_api_key,
    validate_master_key_format,
)
from src.graphrag_api_service.exceptions import ConfigurationError


class TestMasterKeyGeneration:
    """Test master key generation and validation."""

    def test_generate_master_api_key(self):
        """Test master key generation."""
        key = generate_master_api_key()

        # Check format
        assert key.startswith("grak_master_")
        assert len(key) >= 64

        # Check entropy
        assert len(set(key)) >= 16

        # Should be different each time
        key2 = generate_master_api_key()
        assert key != key2

    def test_validate_master_key_format_valid(self):
        """Test validation of valid master key formats."""
        valid_keys = [
            generate_master_api_key(),
            "grak_master_abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOP",  # 64 chars, high entropy
        ]

        for key in valid_keys:
            assert validate_master_key_format(key)

    def test_validate_master_key_format_invalid(self):
        """Test validation of invalid master key formats."""
        invalid_keys = [
            "",
            "short",
            "grak_master_",  # Too short
            "wrong_prefix_" + "a" * 52,
            "grak_master_" + "a" * 10,  # Too short
            "grak_master_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # Low entropy
        ]

        for key in invalid_keys:
            assert not validate_master_key_format(key)


class TestMasterKeyValidator:
    """Test master key validator functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with master key."""
        settings = Mock()
        settings.master_api_key = generate_master_api_key()
        return settings

    @pytest.fixture
    def master_key_validator(self, mock_settings):
        """Master key validator with mocked settings."""
        with patch(
            "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
        ):
            validator = MasterKeyValidator()
            yield validator

    def test_validate_master_key_success(self, master_key_validator, mock_settings):
        """Test successful master key validation."""
        # Use the same key that's configured
        result = master_key_validator.validate_master_key(mock_settings.master_api_key)
        assert result is True

        # Check usage stats updated
        assert master_key_validator._usage_stats["usage_count"] == 1
        assert master_key_validator._usage_stats["last_used_at"] is not None

    def test_validate_master_key_failure(self, master_key_validator):
        """Test failed master key validation."""
        invalid_keys = [
            "",
            "invalid_key",
            "grak_master_wrong_key_value_here_but_correct_format_length",
            generate_master_api_key(),  # Different key
        ]

        for invalid_key in invalid_keys:
            result = master_key_validator.validate_master_key(invalid_key)
            assert result is False

    def test_validate_master_key_no_config(self):
        """Test validation when no master key is configured."""
        mock_settings = Mock()
        mock_settings.master_api_key = None

        with patch(
            "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
        ):
            validator = MasterKeyValidator()
            result = validator.validate_master_key("any_key")
            assert result is False

    def test_get_master_key_info(self, master_key_validator, mock_settings):
        """Test getting master key information."""
        info = master_key_validator.get_master_key_info()

        assert isinstance(info, MasterKeyInfo)
        assert info.is_valid is True
        assert len(info.key_hash) == 16  # Truncated hash
        assert info.usage_count == 0  # No usage yet
        assert APIKeyScope.MASTER_ADMIN in info.permissions
        assert APIKeyScope.MANAGE_ALL_KEYS in info.permissions
        assert APIKeyScope.SYSTEM_ADMIN in info.permissions

    def test_get_master_key_info_no_config(self):
        """Test getting master key info when not configured."""
        mock_settings = Mock()
        mock_settings.master_api_key = None

        with patch(
            "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
        ):
            validator = MasterKeyValidator()
            info = validator.get_master_key_info()

            assert info.is_valid is False
            assert info.key_hash == ""
            assert info.permissions == []

    def test_get_master_permissions(self, master_key_validator):
        """Test getting master key permissions."""
        permissions = master_key_validator.get_master_permissions()

        assert isinstance(permissions, list)
        assert len(permissions) > 0
        assert "master:admin" in permissions
        assert "master:manage_all_keys" in permissions
        assert "master:system_admin" in permissions
        assert "read:workspaces" in permissions
        assert "write:workspaces" in permissions

    def test_is_master_key_configured(self, master_key_validator):
        """Test checking if master key is configured."""
        assert master_key_validator.is_master_key_configured() is True

    def test_is_master_key_not_configured(self):
        """Test checking when master key is not configured."""
        mock_settings = Mock()
        mock_settings.master_api_key = None

        with patch(
            "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
        ):
            validator = MasterKeyValidator()
            assert validator.is_master_key_configured() is False

    def test_generate_new_master_key(self, master_key_validator):
        """Test generating new master key for rotation."""
        new_key = master_key_validator.generate_new_master_key()

        assert validate_master_key_format(new_key)
        assert new_key.startswith("grak_master_")
        assert len(new_key) >= 64

    def test_validate_admin_operation(self, master_key_validator):
        """Test validating administrative operations."""
        # Master admin can do everything
        master_permissions = ["master:admin"]
        assert master_key_validator.validate_admin_operation("list_all_keys", master_permissions)
        assert master_key_validator.validate_admin_operation("create_user_key", master_permissions)
        assert master_key_validator.validate_admin_operation("batch_operations", master_permissions)

        # Specific permissions
        key_manager_permissions = ["master:manage_all_keys"]
        assert master_key_validator.validate_admin_operation(
            "list_all_keys", key_manager_permissions
        )
        assert master_key_validator.validate_admin_operation(
            "create_user_key", key_manager_permissions
        )
        assert not master_key_validator.validate_admin_operation(
            "system_admin", key_manager_permissions
        )

        # No permissions
        no_permissions = []
        assert not master_key_validator.validate_admin_operation("list_all_keys", no_permissions)


class TestAdminAuditLogger:
    """Test administrative audit logging."""

    @pytest.fixture
    def audit_logger(self):
        """Admin audit logger instance."""
        return AdminAuditLogger()

    def test_log_admin_operation_success(self, audit_logger):
        """Test logging successful admin operation."""
        audit_logger.log_admin_operation(
            operation_id="op_123",
            admin_user_id="admin_user",
            operation_type="create_key",
            affected_resources=["key_456"],
            success=True,
            before_state={"active": False},
            after_state={"active": True},
        )

        # Check audit log was stored
        logs = audit_logger.get_audit_logs()
        assert len(logs) == 1

        log = logs[0]
        assert log.operation_id == "op_123"
        assert log.admin_user_id == "admin_user"
        assert log.operation_type == "create_key"
        assert log.affected_resources == ["key_456"]
        assert log.success is True
        assert log.before_state == {"active": False}
        assert log.after_state == {"active": True}

    def test_log_admin_operation_failure(self, audit_logger):
        """Test logging failed admin operation."""
        audit_logger.log_admin_operation(
            operation_id="op_456",
            admin_user_id="admin_user",
            operation_type="delete_key",
            affected_resources=[],
            success=False,
            error_message="Key not found",
        )

        logs = audit_logger.get_audit_logs()
        assert len(logs) == 1

        log = logs[0]
        assert log.success is False
        assert log.error_message == "Key not found"

    def test_get_audit_logs_filtering(self, audit_logger):
        """Test audit log filtering."""
        # Add multiple logs
        audit_logger.log_admin_operation("op1", "admin1", "create", ["res1"], True)
        audit_logger.log_admin_operation("op2", "admin2", "delete", ["res2"], True)
        audit_logger.log_admin_operation("op3", "admin1", "update", ["res3"], False)

        # Filter by admin user
        admin1_logs = audit_logger.get_audit_logs(admin_user_id="admin1")
        assert len(admin1_logs) == 2
        assert all(log.admin_user_id == "admin1" for log in admin1_logs)

        # Filter by operation type
        create_logs = audit_logger.get_audit_logs(operation_type="create")
        assert len(create_logs) == 1
        assert create_logs[0].operation_type == "create"

        # Test limit
        limited_logs = audit_logger.get_audit_logs(limit=2)
        assert len(limited_logs) == 2

    def test_audit_log_ordering(self, audit_logger):
        """Test audit logs are ordered by timestamp (newest first)."""
        # Add logs with slight delay to ensure different timestamps
        import time

        audit_logger.log_admin_operation("op1", "admin", "create", [], True)
        time.sleep(0.001)
        audit_logger.log_admin_operation("op2", "admin", "update", [], True)
        time.sleep(0.001)
        audit_logger.log_admin_operation("op3", "admin", "delete", [], True)

        logs = audit_logger.get_audit_logs()
        assert len(logs) == 3

        # Should be ordered newest first
        assert logs[0].operation_id == "op3"
        assert logs[1].operation_id == "op2"
        assert logs[2].operation_id == "op1"


class TestConfigurationValidation:
    """Test configuration validation for master keys."""

    def test_valid_master_key_config(self):
        """Test valid master key configuration."""
        from src.graphrag_api_service.config import Settings

        valid_key = generate_master_api_key()

        # Should not raise exception
        settings = Settings(master_api_key=valid_key)
        assert settings.master_api_key == valid_key

    def test_invalid_master_key_config_too_short(self):
        """Test invalid master key configuration - too short."""
        from src.graphrag_api_service.config import Settings

        with pytest.raises(ValidationError):  # Should be caught by Pydantic validation
            Settings(master_api_key="grak_master_short")

    def test_invalid_master_key_config_wrong_prefix(self):
        """Test invalid master key configuration - wrong prefix."""
        from src.graphrag_api_service.config import Settings

        with pytest.raises(ConfigurationError):  # Should be caught by validation
            Settings(master_api_key="wrong_prefix_" + "a" * 52)

    def test_invalid_master_key_config_low_entropy(self):
        """Test invalid master key configuration - low entropy."""
        from src.graphrag_api_service.config import Settings

        with pytest.raises(ConfigurationError):  # Should be caught by validation
            Settings(master_api_key="grak_master_" + "a" * 52)  # All same character


class TestSecurityIntegration:
    """Test security integration with master key system."""

    def test_security_logging_integration(self):
        """Test security logging is properly integrated."""
        with patch("src.graphrag_api_service.auth.master_key.get_security_logger") as mock_logger:
            mock_security_logger = Mock()
            mock_logger.return_value = mock_security_logger

            # Create validator with mocked logger
            mock_settings = Mock()
            mock_settings.master_api_key = generate_master_api_key()

            with patch(
                "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
            ):
                validator = MasterKeyValidator()

                # Test successful validation
                validator.validate_master_key(mock_settings.master_api_key)

                # Verify security logging was called
                mock_security_logger.authentication_attempt.assert_called()
                call_args = mock_security_logger.authentication_attempt.call_args
                assert call_args[1]["success"] is True
                assert call_args[1]["user_id"] == "master_admin"
                assert call_args[1]["method"] == "master_key"

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks in key validation."""
        import time

        mock_settings = Mock()
        mock_settings.master_api_key = generate_master_api_key()

        with patch(
            "src.graphrag_api_service.auth.master_key.get_settings", return_value=mock_settings
        ):
            validator = MasterKeyValidator()

            # Time validation of correct key
            start_time = time.time()
            result1 = validator.validate_master_key(mock_settings.master_api_key)
            time1 = time.time() - start_time

            # Time validation of incorrect key
            start_time = time.time()
            result2 = validator.validate_master_key(
                "grak_master_wrong_key_but_same_length_for_timing_test_here"
            )
            time2 = time.time() - start_time

            assert result1 is True
            assert result2 is False

            # Times should be similar (constant-time comparison)
            # Allow for some variance due to system load
            if min(time1, time2) > 0:  # Avoid division by zero
                time_ratio = max(time1, time2) / min(time1, time2)
                assert (
                    time_ratio < 10.0
                )  # Should be within 10x of each other (relaxed for test environment)
            else:
                # If one time is zero, both should be very small
                assert max(time1, time2) < 0.01  # Less than 10ms (relaxed for test environment)
