# tests/test_system_operations.py
# Tests for system management operations
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for system management operations and enhanced monitoring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.main import app
from src.graphrag_api_service.system.operations import SystemOperations, SystemOperationsError


class TestSystemOperations:
    """Test system operations functionality."""

    @pytest.fixture
    def settings(self, default_settings):
        """Create test settings."""
        default_settings.graphrag_data_path = "/test/data"
        return default_settings

    @pytest.fixture
    def mock_provider_factory(self):
        """Create mock provider factory."""
        factory = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(
            return_value=MagicMock(
                healthy=True,
                available_models=["model1", "model2"],
                error=None,
                metadata={"test": "data"},
                model_dump=lambda: {"healthy": True, "models": ["model1", "model2"]},
            )
        )
        mock_provider.get_configuration_info = MagicMock(
            return_value={"provider": "test", "models": ["model1"]}
        )
        factory.create_provider = MagicMock(return_value=mock_provider)
        return factory

    @pytest.fixture
    def system_operations(self, settings, mock_provider_factory):
        """Create system operations instance."""
        return SystemOperations(settings=settings, provider_factory=mock_provider_factory)

    @pytest.mark.asyncio
    async def test_switch_provider_success(self, system_operations):
        """Test successful provider switching."""
        result = await system_operations.switch_provider("google_gemini", validate_connection=True)

        assert result["success"] is True
        assert result["previous_provider"] == "ollama"
        assert result["current_provider"] == "google_gemini"
        assert "validation_result" in result
        assert system_operations.metrics["provider_switches"] == 1

    @pytest.mark.asyncio
    async def test_switch_provider_validation_failure(
        self, system_operations, mock_provider_factory
    ):
        """Test provider switch with validation failure."""
        # Mock unhealthy provider
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(
            return_value=MagicMock(
                healthy=False,
                error="Connection failed",
                model_dump=lambda: {"healthy": False, "error": "Connection failed"},
            )
        )
        mock_provider_factory.create_provider = MagicMock(return_value=mock_provider)

        with pytest.raises(SystemOperationsError, match="Provider validation failed"):
            await system_operations.switch_provider("google_gemini", validate_connection=True)

        # Provider should be rolled back
        assert system_operations.settings.llm_provider.value == "ollama"

    @pytest.mark.asyncio
    async def test_switch_provider_without_validation(self, system_operations):
        """Test provider switch without validation."""
        result = await system_operations.switch_provider("google_gemini", validate_connection=False)

        assert result["success"] is True
        assert result["validation_result"] is None
        assert system_operations.settings.llm_provider.value == "google_gemini"

    @pytest.mark.asyncio
    async def test_get_advanced_health(self, system_operations):
        """Test advanced health check."""
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.virtual_memory", return_value=MagicMock(percent=60.0)):
                with patch("psutil.disk_usage", return_value=MagicMock(percent=70.0)):
                    health = await system_operations.get_advanced_health()

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in health
        assert "components" in health
        assert "provider" in health
        assert health["provider"]["healthy"] is True
        assert "graphrag" in health
        assert "workspaces" in health
        assert "graph_data" in health
        assert "system_resources" in health
        assert health["system_resources"]["cpu_percent"] == 50.0
        assert health["system_resources"]["memory_percent"] == 60.0

    @pytest.mark.asyncio
    async def test_get_advanced_health_degraded(self, system_operations):
        """Test advanced health check with degraded status."""
        with patch("psutil.cpu_percent", return_value=95.0):
            with patch("psutil.virtual_memory", return_value=MagicMock(percent=60.0)):
                with patch("psutil.disk_usage", return_value=MagicMock(percent=70.0)):
                    health = await system_operations.get_advanced_health()

        assert health["status"] == "degraded"
        assert health["system_resources"]["cpu_percent"] == 95.0

    @pytest.mark.asyncio
    async def test_get_enhanced_status(self, system_operations):
        """Test enhanced status generation."""
        # Add some metrics
        system_operations.metrics["graph_queries"] = 10

        status = await system_operations.get_enhanced_status()

        assert status["version"] == "1.0.0"
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0
        assert "provider_info" in status
        assert "graph_metrics" in status
        assert "indexing_metrics" in status
        assert "total_jobs" in status["indexing_metrics"]
        assert "active_jobs" in status["indexing_metrics"]
        assert "queued_jobs" in status["indexing_metrics"]
        assert "workspace_metrics" in status
        assert "recent_operations" in status

    @pytest.mark.asyncio
    async def test_validate_configuration_provider(self, system_operations):
        """Test provider configuration validation."""
        result = await system_operations.validate_configuration("provider")

        assert "valid" in result
        assert result["config_type"] == "provider"
        assert "errors" in result
        assert "warnings" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_validate_configuration_invalid_provider(self, system_operations):
        """Test validation with invalid provider."""

        # Mock an invalid provider scenario by temporarily changing validation logic
        original_value = system_operations.settings.llm_provider
        # We'll test with None to simulate missing provider
        system_operations.settings.llm_provider = None
        result = await system_operations.validate_configuration("provider")
        system_operations.settings.llm_provider = original_value

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "No LLM provider configured" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_validate_configuration_graphrag(self, system_operations):
        """Test GraphRAG configuration validation."""
        result = await system_operations.validate_configuration("graphrag")

        assert result["config_type"] == "graphrag"
        # Should have warnings about missing config
        assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_validate_configuration_all(self, system_operations):
        """Test validation of all configuration types."""
        result = await system_operations.validate_configuration("all")

        assert result["config_type"] == "all"
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["suggestions"], list)

    @pytest.mark.asyncio
    async def test_validate_configuration_strict_mode(self, system_operations):
        """Test configuration validation in strict mode."""
        system_operations.settings.graphrag_data_path = None
        result = await system_operations.validate_configuration("graphrag", strict_mode=True)

        assert result["valid"] is False  # Warnings cause failure in strict mode

    def test_record_operation(self, system_operations):
        """Test operation recording."""
        system_operations._record_operation("test_op", {"key": "value"})

        assert len(system_operations.operation_history) == 1
        assert system_operations.operation_history[0]["type"] == "test_op"
        assert system_operations.operation_history[0]["details"]["key"] == "value"

    def test_update_metrics(self, system_operations):
        """Test metric updates."""
        system_operations.update_metrics("graph_queries", 5)
        assert system_operations.metrics["graph_queries"] == 5

        system_operations.update_metrics("graph_queries", 3)
        assert system_operations.metrics["graph_queries"] == 8


class TestSystemAPI:
    """Test system API endpoints."""

    def test_provider_switch_endpoint_unavailable(self):
        """Test provider switch when system operations unavailable."""
        client = TestClient(app)
        response = client.post(
            "/api/system/provider/switch",
            json={"provider": "google_gemini", "validate_connection": True},
        )

        # System operations may not be initialized in test
        assert response.status_code in [500, 503]

    def test_provider_switch_endpoint_success(self):
        """Test successful provider switch via API."""
        client = TestClient(app)
        response = client.post(
            "/api/system/provider/switch",
            json={"provider": "google_gemini", "validate_connection": True},
        )

        # With mock implementation, it returns success
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_advanced_health_endpoint(self):
        """Test advanced health check endpoint."""
        client = TestClient(app)
        response = client.get("/api/system/health/advanced")

        # With mock implementation, it returns health data
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_enhanced_status_endpoint(self):
        """Test enhanced status endpoint."""
        client = TestClient(app)
        response = client.get("/api/system/status/enhanced")

        # With mock implementation, it returns status data
        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    def test_config_validation_endpoint(self):
        """Test configuration validation endpoint."""
        client = TestClient(app)
        response = client.post(
            "/api/system/config/validate",
            json={"config_type": "provider", "strict_mode": False},
        )

        # With mock implementation, it returns validation data
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
