# src/graphrag_api_service/workspace/cleanup.py
# Workspace cleanup service for automatic lifecycle management
# Author: Pierre Grothé
# Creation Date: 2025-09-04

"""Background service for automatic workspace cleanup and lifecycle management."""

import asyncio
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ..config import Settings
from ..logging_config import get_logger
from .models import Workspace, WorkspaceStatus

logger = get_logger(__name__)


class WorkspaceCleanupService:
    """Background service for automatic workspace cleanup."""

    def __init__(self, settings: Settings, workspace_manager: Any) -> None:
        """Initialize the cleanup service.

        Args:
            settings: Application settings
            workspace_manager: Workspace manager instance
        """
        self.settings = settings
        self.workspace_manager = workspace_manager
        self._cleanup_task: asyncio.Task | None = None
        self._running = False
        self._stats: dict[str, int | str | None] = {
            "total_cleanups": 0,
            "expired_cleaned": 0,
            "idle_cleaned": 0,
            "size_cleaned": 0,
            "errors": 0,
            "last_cleanup": None,
        }

    async def start(self) -> None:
        """Start the background cleanup service."""
        if not self.settings.workspace_cleanup_enabled:
            logger.info("Workspace cleanup is disabled")
            return

        if self._running:
            logger.warning("Cleanup service is already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Workspace cleanup service started with {self.settings.workspace_cleanup_interval_minutes}min interval"
        )

    async def stop(self) -> None:
        """Stop the background cleanup service."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Workspace cleanup service stopped")

    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while self._running:
            try:
                await self._perform_cleanup()
                self._stats["last_cleanup"] = datetime.now(UTC).isoformat()
            except Exception as e:
                logger.error(f"Error during workspace cleanup: {e}")
                self._stats["errors"] = cast(int, self._stats["errors"]) + 1

            # Wait for next cleanup interval
            await asyncio.sleep(self.settings.workspace_cleanup_interval_minutes * 60)

    async def _perform_cleanup(self) -> None:
        """Perform workspace cleanup based on policies."""
        logger.debug("Starting workspace cleanup cycle")

        try:
            workspaces = await self.workspace_manager.list_workspaces()
            cleanup_candidates = []

            for workspace in workspaces:
                if await self._should_cleanup_workspace(workspace):
                    cleanup_candidates.append(workspace)

            if cleanup_candidates:
                logger.info(f"Found {len(cleanup_candidates)} workspaces for cleanup")

                for workspace in cleanup_candidates:
                    await self._cleanup_workspace(workspace)

            self._stats["total_cleanups"] = cast(int, self._stats["total_cleanups"]) + 1
            logger.debug(f"Cleanup cycle completed. Processed {len(cleanup_candidates)} workspaces")

        except Exception as e:
            logger.error(f"Error during cleanup cycle: {e}")
            raise

    async def _should_cleanup_workspace(self, workspace: Workspace) -> bool:
        """Determine if a workspace should be cleaned up.

        Args:
            workspace: Workspace to check

        Returns:
            True if workspace should be cleaned up
        """
        # Skip workspaces that are currently being processed
        if workspace.status in [WorkspaceStatus.INDEXING]:
            logger.debug(f"Skipping workspace {workspace.id} - currently {workspace.status}")
            return False

        # Check if workspace has active operations
        if await self._has_active_operations(workspace):
            logger.debug(f"Skipping workspace {workspace.id} - has active operations")
            return False

        # Check expiration (TTL)
        if workspace.is_expired():
            logger.info(f"Workspace {workspace.id} has expired")
            return True

        # Check idle time
        if workspace.is_idle(self.settings.workspace_max_idle_hours):
            logger.info(f"Workspace {workspace.id} has been idle too long")
            return True

        # Check size limits
        if (
            self.settings.workspace_max_size_mb > 0
            and workspace.size_bytes > self.settings.workspace_max_size_mb * 1024 * 1024
        ):
            logger.info(f"Workspace {workspace.id} exceeds size limit")
            return True

        return False

    async def _has_active_operations(self, workspace: Workspace) -> bool:
        """Check if workspace has active operations.

        Args:
            workspace: Workspace to check

        Returns:
            True if workspace has active operations
        """
        # Check if there are any active indexing jobs for this workspace
        try:
            # This would need to be implemented based on your indexing manager
            # For now, we'll use a simple heuristic based on recent access
            recent_threshold = datetime.now(UTC) - timedelta(
                minutes=self.settings.workspace_grace_period_minutes
            )
            return workspace.last_accessed_at > recent_threshold
        except Exception as e:
            logger.warning(f"Error checking active operations for workspace {workspace.id}: {e}")
            return True  # Err on the side of caution

    async def _cleanup_workspace(self, workspace: Workspace) -> None:
        """Clean up a specific workspace.

        Args:
            workspace: Workspace to clean up
        """
        try:
            logger.info(f"Cleaning up workspace {workspace.id} ({workspace.config.name})")

            # Calculate workspace size before cleanup
            workspace_path = workspace.get_workspace_directory(
                Path(self.settings.base_workspaces_path)
            )
            size_before = self._calculate_directory_size(workspace_path)

            # Archive or delete the workspace
            if workspace.status != WorkspaceStatus.ARCHIVED:
                # First try to archive
                workspace.update_status(WorkspaceStatus.ARCHIVED)
                await self.workspace_manager.update_workspace(workspace.id, workspace)

            # Remove workspace files
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
                logger.info(f"Removed workspace directory: {workspace_path}")

            # Remove from workspace manager
            await self.workspace_manager.delete_workspace(workspace.id)

            # Update statistics
            if workspace.is_expired():
                self._stats["expired_cleaned"] = cast(int, self._stats["expired_cleaned"]) + 1
            elif workspace.is_idle(self.settings.workspace_max_idle_hours):
                self._stats["idle_cleaned"] = cast(int, self._stats["idle_cleaned"]) + 1
            else:
                self._stats["size_cleaned"] = cast(int, self._stats["size_cleaned"]) + 1

            logger.info(
                f"Successfully cleaned up workspace {workspace.id}, freed {size_before / 1024 / 1024:.1f}MB"
            )

        except Exception as e:
            logger.error(f"Error cleaning up workspace {workspace.id}: {e}")
            self._stats["errors"] = cast(int, self._stats["errors"]) + 1
            raise

    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes.

        Args:
            directory: Directory to calculate size for

        Returns:
            Size in bytes
        """
        if not directory.exists():
            return 0

        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating directory size for {directory}: {e}")

        return total_size

    async def force_cleanup(self, workspace_id: str) -> bool:
        """Force cleanup of a specific workspace.

        Args:
            workspace_id: ID of workspace to clean up

        Returns:
            True if cleanup was successful
        """
        try:
            workspace = await self.workspace_manager.get_workspace(workspace_id)
            if not workspace:
                logger.warning(f"Workspace {workspace_id} not found for force cleanup")
                return False

            await self._cleanup_workspace(workspace)
            return True

        except Exception as e:
            logger.error(f"Error during force cleanup of workspace {workspace_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get cleanup service statistics.

        Returns:
            Dictionary with cleanup statistics
        """
        return {
            **self._stats,
            "running": self._running,
            "settings": {
                "cleanup_enabled": self.settings.workspace_cleanup_enabled,
                "cleanup_interval_minutes": self.settings.workspace_cleanup_interval_minutes,
                "ttl_hours": self.settings.workspace_ttl_hours,
                "max_idle_hours": self.settings.workspace_max_idle_hours,
                "max_size_mb": self.settings.workspace_max_size_mb,
                "grace_period_minutes": self.settings.workspace_grace_period_minutes,
            },
        }


# Global cleanup service instance
_cleanup_service: WorkspaceCleanupService | None = None


def get_cleanup_service(settings: Settings, workspace_manager: Any) -> WorkspaceCleanupService:
    """Get the global cleanup service instance.

    Args:
        settings: Application settings
        workspace_manager: Workspace manager instance

    Returns:
        Cleanup service instance
    """
    global _cleanup_service

    if _cleanup_service is None:
        _cleanup_service = WorkspaceCleanupService(settings, workspace_manager)

    return _cleanup_service


async def cleanup_cleanup_service() -> None:
    """Clean up the global cleanup service instance."""
    global _cleanup_service

    if _cleanup_service:
        await _cleanup_service.stop()
        _cleanup_service = None
