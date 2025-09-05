# src/graphrag_api_service/utils/security.py
# Security utilities for authentication and input validation
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Security utilities for password validation, input sanitization, and rate limiting."""

import html
import re
import time
from collections import defaultdict

from ..exceptions import ValidationError


class PasswordValidator:
    """Password strength validation utility."""

    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?",
    ):
        """Initialize password validator.

        Args:
            min_length: Minimum password length
            max_length: Maximum password length
            require_uppercase: Require uppercase letters
            require_lowercase: Require lowercase letters
            require_digits: Require digits
            require_special: Require special characters
            special_chars: Allowed special characters
        """
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
        self.special_chars = special_chars

        # Common weak passwords to reject
        self.weak_passwords = {
            "password",
            "123456",
            "123456789",
            "qwerty",
            "abc123",
            "password123",
            "admin",
            "letmein",
            "welcome",
            "monkey",
            "dragon",
            "master",
            "shadow",
            "superman",
            "michael",
            "football",
            "baseball",
            "liverpool",
            "jordan",
            "princess",
        }

    def validate(self, password: str) -> tuple[bool, list[str]]:
        """Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not password:
            errors.append("Password cannot be empty")
            return False, errors

        # Length checks
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")

        if len(password) > self.max_length:
            errors.append(f"Password must be less than {self.max_length} characters long")

        # Character requirements
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append(
                f"Password must contain at least one special character: {self.special_chars}"
            )

        # Check for common weak passwords
        if password.lower() in self.weak_passwords:
            errors.append("Password is too common and easily guessable")

        # Check for simple patterns
        if self._has_simple_patterns(password):
            errors.append("Password contains simple patterns and is easily guessable")

        return len(errors) == 0, errors

    def _has_simple_patterns(self, password: str) -> bool:
        """Check for simple patterns in password."""
        password_lower = password.lower()

        # Check for repeated characters (more than 3 in a row)
        if re.search(r"(.)\1{3,}", password):
            return True

        # Check for sequential characters
        sequences = [
            "abcdefghijklmnopqrstuvwxyz",
            "0123456789",
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
        ]

        for seq in sequences:
            for i in range(len(seq) - 3):
                if seq[i : i + 4] in password_lower or seq[i : i + 4][::-1] in password_lower:
                    return True

        return False


class InputSanitizer:
    """Input sanitization utility."""

    @staticmethod
    def sanitize_string(input_str: str, max_length: int | None = None) -> str:
        """Sanitize string input.

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(input_str, str):
            input_str = str(input_str)

        # Strip whitespace
        sanitized = input_str.strip()

        # HTML escape
        sanitized = html.escape(sanitized)

        # Remove null bytes and control characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Truncate if necessary
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email address.

        Args:
            email: Email address to sanitize

        Returns:
            Sanitized email address

        Raises:
            ValidationError: If email format is invalid
        """
        if not email:
            raise ValidationError("Email cannot be empty")

        # Basic sanitization
        email = email.strip().lower()

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")

        # Check for suspicious patterns
        if ".." in email or email.startswith(".") or email.endswith("."):
            raise ValidationError("Invalid email format")

        return email

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Sanitize username.

        Args:
            username: Username to sanitize

        Returns:
            Sanitized username

        Raises:
            ValidationError: If username format is invalid
        """
        if not username:
            raise ValidationError("Username cannot be empty")

        # Basic sanitization
        username = username.strip()

        # Username validation (alphanumeric, underscore, hyphen only)
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        # Length validation
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")

        if len(username) > 50:
            raise ValidationError("Username must be less than 50 characters long")

        return username


class RateLimitHelper:
    """Rate limiting utility."""

    def __init__(self):
        """Initialize rate limit helper."""
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
        current_time: float | None = None,
    ) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            identifier: Unique identifier for the client (IP, user ID, etc.)
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            current_time: Current timestamp (for testing)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if current_time is None:
            current_time = time.time()

        # Cleanup old entries periodically
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(current_time)

        # Get request history for this identifier
        request_times = self._requests[identifier]

        # Remove requests outside the current window
        cutoff_time = current_time - window_seconds
        request_times[:] = [t for t in request_times if t > cutoff_time]

        # Check if limit exceeded
        if len(request_times) >= max_requests:
            # Calculate retry after time
            oldest_request = min(request_times)
            retry_after = int(oldest_request + window_seconds - current_time) + 1
            return False, max(retry_after, 1)

        # Add current request
        request_times.append(current_time)

        return True, 0

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old rate limit entries."""
        cutoff_time = current_time - 3600  # Keep 1 hour of history

        for identifier in list(self._requests.keys()):
            request_times = self._requests[identifier]
            request_times[:] = [t for t in request_times if t > cutoff_time]

            # Remove empty entries
            if not request_times:
                del self._requests[identifier]

        self._last_cleanup = current_time

    def reset_identifier(self, identifier: str) -> None:
        """Reset rate limit for a specific identifier.

        Args:
            identifier: Identifier to reset
        """
        if identifier in self._requests:
            del self._requests[identifier]


# Global instances for convenience
_password_validator = PasswordValidator()
_input_sanitizer = InputSanitizer()
_rate_limit_helper = RateLimitHelper()


def validate_password_strength(password: str) -> None:
    """Validate password strength using default validator.

    Args:
        password: Password to validate

    Raises:
        ValidationError: If password is not strong enough
    """
    is_valid, errors = _password_validator.validate(password)
    if not is_valid:
        raise ValidationError(f"Password validation failed: {'; '.join(errors)}")


def sanitize_input(input_str: str, max_length: int | None = None) -> str:
    """Sanitize string input using default sanitizer.

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    return _input_sanitizer.sanitize_string(input_str, max_length)


def check_rate_limit(identifier: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Check rate limit using default helper.

    Args:
        identifier: Unique identifier for the client
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds

    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    return _rate_limit_helper.check_rate_limit(identifier, max_requests, window_seconds)
