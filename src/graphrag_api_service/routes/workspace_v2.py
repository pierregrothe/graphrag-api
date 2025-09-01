# src/graphrag_api_service/routes/workspace_v2.py
# Workspace management API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Workspace management API route handlers with proper dependency injection."""

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from ..deps import WorkspaceManagerDep
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


@router.post("/workspaces", response_model=Workspace)
async def create_workspace(
    request: WorkspaceCreateRequest,
    workspace_manager: WorkspaceManagerDep
) -> Workspace:
    """Create a new GraphRAG workspace.

    Creates a new workspace with its own configuration, data directory,
    and isolated GraphRAG processing environment.

    Args:
        request: Workspace creation request
        workspace_manager: Workspace manager instance (injected)

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
    except Exception as e:
        logger.error(f"Unexpected error creating workspace: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create workspace: {e}"
        ) from e


@router.get("/workspaces", response_model=list[WorkspaceSummary])
async def list_workspaces(workspace_manager: WorkspaceManagerDep) -> list[WorkspaceSummary]:
    """List all available workspaces.

    Returns:
        List of workspace summaries

    Raises:
        HTTPException: If listing fails
    """
    logger.debug("Listing all workspaces")

    try:
        workspaces = workspace_manager.list_workspaces()
        logger.info(f"Found {len(workspaces)} workspaces")
        return workspaces
    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list workspaces: {e}"
        ) from e


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
async def get_workspace(
    workspace_id: str,
    workspace_manager: WorkspaceManagerDep
) -> Workspace:
    """Get detailed information about a specific workspace.

    Args:
        workspace_id: Workspace ID
        workspace_manager: Workspace manager instance (injected)

    Returns:
        Workspace information

    Raises:
        HTTPException: If workspace not found or access fails
    """
    logger.debug(f"Getting workspace: {workspace_id}")

    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workspace: {e}"
        ) from e


@router.put("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdateRequest,
    workspace_manager: WorkspaceManagerDep
) -> Workspace:
    """Update workspace configuration.

    Args:
        workspace_id: Workspace ID
        request: Update request with new configuration
        workspace_manager: Workspace manager instance (injected)

    Returns:
        Updated workspace information

    Raises:
        HTTPException: If workspace not found or update fails
    """
    logger.info(f"Updating workspace: {workspace_id}")

    try:
        workspace = workspace_manager.update_workspace(workspace_id, request)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        logger.info(f"Successfully updated workspace: {workspace_id}")
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update workspace: {e}"
        ) from e


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    remove_files: bool = False,
    workspace_manager: WorkspaceManagerDep = None
) -> dict[str, str]:
    """Delete a workspace.

    Args:
        workspace_id: Workspace ID
        remove_files: Whether to remove workspace files from disk
        workspace_manager: Workspace manager instance (injected)

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: If workspace not found or deletion fails
    """
    logger.info(f"Deleting workspace: {workspace_id} (remove_files={remove_files})")

    try:
        success = workspace_manager.delete_workspace(workspace_id, remove_files)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
        logger.info(f"Successfully deleted workspace: {workspace_id}")
        return {"message": f"Workspace {workspace_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete workspace: {e}"
        ) from e


@router.get("/workspaces/{workspace_id}/config")
async def get_workspace_config(
    workspace_id: str,
    workspace_manager: WorkspaceManagerDep
) -> dict[str, Any]:
    """Get GraphRAG configuration for a workspace.

    Args:
        workspace_id: Workspace ID
        workspace_manager: Workspace manager instance (injected)

    Returns:
        GraphRAG configuration as YAML/JSON

    Raises:
        HTTPException: If workspace not found or config read fails
    """
    logger.debug(f"Getting config for workspace: {workspace_id}")

    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

        # Read the settings.yaml file
        config_path = Path(workspace.data_path) / "settings.yaml"
        if not config_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Configuration file not found for workspace {workspace_id}"
            )

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config for workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get workspace config: {e}"
        ) from e