# src/graphrag_api_service/security/security_config.py
# Security configuration and hardening settings
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Security configuration and hardening settings."""

import secrets
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CORSConfig(BaseModel):
    """CORS configuration settings."""

    enabled: bool = Field(default=True, description="Enable CORS")
    allow_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8001"],
        description="Allowed origins",
    )
    allow_credentials: bool = Field(default=True, description="Allow credentials")
    allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    allow_headers: list[str] = Field(default=["*"], description="Allowed headers")
    max_age: int = Field(default=3600, description="Max age for preflight requests")

    @field_validator("allow_origins")
    @classmethod
    def validate_origins(cls, v: list[str]) -> list[str]:
        """Validate origins are properly formatted."""
        for origin in v:
            if origin == "*":
                continue
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid origin format: {origin}")
        return v


class HeadersConfig(BaseModel):
    """Security headers configuration."""

    x_content_type_options: str = Field(
        default="nosniff", description="X-Content-Type-Options header"
    )
    x_frame_options: str = Field(default="DENY", description="X-Frame-Options header")
    x_xss_protection: str = Field(default="1; mode=block", description="X-XSS-Protection header")
    strict_transport_security: str = Field(
        default="max-age=31536000; includeSubDomains",
        description="Strict-Transport-Security header",
    )
    content_security_policy: str = Field(
        default="default-src 'self'", description="Content-Security-Policy header"
    )
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin", description="Referrer-Policy header"
    )


class InputValidationConfig(BaseModel):
    """Input validation configuration."""

    max_query_length: int = Field(default=10000, description="Maximum query length")
    max_request_size: int = Field(
        default=10 * 1024 * 1024, description="Maximum request size in bytes"
    )
    max_json_depth: int = Field(default=10, description="Maximum JSON nesting depth")
    allowed_content_types: list[str] = Field(
        default=["application/json", "text/plain"], description="Allowed content types"
    )
    sanitize_inputs: bool = Field(default=True, description="Enable input sanitization")
    validate_json_schema: bool = Field(default=True, description="Validate JSON against schema")


class AuthenticationConfig(BaseModel):
    """Authentication configuration."""

    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    require_strong_passwords: bool = Field(default=True, description="Require strong passwords")
    min_password_length: int = Field(default=8, description="Minimum password length")
    require_mfa: bool = Field(default=False, description="Require multi-factor authentication")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(
        default=15, description="Account lockout duration in minutes"
    )


class APISecurityConfig(BaseModel):
    """API security configuration."""

    api_key_required: bool = Field(default=False, description="Require API key for access")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    rotate_api_keys: bool = Field(default=True, description="Enable API key rotation")
    api_key_expiry_days: int = Field(default=90, description="API key expiry in days")
    log_api_access: bool = Field(default=True, description="Log API access")
    detect_anomalies: bool = Field(default=True, description="Enable anomaly detection")


class SQLInjectionProtection(BaseModel):
    """SQL injection protection settings."""

    use_parameterized_queries: bool = Field(
        default=True, description="Use parameterized queries only"
    )
    escape_special_characters: bool = Field(default=True, description="Escape special characters")
    validate_query_structure: bool = Field(default=True, description="Validate query structure")
    block_suspicious_patterns: bool = Field(
        default=True, description="Block suspicious SQL patterns"
    )
    log_suspicious_queries: bool = Field(default=True, description="Log suspicious queries")


class SecurityConfig(BaseModel):
    """Main security configuration."""

    cors: CORSConfig = Field(default_factory=CORSConfig)
    headers: HeadersConfig = Field(default_factory=HeadersConfig)
    input_validation: InputValidationConfig = Field(default_factory=InputValidationConfig)
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    api_security: APISecurityConfig = Field(default_factory=APISecurityConfig)
    sql_protection: SQLInjectionProtection = Field(default_factory=SQLInjectionProtection)

    # Global security settings
    enable_security: bool = Field(default=True, description="Enable security features")
    security_audit_log: bool = Field(default=True, description="Enable security audit logging")
    intrusion_detection: bool = Field(default=True, description="Enable intrusion detection")
    block_suspicious_ips: bool = Field(default=True, description="Block suspicious IP addresses")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    enable_ddos_protection: bool = Field(default=True, description="Enable DDoS protection")

    def get_security_headers(self) -> dict[str, str]:
        """Get security headers dictionary."""
        if not self.enable_security:
            return {}

        return {
            "X-Content-Type-Options": self.headers.x_content_type_options,
            "X-Frame-Options": self.headers.x_frame_options,
            "X-XSS-Protection": self.headers.x_xss_protection,
            "Strict-Transport-Security": self.headers.strict_transport_security,
            "Content-Security-Policy": self.headers.content_security_policy,
            "Referrer-Policy": self.headers.referrer_policy,
        }

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration dictionary."""
        if not self.cors.enabled:
            return {}

        return {
            "allow_origins": self.cors.allow_origins,
            "allow_credentials": self.cors.allow_credentials,
            "allow_methods": self.cors.allow_methods,
            "allow_headers": self.cors.allow_headers,
            "max_age": self.cors.max_age,
        }


# Default security configuration instance
default_security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get the current security configuration."""
    return default_security_config
