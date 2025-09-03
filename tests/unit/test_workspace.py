# tests/unit/test_workspace.py
# Unit tests for workspace management module
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""
Module: Workspace Management
Tests: Workspace CRUD operations, configuration generation, file management
Coverage: Create, read, update, delete workspaces; GraphRAG config generation
Dependencies: File system access
"""

import tempfile
import uuid
from pathlib import Path

import pytest

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.workspace.manager import WorkspaceManager
from src.graphrag_api_service.workspace.models import (
    WorkspaceCreateRequest,
    WorkspaceStatus,
    WorkspaceUpdateRequest,
)


class TestWorkspaceManager:
    """Test workspace manager functionality."""

    @pytest.fixture
    def workspace_manager(self):
        """Create a workspace manager instance for testing."""
        settings = Settings()
        return WorkspaceManager(settings)

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_create_workspace_valid_data_returns_success(
        self, workspace_manager, temp_data_dir
    ):
        """Test creating workspace with valid data returns success."""
        request = WorkspaceCreateRequest(
            name=f"test-workspace-{uuid.uuid4().hex[:8]}",
            description="Test workspace",
            data_path=str(temp_data_dir),
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)

        assert workspace is not None
        assert workspace.config.name == request.name
        assert workspace.config.description == request.description
        assert workspace.status == WorkspaceStatus.CREATED

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate_name_raises_error(
        self, workspace_manager, temp_data_dir
    ):
        """Test creating workspace with duplicate name raises error."""
        request = WorkspaceCreateRequest(
            name="duplicate-workspace",
            description="Test workspace",
            data_path=str(temp_data_dir),
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        # Create first workspace
        await workspace_manager.create_workspace(request)

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await workspace_manager.create_workspace(request)

    @pytest.mark.asyncio
    async def test_create_workspace_invalid_path_raises_error(self, workspace_manager):
        """Test creating workspace with invalid data path raises error."""
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Test workspace",
            data_path="/nonexistent/path",
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        with pytest.raises(ValueError, match="does not exist"):
            await workspace_manager.create_workspace(request)

    @pytest.mark.asyncio
    async def test_get_workspace_by_id_returns_workspace(self, workspace_manager, temp_data_dir):
        """Test getting workspace by ID returns correct workspace."""
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Test workspace",
            data_path=str(temp_data_dir),
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        created = await workspace_manager.create_workspace(request)
        retrieved = await workspace_manager.get_workspace(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.config.name == created.config.name

    @pytest.mark.asyncio
    async def test_get_workspace_invalid_id_returns_none(self, workspace_manager):
        """Test getting workspace with invalid ID returns None."""
        workspace = await workspace_manager.get_workspace("invalid-id")
        assert workspace is None

    @pytest.mark.asyncio
    async def test_list_workspaces_returns_all_workspaces(self, workspace_manager, temp_data_dir):
        """Test listing workspaces returns all created workspaces."""
        # Create multiple workspaces
        for i in range(3):
            request = WorkspaceCreateRequest(
                name=f"workspace-{i}",
                description=f"Test workspace {i}",
                data_path=str(temp_data_dir),
                chunk_size=None,
                chunk_overlap=None,
                llm_model_override=None,
                embedding_model_override=None,
                max_entities=None,
                max_relationships=None,
                community_levels=None,
            )
            await workspace_manager.create_workspace(request)

        workspaces = await workspace_manager.list_workspaces()
        assert len(workspaces) >= 3

    @pytest.mark.asyncio
    async def test_update_workspace_modifies_configuration(self, workspace_manager, temp_data_dir):
        """Test updating workspace modifies configuration correctly."""
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Original description",
            data_path=str(temp_data_dir),
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)

        update_request = WorkspaceUpdateRequest(
            description="Updated description",
            chunk_size=2000,
            data_path=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        updated = await workspace_manager.update_workspace(workspace.id, update_request)

        assert updated.config.description == "Updated description"
        assert updated.config.chunk_size == 2000

    @pytest.mark.asyncio
    async def test_delete_workspace_removes_workspace(self, workspace_manager, temp_data_dir):
        """Test deleting workspace removes it from the system."""
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Test workspace",
            data_path=str(temp_data_dir),
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)
        result = await workspace_manager.delete_workspace(workspace.id)

        assert result is True

        # Verify workspace is deleted
        retrieved = await workspace_manager.get_workspace(workspace.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_workspace_invalid_id_returns_false(self, workspace_manager):
        """Test deleting workspace with invalid ID returns False."""
        result = await workspace_manager.delete_workspace("invalid-id")
        assert result is False
