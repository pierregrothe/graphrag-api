# src/graphrag_api_service/routes/workspace.py
# Workspace management API route handlers
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Workspace management API route handlers."""

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from ..logging_config import get_logger
from ..workspace.models import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)

logger = get_logger(__name__)

# Create router for workspace endpoints
router = APIRouter(prefix="/api", tags=["Workspace"])


# Dependency injection function (to be called from main.py)
def setup_workspace_routes(workspace_manager):
    """Setup workspace routes with dependencies."""

    @router.post("/workspaces", response_model=Workspace)
    async def create_workspace(request: WorkspaceCreateRequest) -> Workspace:
        """Create a new GraphRAG workspace.

        Creates a new workspace with its own configuration, data directory,
        and isolated GraphRAG processing environment.

        Args:
            request: Workspace creation request

        Returns:
            Created workspace information

        Raises:
            HTTPException: If workspace creation fails
        """
        logger.info(f"Creating workspace: {request.name}")

        try:
            workspace = workspace_manager.create_workspace(request)
            logger.info(f"Successfully created workspace: {workspace.id}")
            return workspace
        except ValueError as e:
            logger.error(f"Workspace creation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except OSError as e:
            logger.error(f"Workspace directory creation failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create workspace directories: {e}"
            ) from e

    @router.get("/workspaces", response_model=list[WorkspaceSummary])
    async def list_workspaces() -> list[WorkspaceSummary]:
        """List all GraphRAG workspaces.

        Returns:
            List of workspace summaries with key information
        """
        logger.info("Listing workspaces")
        workspaces = workspace_manager.list_workspaces()
        logger.info(f"Found {len(workspaces)} workspaces")
        return workspaces

    @router.get("/workspaces/{workspace_id}", response_model=Workspace)
    async def get_workspace(workspace_id: str) -> Workspace:
        """Get workspace by ID.

        Args:
            workspace_id: Unique workspace identifier

        Returns:
            Workspace information

        Raises:
            HTTPException: If workspace not found
        """
        logger.info(f"Getting workspace: {workspace_id}")

        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            logger.warning(f"Workspace not found: {workspace_id}")
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

        return workspace

    @router.put("/workspaces/{workspace_id}", response_model=Workspace)
    async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest) -> Workspace:
        """Update workspace configuration.

        Args:
            workspace_id: Unique workspace identifier
            request: Workspace update request

        Returns:
            Updated workspace information

        Raises:
            HTTPException: If workspace not found or update fails
        """
        logger.info(f"Updating workspace: {workspace_id}")

        try:
            workspace = workspace_manager.update_workspace(workspace_id, request)
            logger.info(f"Successfully updated workspace: {workspace_id}")
            return workspace
        except ValueError as e:
            logger.error(f"Workspace update failed: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.delete("/workspaces/{workspace_id}")
    async def delete_workspace(workspace_id: str, remove_files: bool = False) -> dict[str, Any]:
        """Delete workspace.

        Args:
            workspace_id: Unique workspace identifier
            remove_files: Whether to remove workspace files from disk

        Returns:
            Deletion status information

        Raises:
            HTTPException: If workspace not found
        """
        logger.info(f"Deleting workspace: {workspace_id} (remove_files={remove_files})")

        success = workspace_manager.delete_workspace(workspace_id, remove_files)
        if not success:
            logger.warning(f"Workspace not found for deletion: {workspace_id}")
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

        logger.info(f"Successfully deleted workspace: {workspace_id}")
        return {
            "status": "deleted",
            "workspace_id": workspace_id,
            "files_removed": remove_files,
            "message": f"Workspace {workspace_id} deleted successfully",
        }

    @router.get("/workspaces/{workspace_id}/config")
    async def get_workspace_config(workspace_id: str) -> dict[str, Any]:
        """Get workspace GraphRAG configuration file content.

        Args:
            workspace_id: Unique workspace identifier

        Returns:
            Workspace GraphRAG configuration

        Raises:
            HTTPException: If workspace not found or config not available
        """
        logger.info(f"Getting workspace config: {workspace_id}")

        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            logger.warning(f"Workspace not found: {workspace_id}")
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

        if not workspace.config_file_path:
            raise HTTPException(status_code=404, detail="Workspace configuration not available")

        try:
            config_path = Path(workspace.config_file_path)
            if not config_path.exists():
                raise HTTPException(status_code=404, detail="Configuration file not found")

            with open(config_path, encoding="utf-8") as f:
                config_content = yaml.safe_load(f)

            return {
                "workspace_id": workspace_id,
                "config_file": str(config_path),
                "configuration": config_content,
            }

        except Exception as e:
            logger.error(f"Failed to read workspace config: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to read configuration: {e}") from e

    return router
