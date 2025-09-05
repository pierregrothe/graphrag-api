# src/graphrag_api_service/config.py
# Configuration management for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Configuration settings for the GraphRAG API service."""

import os
import secrets
from enum import Enum

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigurationError


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    GOOGLE_GEMINI = "google_gemini"


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # API Settings
    app_name: str = "GraphRAG API Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server Settings
    # Note: 0.0.0.0 binding is intentional for API service - use firewall/proxy for security
    host: str = "0.0.0.0"  # nosec B104 - Required for container deployment
    port: int = 8001  # Changed from 8000 to avoid Docker conflicts

    # GraphRAG Settings
    graphrag_config_path: str | None = None
    graphrag_data_path: str | None = None
    base_workspaces_path: str = Field(
        default="workspaces",
        description="Base directory for workspace data (security boundary)",
    )

    # Workspace Lifecycle Management
    workspace_ttl_hours: int = Field(
        default=24,
        description="Default workspace TTL in hours (0 = no expiration)",
    )
    workspace_cleanup_enabled: bool = Field(
        default=True,
        description="Enable automatic workspace cleanup",
    )
    workspace_cleanup_interval_minutes: int = Field(
        default=60,
        description="Interval between cleanup runs in minutes",
    )
    workspace_max_idle_hours: int = Field(
        default=12,
        description="Maximum idle time before workspace is eligible for cleanup",
    )
    workspace_grace_period_minutes: int = Field(
        default=30,
        description="Grace period before cleanup when active operations detected",
    )
    workspace_max_size_mb: int = Field(
        default=1000,
        description="Maximum workspace size in MB (0 = no limit)",
    )
    workspace_usage_tracking_enabled: bool = Field(
        default=True,
        description="Enable workspace usage tracking and metrics",
    )

    # LLM Provider Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM provider to use (ollama or google_gemini)",
    )

    # Ollama Configuration (Local)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL",
    )
    ollama_llm_model: str = Field(
        default="gemma:4b",
        description="Ollama LLM model name",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name",
    )

    # Google Gemini Configuration (Cloud & Vertex AI)
    google_api_key: str | None = Field(
        default=None,
        description="Google Cloud API key for Gemini",
    )
    google_project_id: str | None = Field(
        default=None,
        description="Google Cloud project ID",
    )
    google_location: str = Field(
        default="us-central1",
        description="Google Cloud location",
    )
    google_cloud_use_vertex_ai: bool = Field(
        default=False,
        description="Use Vertex AI endpoints instead of standard Gemini API",
    )
    vertex_ai_endpoint: str | None = Field(
        default=None,
        description="Custom Vertex AI endpoint URL (optional)",
    )
    vertex_ai_location: str = Field(
        default="us-central1",
        description="Vertex AI location for regional endpoints",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model version",
    )
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Gemini embedding model",
    )

    # Authentication & Security Settings
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32),
        description=(
            "Secret key for JWT token signing - must be set via JWT_SECRET_KEY "
            "environment variable in production"
        ),
        min_length=32,  # Minimum 32 characters for security
    )

    # Master Key Configuration
    master_api_key: str | None = Field(
        default=None,
        description=(
            "Master API key for administrative operations - must be set via "
            "MASTER_API_KEY environment variable"
        ),
        min_length=64,  # Minimum 64 characters for master key security
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )
    api_key_prefix: str = Field(
        default="grag_",
        description="Prefix for generated API keys",
    )
    default_rate_limit: int = Field(
        default=1000,
        description="Default rate limit (requests per window)",
    )
    rate_limit_window: int = Field(
        default=3600,
        description="Rate limit window in seconds",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key security requirements."""
        # Check for insecure default values
        insecure_defaults = [
            "your-secret-key-change-in-production",
            "your-secret-key-here",
            "secret",
            "jwt-secret",
            "change-me",
        ]

        if v.lower() in [default.lower() for default in insecure_defaults]:
            raise ValueError(
                "JWT secret key cannot use default insecure values. "
                "Set JWT_SECRET_KEY environment variable with a secure random key."
            )

        # Ensure minimum security requirements
        if len(v) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters long for security. "
                "Use a cryptographically secure random string."
            )

        return v

    @field_validator("master_api_key")
    @classmethod
    def validate_master_api_key(cls, v: str | None) -> str | None:
        """Validate master API key security requirements."""
        if v is None:
            return v

        # Check minimum length
        if len(v) < 64:
            raise ConfigurationError(
                "Master API key must be at least 64 characters long", config_key="master_api_key"
            )

        # Check entropy (minimum 16 unique characters)
        if len(set(v)) < 16:
            raise ConfigurationError(
                "Master API key must have sufficient entropy (at least 16 unique characters)",
                config_key="master_api_key",
            )

        # Check format (should start with grak_master_)
        if not v.startswith("grak_master_"):
            raise ConfigurationError(
                "Master API key must start with 'grak_master_' prefix", config_key="master_api_key"
            )

        return v

    @field_validator("api_key_prefix")
    @classmethod
    def validate_api_key_prefix(cls, v: str) -> str:
        """Validate API key prefix security requirements."""
        if len(v) < 4:
            raise ValueError("API key prefix must be at least 4 characters long for security")

        # Prevent common insecure prefixes
        insecure_prefixes = ["api_", "key_", "test_", "dev_", "admin_"]
        if v.lower() in insecure_prefixes:
            raise ValueError(
                f"API key prefix '{v}' is too generic. Use a unique prefix for your service."
            )

        return v

    @field_validator("default_rate_limit")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate rate limit is reasonable for security."""
        if v <= 0:
            raise ValueError("Rate limit must be positive")

        if v > 10000:
            raise ValueError(
                "Rate limit is very high (>10000). Consider if this is appropriate for security."
            )

        return v

    # Monitoring & Observability Settings
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint",
    )
    tracing_enabled: bool = Field(
        default=False,
        description="Enable distributed tracing",
    )
    tracing_service_name: str = Field(
        default="graphrag-api",
        description="Service name for tracing",
    )
    jaeger_endpoint: str = Field(
        default="http://localhost:14268/api/traces",
        description="Jaeger collector endpoint",
    )

    # Performance Tuning Settings
    max_request_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum request size in bytes",
    )
    request_timeout: int = Field(
        default=300,
        description="Request timeout in seconds",
    )
    graphql_max_complexity: int = Field(
        default=1000,
        description="Maximum GraphQL query complexity",
    )
    cache_default_ttl: int = Field(
        default=300,
        description="Default cache TTL in seconds",
    )

    # Feature Flags
    enable_subscriptions: bool = Field(
        default=True,
        description="Enable GraphQL subscriptions",
    )
    enable_real_time_updates: bool = Field(
        default=True,
        description="Enable real-time updates via WebSocket",
    )
    enable_advanced_analytics: bool = Field(
        default=True,
        description="Enable advanced analytics features",
    )
    enable_performance_monitoring: bool = Field(
        default=True,
        description="Enable performance monitoring",
    )

    # Database Settings
    database_type: str = Field(
        default="sqlite",
        description="Database type (only sqlite supported in simplified architecture)",
    )
    database_path: str = Field(
        default="data/graphrag.db",
        description="SQLite database file path",
    )
    # Legacy fields kept for compatibility
    database_url: str = Field(
        default="",
        description="Legacy field - not used with SQLite",
    )
    database_pool_size: int = Field(
        default=5,
        description="Legacy field - not used with SQLite",
    )

    # Cache Settings
    cache_type: str = Field(
        default="memory",
        description="Cache type (memory or redis)",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Default cache TTL in seconds",
    )

    # Redis Settings (optional, only if cache_type=redis)
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis for distributed caching",
    )

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("base_workspaces_path")
    @classmethod
    def validate_workspace_path(cls, v: str) -> str:
        """Validate workspace path format."""
        if not v or v.strip() == "":
            raise ConfigurationError(
                "Base workspaces path cannot be empty", config_key="base_workspaces_path"
            )

        # Prevent path traversal in configuration
        if ".." in v or v.startswith("/"):
            raise ConfigurationError(
                "Base workspaces path cannot contain '..' or start with '/'",
                config_key="base_workspaces_path",
            )

        return v.strip()

    @model_validator(mode="after")
    def validate_google_configuration(self) -> "Settings":
        """Validate Google Gemini configuration requirements."""
        if self.llm_provider == LLMProvider.GOOGLE_GEMINI:
            # Project ID is always required for Google Gemini
            if not self.google_project_id:
                raise ValueError("google_project_id is required when using google_gemini provider")

            # API key is only required when not using Vertex AI
            if not self.google_cloud_use_vertex_ai and not self.google_api_key:
                raise ValueError(
                    "google_api_key is required when using google_gemini provider without Vertex AI"
                )

        return self

    def is_ollama_provider(self) -> bool:
        """Check if Ollama provider is configured."""
        return self.llm_provider == LLMProvider.OLLAMA

    def is_google_gemini_provider(self) -> bool:
        """Check if Google Gemini provider is configured."""
        return self.llm_provider == LLMProvider.GOOGLE_GEMINI

    def is_vertex_ai_enabled(self) -> bool:
        """Check if Vertex AI is enabled for Google Gemini provider."""
        return self.is_google_gemini_provider() and self.google_cloud_use_vertex_ai

    def get_provider_info(self) -> dict[str, str | None | bool]:
        """Get current provider configuration info."""
        if self.is_ollama_provider():
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "llm_model": self.ollama_llm_model,
                "embedding_model": self.ollama_embedding_model,
            }
        elif self.is_google_gemini_provider():
            return {
                "provider": "google_gemini",
                "project_id": self.google_project_id,
                "location": self.google_location,
                "use_vertex_ai": self.google_cloud_use_vertex_ai,
                "vertex_ai_endpoint": self.vertex_ai_endpoint,
                "vertex_ai_location": self.vertex_ai_location,
                "llm_model": self.gemini_model,
                "embedding_model": self.gemini_embedding_model,
            }
        return {"provider": "unknown"}

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        """Validate overall security configuration."""
        # Check if we're in production mode (not debug)
        if not self.debug and not os.getenv("JWT_SECRET_KEY"):
            raise ValueError(
                "In production mode (debug=False), JWT_SECRET_KEY environment variable must be set"
            )

        # Additional production security validations can be added here

        return self


# API Configuration Constants
API_PREFIX = "/api"
GRAPHQL_PREFIX = "/graphql"

# Validation Constants
MAX_COMMUNITY_LEVEL = 4
MIN_MAX_TOKENS = 100

# Test Constants (for test environments)
TEST_API_KEY = "test_api_key"
TEST_PROJECT_ID = "test_project_id"
TEST_DATA_PATH = "/test/data"
TEST_CONFIG_PATH = "/test/config"

# Environment Variable Names
ENV_APP_NAME = "APP_NAME"
ENV_DEBUG = "DEBUG"
ENV_PORT = "PORT"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_GRAPHRAG_CONFIG_PATH = "GRAPHRAG_CONFIG_PATH"
ENV_GRAPHRAG_DATA_PATH = "GRAPHRAG_DATA_PATH"
ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_OLLAMA_BASE_URL = "OLLAMA_BASE_URL"
ENV_OLLAMA_LLM_MODEL = "OLLAMA_LLM_MODEL"
ENV_OLLAMA_EMBEDDING_MODEL = "OLLAMA_EMBEDDING_MODEL"
ENV_GOOGLE_API_KEY = "GOOGLE_API_KEY"
ENV_GOOGLE_PROJECT_ID = "GOOGLE_PROJECT_ID"
ENV_GEMINI_MODEL = "GEMINI_MODEL"
ENV_GOOGLE_LOCATION = "GOOGLE_LOCATION"
ENV_GOOGLE_CLOUD_USE_VERTEX_AI = "GOOGLE_CLOUD_USE_VERTEX_AI"
ENV_VERTEX_AI_ENDPOINT = "VERTEX_AI_ENDPOINT"
ENV_VERTEX_AI_LOCATION = "VERTEX_AI_LOCATION"

# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        The global settings instance
    """
    return settings


def generate_master_api_key() -> str:
    """Generate a secure master API key with proper format and entropy.

    Returns:
        str: A secure master API key with format 'grak_master_<random_string>'
    """
    # Generate 52 characters of random data (64 - 12 for prefix)
    random_part = secrets.token_urlsafe(39)  # 39 * 4/3 ≈ 52 chars
    return f"grak_master_{random_part}"


def validate_master_key_format(key: str) -> bool:
    """Validate master key format and security requirements.

    Args:
        key: Master key to validate

    Returns:
        bool: True if key meets all requirements
    """
    if not key or len(key) < 64:
        return False

    if not key.startswith("grak_master_"):
        return False

    if len(set(key)) < 16:  # Entropy check
        return False

    return True
