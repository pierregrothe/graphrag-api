# src/graphrag_api_service/deployment/config.py
# Production Deployment Configuration Management
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Production deployment configuration with environment management and validation."""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    database: str = "graphrag"
    username: str = "graphrag_user"
    password: str = Field("", alias="DB_PASSWORD")
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    ssl_mode: str = "prefer"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # Allow both field name and alias
    )


class RedisConfig(BaseSettings):
    """Redis configuration for caching."""

    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: str | None = Field(None, alias="REDIS_PASSWORD")
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class SecurityConfig(BaseSettings):
    """Security configuration."""

    secret_key: str = Field("default-secret-key", alias="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )
    cors_origins: list[str] = ["*"]
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    rate_limit_per_minute: int = 100
    max_request_size_mb: int = 10


class PerformanceConfig(BaseSettings):
    """Performance configuration."""

    max_workers: int = 4
    worker_timeout: int = 300
    keepalive: int = 2
    max_requests: int = 1000
    max_requests_jitter: int = 100
    preload_app: bool = True

    # Memory settings
    max_memory_usage_percent: float = 80.0
    cache_size_mb: int = 512
    chunk_size: int = 10000

    # Connection pooling
    db_pool_size: int = 10
    db_max_overflow: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str | None = None
    max_file_size_mb: int = 100
    backup_count: int = 5
    json_format: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""

    metrics_enabled: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    performance_monitoring: bool = True
    audit_logging: bool = True

    # Alerting thresholds
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    response_time_threshold: float = 5.0
    error_rate_threshold: float = 0.05

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


class DeploymentSettings(BaseSettings):
    """Main deployment settings with environment variable support."""

    # Environment
    environment: str = Field("development", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")

    # Application
    app_name: str = "GraphRAG API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    # Data paths
    data_path: str = Field("./data", alias="DATA_PATH")
    workspace_path: str = Field("./workspaces", alias="WORKSPACE_PATH")

    # Component configurations
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig())  # type: ignore
    redis: RedisConfig = Field(default_factory=lambda: RedisConfig())  # type: ignore
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig())  # type: ignore
    performance: PerformanceConfig = Field(default_factory=lambda: PerformanceConfig())
    logging: LoggingConfig = Field(default_factory=lambda: LoggingConfig())
    monitoring: MonitoringConfig = Field(default_factory=lambda: MonitoringConfig())

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    def __init__(self, **kwargs):
        """Initialize with environment variable support for nested configs."""
        # Create nested configs with current environment variables
        if "database" not in kwargs:
            kwargs["database"] = DatabaseConfig()  # type: ignore
        if "redis" not in kwargs:
            kwargs["redis"] = RedisConfig()  # type: ignore
        if "security" not in kwargs:
            kwargs["security"] = SecurityConfig()  # type: ignore
        if "performance" not in kwargs:
            kwargs["performance"] = PerformanceConfig()
        if "logging" not in kwargs:
            kwargs["logging"] = LoggingConfig()
        if "monitoring" not in kwargs:
            kwargs["monitoring"] = MonitoringConfig()

        super().__init__(**kwargs)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_environments = ["development", "staging", "production"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v

    @field_validator("data_path", "workspace_path")
    @classmethod
    def validate_paths(cls, v):
        """Validate and create paths if they don't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_database_url(self) -> str:
        """Get database connection URL."""
        return (
            f"postgresql://{self.database.username}:{self.database.password}"
            f"@{self.database.host}:{self.database.port}/{self.database.database}"
        )

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.redis.password}@" if self.redis.password else ""
        return f"redis://{auth}{self.redis.host}:{self.redis.port}/{self.redis.database}"


class ConfigManager:
    """Configuration manager for deployment settings."""

    def __init__(self, config_file: str | None = None):
        """Initialize the configuration manager.

        Args:
            config_file: Optional configuration file path
        """
        self.config_file = config_file
        self._settings: DeploymentSettings | None = None

    def load_settings(self) -> DeploymentSettings:
        """Load deployment settings.

        Returns:
            Deployment settings
        """
        if self._settings is None:
            if self.config_file and os.path.exists(self.config_file):
                # Load from file by temporarily setting the env_file in all Config classes
                config_file_path = self.config_file  # Capture in local variable for closure

                class DatabaseConfigWithFile(DatabaseConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class RedisConfigWithFile(RedisConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class SecurityConfigWithFile(SecurityConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class PerformanceConfigWithFile(PerformanceConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class LoggingConfigWithFile(LoggingConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class MonitoringConfigWithFile(MonitoringConfig):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                        populate_by_name=True,
                    )

                class ConfigWithFile(DeploymentSettings):
                    model_config = SettingsConfigDict(
                        env_file=config_file_path,
                        env_file_encoding="utf-8",
                        case_sensitive=False,
                        extra="ignore",
                    )

                    def __init__(self, **kwargs):
                        """Initialize with file-based nested configs."""
                        # Create nested configs with file-based configuration
                        if "database" not in kwargs:
                            kwargs["database"] = DatabaseConfigWithFile()  # type: ignore
                        if "redis" not in kwargs:
                            kwargs["redis"] = RedisConfigWithFile()  # type: ignore
                        if "security" not in kwargs:
                            kwargs["security"] = SecurityConfigWithFile()  # type: ignore
                        if "performance" not in kwargs:
                            kwargs["performance"] = PerformanceConfigWithFile()
                        if "logging" not in kwargs:
                            kwargs["logging"] = LoggingConfigWithFile()
                        if "monitoring" not in kwargs:
                            kwargs["monitoring"] = MonitoringConfigWithFile()

                        super().__init__(**kwargs)

                self._settings = ConfigWithFile()
            else:
                # Load from environment
                self._settings = DeploymentSettings()

            logger.info(f"Configuration loaded for environment: {self._settings.environment}")

        return self._settings

    def validate_production_config(self, settings: DeploymentSettings) -> list[str]:
        """Validate production configuration.

        Args:
            settings: Deployment settings

        Returns:
            List of validation errors
        """
        errors = []

        if settings.is_production():
            # Security validations
            if settings.debug:
                errors.append("Debug mode must be disabled in production")

            if settings.security.secret_key == "your-secret-key-here":
                errors.append("Secret key must be changed from default value")

            if "*" in settings.security.cors_origins:
                errors.append("CORS origins should be restricted in production")

            # Performance validations
            if settings.performance.max_workers < 2:
                errors.append("At least 2 workers recommended for production")

            # Database validations
            if settings.database.host == "localhost":
                errors.append("Database host should not be localhost in production")

            # Monitoring validations
            if not settings.monitoring.metrics_enabled:
                errors.append("Metrics should be enabled in production")

        return errors

    def get_gunicorn_config(self, settings: DeploymentSettings) -> dict[str, Any]:
        """Get Gunicorn configuration.

        Args:
            settings: Deployment settings

        Returns:
            Gunicorn configuration
        """
        return {
            "bind": f"{settings.host}:{settings.port}",
            "workers": settings.performance.max_workers,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "worker_connections": 1000,
            "timeout": settings.performance.worker_timeout,
            "keepalive": settings.performance.keepalive,
            "max_requests": settings.performance.max_requests,
            "max_requests_jitter": settings.performance.max_requests_jitter,
            "preload_app": settings.performance.preload_app,
            "access_log": "-",
            "error_log": "-",
            "log_level": settings.logging.level.lower(),
        }

    def generate_docker_compose(self, settings: DeploymentSettings) -> str:
        """Generate Docker Compose configuration.

        Args:
            settings: Deployment settings

        Returns:
            Docker Compose YAML content
        """
        compose_config = f"""version: '3.8'

services:
  graphrag-api:
    build: .
    ports:
      - "{settings.port}:{settings.port}"
    environment:
      - ENVIRONMENT={settings.environment}
      - HOST={settings.host}
      - PORT={settings.port}
      - DEBUG={str(settings.debug).lower()}
      - DATA_PATH={settings.data_path}
      - WORKSPACE_PATH={settings.workspace_path}
      - DB_PASSWORD=${{DB_PASSWORD}}
      - REDIS_PASSWORD=${{REDIS_PASSWORD}}
      - SECRET_KEY=${{SECRET_KEY}}
    volumes:
      - ./data:{settings.data_path}
      - ./workspaces:{settings.workspace_path}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB={settings.database.database}
      - POSTGRES_USER={settings.database.username}
      - POSTGRES_PASSWORD=${{DB_PASSWORD}}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "{settings.database.port}:{settings.database.port}"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${{REDIS_PASSWORD}}
    ports:
      - "{settings.redis.port}:{settings.redis.port}"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - graphrag-api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
"""
        return compose_config

    def generate_nginx_config(self, settings: DeploymentSettings) -> str:
        """Generate Nginx configuration.

        Args:
            settings: Deployment settings

        Returns:
            Nginx configuration content
        """
        return f"""events {{
    worker_connections 1024;
}}

http {{
    upstream graphrag_api {{
        server graphrag-api:{settings.port};
    }}

    server {{
        listen 80;
        server_name _;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }}

    server {{
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Compression
        gzip on;
        gzip_types text/plain application/json application/javascript text/css;

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

        location / {{
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://graphrag_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }}
    }}
}}
"""


# Global configuration manager
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager.

    Returns:
        Configuration manager instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager


def get_settings() -> DeploymentSettings:
    """Get deployment settings.

    Returns:
        Deployment settings
    """
    return get_config_manager().load_settings()
