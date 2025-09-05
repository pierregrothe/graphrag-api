# tests/unit/test_workspace_lifecycle.py
# Unit tests for workspace lifecycle management
# Author: Pierre Grothé
# Creation Date: 2025-09-04

"""Unit tests for workspace lifecycle management and cleanup."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.workspace.cleanup import WorkspaceCleanupService
from src.graphrag_api_service.workspace.models import (
    Workspace,
    WorkspaceConfig,
    WorkspaceStatus,
)


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        workspace_cleanup_enabled=True,
        workspace_cleanup_interval_minutes=1,
        workspace_ttl_hours=24,
        workspace_max_idle_hours=12,
        workspace_grace_period_minutes=30,
        workspace_max_size_mb=100,
        workspace_usage_tracking_enabled=True,
    )


@pytest.fixture
def mock_workspace_manager():
    """Create mock workspace manager."""
    manager = AsyncMock()
    manager.list_workspaces = AsyncMock()
    manager.get_workspace = AsyncMock()
    manager.update_workspace = AsyncMock()
    manager.delete_workspace = AsyncMock()
    return manager


@pytest.fixture
def sample_workspace():
    """Create sample workspace for testing."""
    config = WorkspaceConfig(
        name="test-workspace",
        description="Test workspace for lifecycle testing",
        data_path="/tmp/test-data",
        output_path="/tmp/test-output",
        llm_model_override=None,
        embedding_model_override=None,
    )

    workspace = Workspace(
        id="test-workspace-id",
        config=config,
        status=WorkspaceStatus.INDEXED,
        created_at=datetime.now(UTC) - timedelta(hours=25),  # Expired
        updated_at=datetime.now(UTC) - timedelta(hours=1),
        last_accessed_at=datetime.now(UTC) - timedelta(hours=13),  # Idle
        access_count=10,
        query_count=5,
        indexing_count=2,
        size_bytes=50 * 1024 * 1024,  # 50MB
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        last_error=None,
        workspace_path="/tmp/test-workspace",
        config_file_path="/tmp/test-workspace/settings.yaml",
    )

    # Set expiration
    workspace.set_expiration(24)

    return workspace


@pytest.fixture
def cleanup_service(settings, mock_workspace_manager):
    """Create cleanup service for testing."""
    return WorkspaceCleanupService(settings, mock_workspace_manager)


class TestWorkspaceModel:
    """Test workspace model lifecycle methods."""

    def test_update_access(self, sample_workspace):
        """Test access tracking update."""
        original_count = sample_workspace.access_count
        original_time = sample_workspace.last_accessed_at

        sample_workspace.update_access()

        assert sample_workspace.access_count == original_count + 1
        assert sample_workspace.last_accessed_at > original_time

    def test_update_query_count(self, sample_workspace):
        """Test query count update."""
        original_query_count = sample_workspace.query_count
        original_access_count = sample_workspace.access_count

        sample_workspace.update_query_count()

        assert sample_workspace.query_count == original_query_count + 1
        assert sample_workspace.access_count == original_access_count + 1

    def test_update_indexing_count(self, sample_workspace):
        """Test indexing count update."""
        original_indexing_count = sample_workspace.indexing_count
        original_access_count = sample_workspace.access_count

        sample_workspace.update_indexing_count()

        assert sample_workspace.indexing_count == original_indexing_count + 1
        assert sample_workspace.access_count == original_access_count + 1

    def test_set_expiration(self, sample_workspace):
        """Test expiration setting."""
        # Test setting TTL
        sample_workspace.set_expiration(48)
        assert sample_workspace.expires_at is not None
        assert sample_workspace.expires_at > datetime.now(UTC)

        # Test disabling TTL
        sample_workspace.set_expiration(0)
        assert sample_workspace.expires_at is None

    def test_is_expired(self, sample_workspace):
        """Test expiration checking."""
        # Test expired workspace
        sample_workspace.expires_at = datetime.now(UTC) - timedelta(hours=1)
        assert sample_workspace.is_expired() is True

        # Test non-expired workspace
        sample_workspace.expires_at = datetime.now(UTC) + timedelta(hours=1)
        assert sample_workspace.is_expired() is False

        # Test workspace without expiration
        sample_workspace.expires_at = None
        assert sample_workspace.is_expired() is False

    def test_is_idle(self, sample_workspace):
        """Test idle checking."""
        # Test idle workspace
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(hours=13)
        assert sample_workspace.is_idle(12) is True

        # Test active workspace
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(hours=1)
        assert sample_workspace.is_idle(12) is False

        # Test disabled idle checking
        assert sample_workspace.is_idle(0) is False


class TestWorkspaceCleanupService:
    """Test workspace cleanup service."""

    @pytest.mark.asyncio
    async def test_start_stop_service(self, cleanup_service):
        """Test starting and stopping cleanup service."""
        assert cleanup_service._running is False

        await cleanup_service.start()
        assert cleanup_service._running is True
        assert cleanup_service._cleanup_task is not None

        await cleanup_service.stop()
        assert cleanup_service._running is False

    @pytest.mark.asyncio
    async def test_disabled_cleanup(self, mock_workspace_manager):
        """Test cleanup service when disabled."""
        settings = Settings(workspace_cleanup_enabled=False)
        service = WorkspaceCleanupService(settings, mock_workspace_manager)

        await service.start()
        assert service._running is False
        assert service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_should_cleanup_expired_workspace(self, cleanup_service, sample_workspace):
        """Test cleanup decision for expired workspace."""
        # Make workspace expired
        sample_workspace.expires_at = datetime.now(UTC) - timedelta(hours=1)

        should_cleanup = await cleanup_service._should_cleanup_workspace(sample_workspace)
        assert should_cleanup is True

    @pytest.mark.asyncio
    async def test_should_cleanup_idle_workspace(self, cleanup_service, sample_workspace):
        """Test cleanup decision for idle workspace."""
        # Make workspace idle but not expired
        sample_workspace.expires_at = datetime.now(UTC) + timedelta(hours=1)
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(hours=13)

        should_cleanup = await cleanup_service._should_cleanup_workspace(sample_workspace)
        assert should_cleanup is True

    @pytest.mark.asyncio
    async def test_should_not_cleanup_active_workspace(self, cleanup_service, sample_workspace):
        """Test cleanup decision for active workspace."""
        # Make workspace active and not expired
        sample_workspace.expires_at = datetime.now(UTC) + timedelta(hours=1)
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(minutes=5)

        should_cleanup = await cleanup_service._should_cleanup_workspace(sample_workspace)
        assert should_cleanup is False

    @pytest.mark.asyncio
    async def test_should_not_cleanup_indexing_workspace(self, cleanup_service, sample_workspace):
        """Test cleanup decision for workspace being indexed."""
        # Make workspace expired but currently indexing
        sample_workspace.expires_at = datetime.now(UTC) - timedelta(hours=1)
        sample_workspace.status = WorkspaceStatus.INDEXING

        should_cleanup = await cleanup_service._should_cleanup_workspace(sample_workspace)
        assert should_cleanup is False

    @pytest.mark.asyncio
    async def test_force_cleanup(self, cleanup_service, mock_workspace_manager, sample_workspace):
        """Test force cleanup of specific workspace."""
        mock_workspace_manager.get_workspace.return_value = sample_workspace

        with patch.object(
            cleanup_service, "_cleanup_workspace", new_callable=AsyncMock
        ) as mock_cleanup:
            result = await cleanup_service.force_cleanup("test-workspace-id")

            assert result is True
            mock_workspace_manager.get_workspace.assert_called_once_with("test-workspace-id")
            mock_cleanup.assert_called_once_with(sample_workspace)

    @pytest.mark.asyncio
    async def test_force_cleanup_nonexistent_workspace(
        self, cleanup_service, mock_workspace_manager
    ):
        """Test force cleanup of nonexistent workspace."""
        mock_workspace_manager.get_workspace.return_value = None

        result = await cleanup_service.force_cleanup("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_workspace_success(
        self, cleanup_service, mock_workspace_manager, sample_workspace
    ):
        """Test successful workspace cleanup."""
        workspace_path = Path("/tmp/test-workspace")

        with (
            patch(
                "src.graphrag_api_service.workspace.models.Workspace.get_workspace_directory",
                return_value=workspace_path,
            ),
            patch.object(cleanup_service, "_calculate_directory_size", return_value=1024),
            patch("shutil.rmtree") as mock_rmtree,
            patch("pathlib.Path.exists", return_value=True),
        ):

            await cleanup_service._cleanup_workspace(sample_workspace)

            # Verify workspace was archived
            assert sample_workspace.status == WorkspaceStatus.ARCHIVED
            mock_workspace_manager.update_workspace.assert_called_once()

            # Verify directory was removed
            mock_rmtree.assert_called_once_with(workspace_path)

            # Verify workspace was deleted from manager
            mock_workspace_manager.delete_workspace.assert_called_once_with(sample_workspace.id)

    def test_get_stats(self, cleanup_service):
        """Test getting cleanup service statistics."""
        stats = cleanup_service.get_stats()

        assert isinstance(stats, dict)
        assert "total_cleanups" in stats
        assert "expired_cleaned" in stats
        assert "idle_cleaned" in stats
        assert "size_cleaned" in stats
        assert "errors" in stats
        assert "running" in stats
        assert "settings" in stats

        # Check settings are included
        settings = stats["settings"]
        assert "cleanup_enabled" in settings
        assert "cleanup_interval_minutes" in settings
        assert "ttl_hours" in settings

    @pytest.mark.asyncio
    async def test_has_active_operations_recent_access(self, cleanup_service, sample_workspace):
        """Test active operations detection with recent access."""
        # Set recent access within grace period
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(minutes=15)

        has_active = await cleanup_service._has_active_operations(sample_workspace)
        assert has_active is True

    @pytest.mark.asyncio
    async def test_has_active_operations_old_access(self, cleanup_service, sample_workspace):
        """Test active operations detection with old access."""
        # Set old access outside grace period
        sample_workspace.last_accessed_at = datetime.now(UTC) - timedelta(hours=2)

        has_active = await cleanup_service._has_active_operations(sample_workspace)
        assert has_active is False

    def test_calculate_directory_size(self, cleanup_service):
        """Test directory size calculation."""
        with patch("pathlib.Path.exists", return_value=False):
            size = cleanup_service._calculate_directory_size(Path("/nonexistent"))
            assert size == 0

    @pytest.mark.asyncio
    async def test_perform_cleanup_cycle(
        self, cleanup_service, mock_workspace_manager, sample_workspace
    ):
        """Test full cleanup cycle."""
        # Setup mock workspaces
        expired_workspace = sample_workspace
        expired_workspace.expires_at = datetime.now(UTC) - timedelta(hours=1)

        active_workspace = Workspace(
            id="active-workspace",
            config=WorkspaceConfig(
                name="active",
                description="Active workspace",
                data_path="/tmp/active-data",
                output_path="/tmp/active-output",
                llm_model_override=None,
                embedding_model_override=None,
            ),
            status=WorkspaceStatus.INDEXED,
            last_accessed_at=datetime.now(UTC) - timedelta(minutes=5),
            expires_at=None,
            last_error=None,
            workspace_path="/tmp/active-workspace",
            config_file_path="/tmp/active-workspace/settings.yaml",
        )
        active_workspace.set_expiration(24)

        mock_workspace_manager.list_workspaces.return_value = [expired_workspace, active_workspace]

        with patch.object(
            cleanup_service, "_cleanup_workspace", new_callable=AsyncMock
        ) as mock_cleanup:
            await cleanup_service._perform_cleanup()

            # Should only cleanup expired workspace
            mock_cleanup.assert_called_once_with(expired_workspace)
            assert cleanup_service._stats["total_cleanups"] == 1
