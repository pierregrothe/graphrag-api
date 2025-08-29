# tests/test_deployment_config.py
# Tests for Deployment Configuration Components
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for deployment configuration management and validation."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.graphrag_api_service.deployment.config import (
    DeploymentSettings,
    ConfigManager,
    DatabaseConfig,
    SecurityConfig,
    PerformanceConfig,
)
from pydantic_settings import SettingsConfigDict


class TestDeploymentSettings:
    """Test cases for deployment settings."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_settings(self):
        """Test default deployment settings."""
        # Create a settings class that doesn't load from .env file
        class TestDeploymentSettings(DeploymentSettings):
            model_config = SettingsConfigDict(
                env_file=None,
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore"
            )

        settings = TestDeploymentSettings()

        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.app_name == "GraphRAG API"

    @patch.dict(os.environ, {}, clear=True)
    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments should work
        for env in ["development", "staging", "production"]:
            with patch.dict(os.environ, {"ENVIRONMENT": env}, clear=True):
                settings = DeploymentSettings()
                assert settings.environment == env

        # Invalid environment should raise error
        with pytest.raises(ValueError):
            with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}, clear=True):
                DeploymentSettings()

    @patch.dict(os.environ, {}, clear=True)
    def test_environment_detection_methods(self):
        """Test environment detection methods."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            dev_settings = DeploymentSettings()
            assert dev_settings.is_development() is True
            assert dev_settings.is_production() is False

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            prod_settings = DeploymentSettings()
            assert prod_settings.is_development() is False
            assert prod_settings.is_production() is True

    def test_database_url_generation(self):
        """Test database URL generation."""
        settings = DeploymentSettings()
        settings.database.username = "testuser"
        settings.database.password = "testpass"
        settings.database.host = "localhost"
        settings.database.port = 5432
        settings.database.database = "testdb"
        
        url = settings.get_database_url()
        expected = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert url == expected

    def test_redis_url_generation(self):
        """Test Redis URL generation."""
        settings = DeploymentSettings()
        settings.redis.host = "localhost"
        settings.redis.port = 6379
        settings.redis.database = 0
        settings.redis.password = "testpass"
        
        url = settings.get_redis_url()
        expected = "redis://:testpass@localhost:6379/0"
        assert url == expected

        # Test without password
        settings.redis.password = None
        url = settings.get_redis_url()
        expected = "redis://localhost:6379/0"
        assert url == expected

    @patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "HOST": "0.0.0.0",
        "PORT": "8080",
        "SECRET_KEY": "test-secret-key",
        "DB_PASSWORD": "db-password",
    })
    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        settings = DeploymentSettings()
        
        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.security.secret_key == "test-secret-key"
        assert settings.database.password == "db-password"


class TestConfigManager:
    """Test cases for configuration manager."""

    @pytest.fixture
    def config_manager(self):
        """Create a configuration manager for testing."""
        return ConfigManager()

    def test_settings_loading(self, config_manager):
        """Test settings loading."""
        settings = config_manager.load_settings()
        assert isinstance(settings, DeploymentSettings)

    def test_settings_caching(self, config_manager):
        """Test that settings are cached."""
        settings1 = config_manager.load_settings()
        settings2 = config_manager.load_settings()
        assert settings1 is settings2

    def test_production_config_validation_success(self, config_manager):
        """Test successful production configuration validation."""
        settings = DeploymentSettings(
            environment="production",
            debug=False,
        )
        settings.security.secret_key = "secure-production-key"
        settings.security.cors_origins = ["https://example.com"]
        settings.performance.max_workers = 4
        settings.database.host = "prod-db-host"
        settings.monitoring.metrics_enabled = True
        
        errors = config_manager.validate_production_config(settings)
        assert len(errors) == 0

    @patch.dict(os.environ, {}, clear=True)
    def test_production_config_validation_failures(self, config_manager):
        """Test production configuration validation failures."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "SECRET_KEY": "your-secret-key-here"
        }, clear=True):
            settings = DeploymentSettings()
            settings.security.cors_origins = ["*"]  # Too permissive
            settings.performance.max_workers = 1  # Too few workers
            settings.database.host = "localhost"  # Should not be localhost
            settings.monitoring.metrics_enabled = False  # Should be enabled

            errors = config_manager.validate_production_config(settings)
            assert len(errors) > 0
            assert any("debug" in error.lower() for error in errors)
            assert any("secret" in error.lower() for error in errors)
            assert any("cors" in error.lower() for error in errors)

    @patch.dict(os.environ, {}, clear=True)
    def test_gunicorn_config_generation(self, config_manager):
        """Test Gunicorn configuration generation."""
        with patch.dict(os.environ, {
            "HOST": "127.0.0.1",
            "PORT": "8080"
        }, clear=True):
            settings = DeploymentSettings()
            settings.performance.max_workers = 4
            settings.performance.worker_timeout = 300

            gunicorn_config = config_manager.get_gunicorn_config(settings)

            assert gunicorn_config["bind"] == "127.0.0.1:8080"
            assert gunicorn_config["workers"] == 4
            assert gunicorn_config["timeout"] == 300
            assert gunicorn_config["worker_class"] == "uvicorn.workers.UvicornWorker"

    def test_docker_compose_generation(self, config_manager):
        """Test Docker Compose configuration generation."""
        settings = DeploymentSettings(
            environment="production",
            port=8000,
        )
        
        compose_config = config_manager.generate_docker_compose(settings)
        
        assert "version: '3.8'" in compose_config
        assert "graphrag-api:" in compose_config
        assert "postgres:" in compose_config
        assert "redis:" in compose_config
        assert "nginx:" in compose_config
        assert f"- \"{settings.port}:{settings.port}\"" in compose_config

    def test_nginx_config_generation(self, config_manager):
        """Test Nginx configuration generation."""
        settings = DeploymentSettings(port=8000)
        
        nginx_config = config_manager.generate_nginx_config(settings)
        
        assert "upstream graphrag_api" in nginx_config
        assert f"server graphrag-api:{settings.port}" in nginx_config
        assert "listen 80" in nginx_config
        assert "listen 443 ssl" in nginx_config
        assert "gzip on" in nginx_config


class TestComponentConfigs:
    """Test cases for individual component configurations."""

    def test_database_config(self):
        """Test database configuration."""
        config = DatabaseConfig(
            host="db-host",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            pool_size=20,
        )
        
        assert config.host == "db-host"
        assert config.port == 5432
        assert config.pool_size == 20

    def test_security_config(self):
        """Test security configuration."""
        config = SecurityConfig(
            secret_key="test-key",
            jwt_algorithm="HS256",
            cors_origins=["https://example.com"],
            rate_limit_per_minute=200,
        )
        
        assert config.secret_key == "test-key"
        assert config.jwt_algorithm == "HS256"
        assert config.rate_limit_per_minute == 200

    def test_performance_config(self):
        """Test performance configuration."""
        config = PerformanceConfig(
            max_workers=8,
            worker_timeout=600,
            max_memory_usage_percent=85.0,
            cache_size_mb=1024,
        )
        
        assert config.max_workers == 8
        assert config.worker_timeout == 600
        assert config.max_memory_usage_percent == 85.0
        assert config.cache_size_mb == 1024


class TestConfigFileLoading:
    """Test cases for configuration file loading."""

    def test_config_file_loading(self):
        """Test loading configuration from file."""
        # Create a temporary config file
        config_content = """
ENVIRONMENT=staging
DEBUG=false
HOST=0.0.0.0
PORT=9000
SECRET_KEY=file-secret-key
DB_PASSWORD=file-db-password
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            settings = config_manager.load_settings()
            
            assert settings.environment == "staging"
            assert settings.debug is False
            assert settings.port == 9000
            assert settings.security.secret_key == "file-secret-key"
            assert settings.database.password == "file-db-password"
            
        finally:
            os.unlink(config_file)

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        config_manager = ConfigManager("nonexistent.env")
        settings = config_manager.load_settings()
        
        # Should fall back to environment variables and defaults
        assert isinstance(settings, DeploymentSettings)

    @patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "env-secret-key",
    })
    def test_environment_override(self):
        """Test that environment variables override file settings."""
        config_content = """
ENVIRONMENT=development
SECRET_KEY=file-secret-key
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            settings = config_manager.load_settings()
            
            # Environment variables should take precedence
            assert settings.environment == "production"
            assert settings.security.secret_key == "env-secret-key"
            
        finally:
            os.unlink(config_file)
