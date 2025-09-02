# tests/test_workspace.py
# Tests for GraphRAG workspace management
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for GraphRAG workspace management functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.workspace import WorkspaceManager
from src.graphrag_api_service.workspace.models import (
    WorkspaceCreateRequest,
    WorkspaceStatus,
    WorkspaceUpdateRequest,
)


class TestWorkspaceModels:
    """Test workspace data models."""

    def test_workspace_create_request_validation(self):
        """Test workspace creation request validation."""
        # Valid request
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Test workspace",
            data_path="/test/data",
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )
        assert request.name == "test-workspace"
        assert request.description == "Test workspace"
        assert request.data_path == "/test/data"

    def test_workspace_name_validation(self):
        """Test workspace name validation rules."""
        from src.graphrag_api_service.workspace.models import WorkspaceConfig

        # Valid names
        valid_names = ["test", "test-workspace", "test_workspace", "workspace123", "ws-01"]
        for name in valid_names:
            config = WorkspaceConfig(
                name=name,
                description="Test",
                data_path="/test",
                output_path=None,
                llm_model_override=None,
                embedding_model_override=None,
            )
            assert config.name == name

        # Invalid names should raise validation errors
        with pytest.raises(ValueError, match="Workspace name cannot be empty"):
            WorkspaceConfig(
                name="",
                description="Test",
                data_path="/test",
                output_path=None,
                llm_model_override=None,
                embedding_model_override=None,
                chunk_size=1200,
                chunk_overlap=100,
                max_entities=1000,
                max_relationships=2000,
            )

        with pytest.raises(ValueError, match="can only contain"):
            WorkspaceConfig(
                name="test workspace",
                description="Test",
                data_path="/test",
                output_path=None,
                llm_model_override=None,
                embedding_model_override=None,
                chunk_size=1200,
                chunk_overlap=100,
                max_entities=1000,
                max_relationships=2000,
            )

        with pytest.raises(ValueError, match="cannot exceed 50 characters"):
            WorkspaceConfig(
                name="a" * 51,
                description="Test",
                data_path="/test",
                output_path=None,
                llm_model_override=None,
                embedding_model_override=None,
                chunk_size=1200,
                chunk_overlap=100,
                max_entities=1000,
                max_relationships=2000,
            )


class TestWorkspaceManager:
    """Test workspace manager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def settings(self) -> Settings:
        """Provide test settings."""
        return Settings()

    @pytest.fixture
    def workspace_manager(self, settings: Settings, temp_dir: Path):
        """Create workspace manager with temporary directory."""
        # Create manager normally, then override the base path
        manager = WorkspaceManager(settings, None)  # Use file-based storage for tests

        # Override the base workspaces path to use temp directory
        manager.base_workspaces_path = temp_dir / "workspaces"
        manager.workspaces_index_file = manager.base_workspaces_path / "workspaces.json"

        # Create workspaces directory and reset workspaces
        manager.base_workspaces_path.mkdir(exist_ok=True)
        manager._workspaces = {}
        manager._save_workspaces_index()

        yield manager

    @pytest.fixture
    def test_data_dir(self, temp_dir: Path):
        """Create test data directory with sample files."""
        data_dir = temp_dir / "test_data"
        data_dir.mkdir()

        # Create sample text files
        (data_dir / "doc1.txt").write_text("This is test document 1.", encoding="utf-8")
        (data_dir / "doc2.txt").write_text("This is test document 2.", encoding="utf-8")

        return data_dir

    async def test_create_workspace_success(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test successful workspace creation."""
        request = WorkspaceCreateRequest(
            name="test-workspace",
            description="Test workspace for unit tests",
            data_path=str(test_data_dir),
            chunk_size=800,
            chunk_overlap=100,
            max_entities=500,
            max_relationships=1000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)

        # Verify workspace properties
        assert workspace.config.name == "test-workspace"
        assert workspace.config.description == "Test workspace for unit tests"
        assert workspace.config.chunk_size == 800
        assert workspace.config.max_entities == 500
        assert workspace.status == WorkspaceStatus.CREATED

        # Verify workspace directory was created
        workspace_dir = workspace.get_workspace_directory(workspace_manager.base_workspaces_path)
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()

        # Verify output directory was created
        output_dir = workspace.get_output_directory(workspace_manager.base_workspaces_path)
        assert output_dir.exists()

        # Verify configuration file was created
        config_file = workspace.get_config_file_path(workspace_manager.base_workspaces_path)
        assert config_file.exists()

        # Verify configuration content
        with open(config_file, encoding="utf-8") as f:
            config_content = yaml.safe_load(f)

        assert config_content["chunks"]["size"] == 800
        assert str(test_data_dir) in config_content["input"]["base_dir"]

    async def test_create_workspace_duplicate_name(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test workspace creation with duplicate name fails."""
        request = WorkspaceCreateRequest(
            name="duplicate-workspace",
            description="First workspace",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        # Create first workspace
        await workspace_manager.create_workspace(request)

        # Try to create second workspace with same name
        request2 = WorkspaceCreateRequest(
            name="duplicate-workspace",
            description="Second workspace",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        with pytest.raises(ValueError, match="already exists"):
            await workspace_manager.create_workspace(request2)

    async def test_create_workspace_invalid_data_path(self, workspace_manager: WorkspaceManager):
        """Test workspace creation with invalid data path fails."""
        request = WorkspaceCreateRequest(
            name="invalid-path-workspace",
            description="Workspace with invalid path",
            data_path="/nonexistent/path",
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        with pytest.raises(ValueError, match="Data path does not exist"):
            await workspace_manager.create_workspace(request)

    async def test_get_workspace_by_id(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test retrieving workspace by ID."""
        request = WorkspaceCreateRequest(
            name="retrieve-test",
            description="Workspace for retrieval test",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        created_workspace = await workspace_manager.create_workspace(request)

        # Test successful retrieval
        retrieved_workspace = await workspace_manager.get_workspace(created_workspace.id)
        assert retrieved_workspace is not None
        assert retrieved_workspace.id == created_workspace.id
        assert retrieved_workspace.config.name == "retrieve-test"

        # Test retrieval of non-existent workspace
        non_existent = await workspace_manager.get_workspace("non-existent-id")
        assert non_existent is None

    async def test_get_workspace_by_name(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test retrieving workspace by name."""
        request = WorkspaceCreateRequest(
            name="name-lookup-test",
            description="Workspace for name lookup test",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        created_workspace = await workspace_manager.create_workspace(request)

        # Test successful retrieval by name
        retrieved_workspace = await workspace_manager.get_workspace_by_name("name-lookup-test")
        assert retrieved_workspace is not None
        assert retrieved_workspace.id == created_workspace.id

        # Test retrieval of non-existent workspace
        non_existent = await workspace_manager.get_workspace_by_name("non-existent-name")
        assert non_existent is None

    async def test_list_workspaces(self, workspace_manager: WorkspaceManager, test_data_dir: Path):
        """Test listing workspaces."""
        # Initially empty
        workspaces = await workspace_manager.list_workspaces()
        assert len(workspaces) == 0

        # Create multiple workspaces
        names = ["workspace-1", "workspace-2", "workspace-3"]
        for name in names:
            request = WorkspaceCreateRequest(
                name=name,
                description=f"Test workspace {name}",
                data_path=str(test_data_dir),
                chunk_size=1200,
                chunk_overlap=100,
                max_entities=1000,
                max_relationships=2000,
                llm_model_override=None,
                embedding_model_override=None,
                community_levels=None,
            )
            await workspace_manager.create_workspace(request)

        # List workspaces
        workspaces = await workspace_manager.list_workspaces()
        assert len(workspaces) == 3

        # Verify workspace names
        workspace_names = {ws.name for ws in workspaces}
        assert workspace_names == set(names)

        # Verify summaries have required fields
        for workspace in workspaces:
            assert workspace.id
            assert workspace.name
            assert workspace.description
            assert workspace.status == WorkspaceStatus.CREATED

    async def test_update_workspace(self, workspace_manager: WorkspaceManager, test_data_dir: Path):
        """Test workspace configuration updates."""
        request = WorkspaceCreateRequest(
            name="update-test",
            description="Original description",
            data_path=str(test_data_dir),
            chunk_size=1000,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)
        original_updated_at = workspace.updated_at

        # Update workspace
        update_request = WorkspaceUpdateRequest(
            description="Updated description",
            data_path=None,
            chunk_size=1500,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=2000,
            max_relationships=None,
            community_levels=None,
        )

        updated_workspace = await workspace_manager.update_workspace(workspace.id, update_request)

        # Verify updates
        assert updated_workspace.config.description == "Updated description"
        assert updated_workspace.config.chunk_size == 1500
        assert updated_workspace.config.max_entities == 2000
        assert updated_workspace.updated_at > original_updated_at

        # Verify configuration file was updated
        config_file = updated_workspace.get_config_file_path(workspace_manager.base_workspaces_path)
        with open(config_file, encoding="utf-8") as f:
            config_content = yaml.safe_load(f)

        assert config_content["chunks"]["size"] == 1500

    async def test_update_nonexistent_workspace(self, workspace_manager: WorkspaceManager):
        """Test updating non-existent workspace fails."""
        update_request = WorkspaceUpdateRequest(
            description="New description",
            data_path=None,
            chunk_size=None,
            chunk_overlap=None,
            llm_model_override=None,
            embedding_model_override=None,
            max_entities=None,
            max_relationships=None,
            community_levels=None,
        )

        with pytest.raises(ValueError, match="Workspace not found"):
            await workspace_manager.update_workspace("non-existent-id", update_request)

    async def test_delete_workspace_without_files(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test workspace deletion without removing files."""
        request = WorkspaceCreateRequest(
            name="delete-test",
            description="Workspace for deletion test",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)
        workspace_dir = workspace.get_workspace_directory(workspace_manager.base_workspaces_path)

        # Verify workspace exists
        assert workspace_dir.exists()
        assert await workspace_manager.get_workspace(workspace.id) is not None

        # Delete workspace without removing files
        success = await workspace_manager.delete_workspace(workspace.id, remove_files=False)
        assert success

        # Verify workspace removed from index but files remain
        assert await workspace_manager.get_workspace(workspace.id) is None
        assert workspace_dir.exists()  # Files should remain

    async def test_delete_workspace_with_files(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test workspace deletion with file removal."""
        request = WorkspaceCreateRequest(
            name="delete-files-test",
            description="Workspace for deletion with files test",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)
        workspace_dir = workspace.get_workspace_directory(workspace_manager.base_workspaces_path)

        # Verify workspace exists
        assert workspace_dir.exists()

        # Delete workspace with file removal
        success = await workspace_manager.delete_workspace(workspace.id, remove_files=True)
        assert success

        # Verify workspace and files removed
        assert await workspace_manager.get_workspace(workspace.id) is None
        assert not workspace_dir.exists()

    async def test_delete_nonexistent_workspace(self, workspace_manager: WorkspaceManager):
        """Test deleting non-existent workspace returns False."""
        success = await workspace_manager.delete_workspace("non-existent-id")
        assert not success

    async def test_workspace_stats(self, workspace_manager: WorkspaceManager, test_data_dir: Path):
        """Test workspace statistics calculation."""
        # Initial stats
        stats = await workspace_manager.get_workspace_stats()
        assert stats["total_workspaces"] == 0

        # Create workspaces with different statuses
        request1 = WorkspaceCreateRequest(
            name="stats-test-1",
            description="First test workspace",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )
        workspace1 = await workspace_manager.create_workspace(request1)

        request2 = WorkspaceCreateRequest(
            name="stats-test-2",
            description="Second test workspace",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )
        await workspace_manager.create_workspace(request2)

        # Update one workspace status
        workspace1.status = WorkspaceStatus.INDEXED
        workspace1.files_processed = 5
        workspace1.entities_extracted = 100
        workspace1.relationships_extracted = 200
        workspace_manager._save_workspaces_index()

        # Get updated stats
        stats = await workspace_manager.get_workspace_stats()
        assert stats["total_workspaces"] == 2
        assert stats["status_distribution"]["created"] == 1
        assert stats["status_distribution"]["indexed"] == 1
        assert stats["total_files_processed"] == 5
        assert stats["total_entities_extracted"] == 100
        assert stats["total_relationships_extracted"] == 200

    async def test_workspace_index_persistence(
        self, workspace_manager: WorkspaceManager, test_data_dir: Path
    ):
        """Test workspace index persistence across manager instances."""
        # Create workspace
        request = WorkspaceCreateRequest(
            name="persistence-test",
            description="Test workspace persistence",
            data_path=str(test_data_dir),
            chunk_size=1200,
            chunk_overlap=100,
            max_entities=1000,
            max_relationships=2000,
            llm_model_override=None,
            embedding_model_override=None,
            community_levels=None,
        )

        workspace = await workspace_manager.create_workspace(request)
        workspace_id = workspace.id

        # Create new manager instance (simulating restart)
        new_manager = WorkspaceManager(
            workspace_manager.settings, None
        )  # No database manager for this test

        # Verify the new manager was initialized properly
        assert hasattr(new_manager, 'db_manager'), "New manager missing db_manager attribute"
        assert new_manager.db_manager is None, "db_manager should be None for file-based storage"

        # Ensure the workspaces paths are the same
        new_manager.base_workspaces_path = workspace_manager.base_workspaces_path
        new_manager.workspaces_index_file = workspace_manager.workspaces_index_file

        # Reload the workspaces index from the shared location
        new_manager._load_workspaces_index()

        # Verify workspace persisted
        persisted_workspace = await new_manager.get_workspace(workspace_id)
        assert persisted_workspace is not None
        assert persisted_workspace.config.name == "persistence-test"
