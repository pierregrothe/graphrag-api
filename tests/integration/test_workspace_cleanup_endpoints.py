# tests/integration/test_workspace_cleanup_endpoints.py
# Integration tests for workspace cleanup endpoints
# Author: Pierre Grothé
# Creation Date: 2025-09-04

"""Integration tests for workspace cleanup REST API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.main import create_app
from src.graphrag_api_service.workspace.models import Workspace, WorkspaceConfig, WorkspaceStatus


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_workspace():
    """Create sample workspace for testing."""
    config = WorkspaceConfig(
        name="test-cleanup-workspace",
        description="Test workspace for cleanup testing",
        data_path="/tmp/test-cleanup-data",
        output_path="/tmp/test-cleanup-output",
        llm_model_override=None,
        embedding_model_override=None,
    )

    workspace = Workspace(
        id="cleanup-test-workspace-id",
        config=config,
        status=WorkspaceStatus.INDEXED,
        created_at=datetime.now(UTC) - timedelta(hours=25),
        updated_at=datetime.now(UTC) - timedelta(hours=1),
        last_accessed_at=datetime.now(UTC) - timedelta(hours=13),
        access_count=10,
        query_count=5,
        indexing_count=2,
        size_bytes=50 * 1024 * 1024,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        last_error=None,
        workspace_path="/tmp/test-cleanup-workspace",
        config_file_path="/tmp/test-cleanup-workspace/settings.yaml",
    )

    workspace.set_expiration(24)
    return workspace


class TestWorkspaceCleanupEndpoints:
    """Test workspace cleanup REST API endpoints."""

    def test_force_cleanup_workspace_success(self, client, sample_workspace):
        """Test successful force cleanup of workspace."""
        workspace_id = sample_workspace.id

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()
            mock_cleanup_service.force_cleanup.return_value = True

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["workspace_id"] == workspace_id
            assert "cleaned up successfully" in data["message"]

            mock_cleanup_service.force_cleanup.assert_called_once_with(workspace_id)

    def test_force_cleanup_workspace_not_found(self, client):
        """Test force cleanup of nonexistent workspace."""
        workspace_id = "nonexistent-workspace"

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()
            mock_cleanup_service.force_cleanup.return_value = False

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")

            assert response.status_code == 404
            data = response.json()
            assert "not found or cleanup failed" in data.get("error", "")

    def test_force_cleanup_service_unavailable(self, client):
        """Test force cleanup when cleanup service is unavailable."""
        workspace_id = "test-workspace"

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container without cleanup service
            mock_container.return_value.workspace_cleanup_service = None

            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")

            assert response.status_code == 503
            data = response.json()
            assert "Workspace cleanup service not available" in data.get("error", "")

    def test_get_cleanup_stats_success(self, client):
        """Test successful retrieval of cleanup statistics."""
        expected_stats = {
            "total_cleanups": 5,
            "expired_cleaned": 3,
            "idle_cleaned": 2,
            "size_cleaned": 0,
            "errors": 0,
            "running": True,
            "last_cleanup": "2025-09-04T10:00:00Z",
            "settings": {
                "cleanup_enabled": True,
                "cleanup_interval_minutes": 60,
                "ttl_hours": 24,
                "max_idle_hours": 12,
                "max_size_mb": 1000,
                "grace_period_minutes": 30,
            },
        }

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()
            # get_stats is synchronous, so use a regular Mock
            mock_cleanup_service.get_stats = Mock(return_value=expected_stats)

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            response = client.get("/api/workspaces/cleanup/stats")

            assert response.status_code == 200
            data = response.json()
            assert data == expected_stats

            mock_cleanup_service.get_stats.assert_called_once()

    def test_get_cleanup_stats_service_unavailable(self, client):
        """Test cleanup stats when service is unavailable."""
        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container without cleanup service
            mock_container.return_value.workspace_cleanup_service = None

            response = client.get("/api/workspaces/cleanup/stats")

            assert response.status_code == 503
            data = response.json()
            assert "Workspace cleanup service not available" in data.get("error", "")

    def test_trigger_cleanup_cycle_success(self, client):
        """Test successful manual cleanup cycle trigger."""
        expected_stats = {
            "total_cleanups": 6,
            "expired_cleaned": 3,
            "idle_cleaned": 3,
            "size_cleaned": 0,
            "errors": 0,
            "running": True,
            "last_cleanup": "2025-09-04T10:30:00Z",
        }

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()
            mock_cleanup_service._perform_cleanup = AsyncMock()
            # get_stats is synchronous, so use a regular Mock
            mock_cleanup_service.get_stats = Mock(return_value=expected_stats)

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            response = client.post("/api/workspaces/cleanup/run")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Cleanup cycle completed successfully" in data["message"]
            assert data["stats"] == expected_stats

            mock_cleanup_service._perform_cleanup.assert_called_once()
            mock_cleanup_service.get_stats.assert_called_once()

    def test_trigger_cleanup_cycle_service_unavailable(self, client):
        """Test cleanup cycle trigger when service is unavailable."""
        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container without cleanup service
            mock_container.return_value.workspace_cleanup_service = None

            response = client.post("/api/workspaces/cleanup/run")

            assert response.status_code == 503
            data = response.json()
            assert "Workspace cleanup service not available" in data.get("error", "")

    def test_cleanup_endpoints_error_handling(self, client):
        """Test error handling in cleanup endpoints."""
        workspace_id = "test-workspace"

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container that raises an exception
            mock_container.side_effect = Exception("Service container error")

            # Test force cleanup error
            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")
            assert response.status_code == 500
            assert "Failed to cleanup workspace" in response.json().get("error", "")

            # Test stats error
            response = client.get("/api/workspaces/cleanup/stats")
            assert response.status_code == 500
            assert "Failed to get cleanup stats" in response.json().get("error", "")

            # Test cleanup cycle error
            response = client.post("/api/workspaces/cleanup/run")
            assert response.status_code == 500
            assert "Failed to trigger cleanup cycle" in response.json().get("error", "")

    def test_cleanup_endpoints_workspace_manager_unavailable(self, client):
        """Test cleanup endpoints when workspace manager is unavailable."""
        workspace_id = "test-workspace"

        with patch("src.graphrag_api_service.deps.get_workspace_manager", return_value=None):
            # Test force cleanup
            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")
            assert response.status_code == 503
            # The endpoint checks workspace manager first, but if that passes, it checks cleanup service
            # Since we're not mocking the service container, it will fail at cleanup service check
            assert "not available" in response.json().get("error", "")

            # Test stats
            response = client.get("/api/workspaces/cleanup/stats")
            assert response.status_code == 503
            assert "not available" in response.json().get("error", "")

            # Test cleanup cycle
            response = client.post("/api/workspaces/cleanup/run")
            assert response.status_code == 503
            assert "not available" in response.json().get("error", "")


class TestWorkspaceCleanupIntegration:
    """Test workspace cleanup integration scenarios."""

    def test_cleanup_workflow_integration(self, client, sample_workspace):
        """Test complete cleanup workflow integration."""
        workspace_id = sample_workspace.id

        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()

            # Initial stats
            initial_stats = {
                "total_cleanups": 0,
                "expired_cleaned": 0,
                "idle_cleaned": 0,
                "size_cleaned": 0,
                "errors": 0,
                "running": True,
            }

            # Updated stats after cleanup
            updated_stats = {
                "total_cleanups": 1,
                "expired_cleaned": 1,
                "idle_cleaned": 0,
                "size_cleaned": 0,
                "errors": 0,
                "running": True,
            }

            # get_stats is synchronous, so use a regular Mock with side_effect
            # Provide enough values for all the calls in the test (4 calls total)
            mock_cleanup_service.get_stats = Mock(
                side_effect=[initial_stats, updated_stats, updated_stats, updated_stats]
            )
            mock_cleanup_service.force_cleanup.return_value = True
            mock_cleanup_service._perform_cleanup = AsyncMock()

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            # 1. Get initial stats
            response = client.get("/api/workspaces/cleanup/stats")
            assert response.status_code == 200
            assert response.json()["total_cleanups"] == 0

            # 2. Force cleanup specific workspace
            response = client.post(f"/api/workspaces/{workspace_id}/cleanup")
            assert response.status_code == 200
            assert response.json()["success"] is True

            # 3. Trigger manual cleanup cycle
            response = client.post("/api/workspaces/cleanup/run")
            assert response.status_code == 200
            assert response.json()["success"] is True

            # 4. Get updated stats
            response = client.get("/api/workspaces/cleanup/stats")
            assert response.status_code == 200
            assert response.json()["total_cleanups"] == 1

            # Verify all service methods were called
            assert mock_cleanup_service.get_stats.call_count == 3  # Initial + after cycle + final
            mock_cleanup_service.force_cleanup.assert_called_once_with(workspace_id)
            mock_cleanup_service._perform_cleanup.assert_called_once()

    def test_cleanup_service_lifecycle(self, client):
        """Test cleanup service lifecycle through API."""
        with patch("src.graphrag_api_service.dependencies.get_service_container") as mock_container:
            # Mock service container and cleanup service
            mock_cleanup_service = AsyncMock()
            # get_stats is synchronous, so use a regular Mock
            mock_cleanup_service.get_stats = Mock(
                return_value={
                    "running": True,
                    "total_cleanups": 0,
                    "settings": {
                        "cleanup_enabled": True,
                        "cleanup_interval_minutes": 60,
                    },
                }
            )

            mock_container.return_value.workspace_cleanup_service = mock_cleanup_service

            # Check service is running
            response = client.get("/api/workspaces/cleanup/stats")
            assert response.status_code == 200
            stats = response.json()
            assert stats["running"] is True
            assert stats["settings"]["cleanup_enabled"] is True
