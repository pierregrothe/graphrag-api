# tests/test_indexing.py
# Tests for GraphRAG indexing functionality
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for GraphRAG indexing functionality."""

import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.indexing import IndexingManager
from src.graphrag_api_service.indexing.models import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobStatus,
    IndexingStage,
)
from src.graphrag_api_service.indexing.tasks import IndexingTask
from src.graphrag_api_service.workspace.models import (
    Workspace,
    WorkspaceConfig,
    WorkspaceStatus,
)


class TestIndexingModels:
    """Test indexing data models."""

    def test_indexing_job_creation(self):
        """Test indexing job creation with default values."""
        job = IndexingJob(
            workspace_id="test-workspace",
            started_at=None,
            completed_at=None,
            error_message=None,
        )

        assert job.workspace_id == "test-workspace"
        assert job.status == IndexingJobStatus.QUEUED
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.priority == 5
        assert job.progress.current_stage == IndexingStage.INITIALIZATION
        assert job.progress.overall_progress == 0.0

    def test_indexing_job_lifecycle(self):
        """Test indexing job state transitions."""
        job = IndexingJob(
            workspace_id="test-workspace",
            started_at=None,
            completed_at=None,
            error_message=None,
        )

        # Test start
        assert job.status == IndexingJobStatus.QUEUED
        assert job.is_active  # QUEUED is considered active
        job.start_job()
        # After calling start_job(), status changes to RUNNING
        assert job.status == IndexingJobStatus.RUNNING  # type: ignore[comparison-overlap]
        assert job.started_at is not None
        assert job.is_active

        # Test completion
        job.complete_job()
        assert job.status == IndexingJobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.progress.overall_progress == 1.0
        assert job.is_finished
        assert not job.is_active

    def test_indexing_job_failure_and_retry(self):
        """Test indexing job failure and retry logic."""
        job = IndexingJob(
            workspace_id="test-workspace",
            max_retries=2,
            started_at=None,
            completed_at=None,
            error_message=None,
        )

        # Test failure
        error_msg = "Processing failed"
        job.fail_job(error_msg)
        assert job.status == IndexingJobStatus.FAILED
        assert job.error_message == error_msg
        assert job.is_finished

        # Test retry capability
        assert job.can_retry()
        job.increment_retry()
        assert job.retry_count == 1
        # After increment_retry(), status changes back to QUEUED
        assert job.status == IndexingJobStatus.QUEUED  # type: ignore[comparison-overlap]
        assert job.error_message is None

        # Test max retries
        job.fail_job("Failed again")
        job.increment_retry()
        job.fail_job("Failed third time")
        assert not job.can_retry()

    def test_indexing_job_create_request_validation(self):
        """Test indexing job creation request validation."""
        # Valid request
        request = IndexingJobCreate(workspace_id="test-workspace", priority=8, max_retries=5)
        assert request.workspace_id == "test-workspace"
        assert request.priority == 8
        assert request.max_retries == 5

        # Default values
        request_defaults = IndexingJobCreate(
            workspace_id="test-workspace", priority=5, max_retries=3
        )
        assert request_defaults.priority == 5
        assert request_defaults.max_retries == 3


class TestIndexingTask:
    """Test indexing task execution."""

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
    def test_workspace(self, temp_dir: Path):
        """Create test workspace."""
        config = WorkspaceConfig(
            name="test-workspace",
            description="Test workspace",
            data_path=str(temp_dir / "data"),
            output_path=None,
            chunk_size=800,
            max_entities=100,
            llm_model_override=None,
            embedding_model_override=None,
        )

        workspace = Workspace(
            id=str(uuid.uuid4()),
            config=config,
            status=WorkspaceStatus.CREATED,
            last_error=None,
            workspace_path=None,
            config_file_path=None,
            expires_at=None,
        )

        # Create required directories and files
        data_dir = Path(config.data_path)
        data_dir.mkdir(parents=True, exist_ok=True)

        workspace_dir = temp_dir / "workspaces" / config.name
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Create sample data files
        (data_dir / "doc1.txt").write_text("This is test document 1.", encoding="utf-8")
        (data_dir / "doc2.txt").write_text("This is test document 2.", encoding="utf-8")

        # Create mock settings file
        settings_file = workspace_dir / "settings.yaml"
        settings_file.write_text("# Mock GraphRAG settings", encoding="utf-8")

        return workspace

    @pytest.fixture
    def indexing_task(self, settings: Settings, test_workspace: Workspace, temp_dir: Path):
        """Create indexing task."""
        with patch.object(IndexingTask, "__init__", lambda self, s, w: None):
            task = IndexingTask.__new__(IndexingTask)
            task.settings = settings
            task.workspace = test_workspace
            task.workspace_dir = temp_dir / "workspaces" / test_workspace.config.name
            task.config_file = task.workspace_dir / "settings.yaml"

            # Create the workspace directory and config file
            task.workspace_dir.mkdir(parents=True, exist_ok=True)
            task.config_file.write_text("# Mock GraphRAG settings", encoding="utf-8")

            task.stage_weights = {
                IndexingStage.INITIALIZATION: 0.1,
                IndexingStage.TEXT_PROCESSING: 0.3,
                IndexingStage.ENTITY_EXTRACTION: 0.3,
                IndexingStage.RELATIONSHIP_EXTRACTION: 0.2,
                IndexingStage.COMMUNITY_DETECTION: 0.1,
                IndexingStage.EMBEDDING_GENERATION: 0.0,
                IndexingStage.INDEX_CREATION: 0.0,
                IndexingStage.FINALIZATION: 0.0,
            }
            yield task

    @pytest.fixture
    def test_job(self, test_workspace: Workspace):
        """Create test indexing job."""
        return IndexingJob(
            workspace_id=test_workspace.id,
            started_at=None,
            completed_at=None,
            error_message=None,
        )

    @pytest.mark.asyncio
    async def test_initialization_stage(self, indexing_task: IndexingTask, test_job: IndexingJob):
        """Test initialization stage execution."""
        await indexing_task._run_initialization(test_job)

        assert test_job.progress.current_stage == IndexingStage.INITIALIZATION
        assert test_job.progress.stage_progress == 1.0
        assert test_job.progress.total_files == 2  # Two test files created
        assert test_job.progress.overall_progress > 0.0

    @pytest.mark.asyncio
    async def test_text_processing_stage(self, indexing_task: IndexingTask, test_job: IndexingJob):
        """Test text processing stage execution."""
        # Start the job first (required for processing rate calculation)
        test_job.start_job()

        # Initialize first
        await indexing_task._run_initialization(test_job)

        # Run text processing
        await indexing_task._run_text_processing(test_job)

        assert test_job.progress.current_stage == IndexingStage.TEXT_PROCESSING
        assert test_job.progress.stage_progress == 1.0
        assert test_job.progress.processed_files == test_job.progress.total_files
        assert test_job.progress.processing_rate is not None

    @pytest.mark.asyncio
    async def test_complete_indexing_pipeline(
        self, indexing_task: IndexingTask, test_job: IndexingJob
    ):
        """Test complete indexing pipeline execution."""
        # Mock the JSON file writing in finalization stage
        with patch("builtins.open", create=True), patch("json.dump"):

            await indexing_task.execute_indexing(test_job)

        assert test_job.status == IndexingJobStatus.COMPLETED
        assert test_job.progress.overall_progress == 1.0
        assert test_job.progress.current_stage == IndexingStage.FINALIZATION
        assert test_job.completed_at is not None
        assert test_job.progress.entities_extracted > 0
        assert test_job.progress.relationships_extracted > 0


class TestIndexingManager:
    """Test indexing manager functionality."""

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
    def indexing_manager(self, settings: Settings, temp_dir: Path):
        """Create indexing manager with temporary directory."""
        with patch.object(IndexingManager, "__init__", lambda self, settings: None):
            manager = IndexingManager.__new__(IndexingManager)
            manager.settings = settings
            manager.jobs_dir = temp_dir / "indexing_jobs"
            manager.jobs_index_file = manager.jobs_dir / "jobs.json"
            manager._jobs = {}
            manager._active_tasks = {}
            manager._running_jobs = set()
            manager.max_concurrent_jobs = 2
            manager.job_cleanup_hours = 48
            manager._queue_processor_task = None
            manager._shutdown_event = asyncio.Event()

            # Create jobs directory
            manager.jobs_dir.mkdir(exist_ok=True)
            manager._save_jobs_index()

            yield manager

    @pytest.fixture
    def test_workspace(self):
        """Create test workspace."""
        config = WorkspaceConfig(
            name="test-workspace",
            description="Test workspace",
            data_path="/test/data",
            output_path=None,
            llm_model_override=None,
            embedding_model_override=None,
        )

        return Workspace(
            id=str(uuid.uuid4()),
            config=config,
            status=WorkspaceStatus.CREATED,
            last_error=None,
            workspace_path=None,
            config_file_path=None,
        )

    def test_create_indexing_job_success(
        self, indexing_manager: IndexingManager, test_workspace: Workspace
    ):
        """Test successful indexing job creation."""
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=3, max_retries=2)

        job = indexing_manager.create_indexing_job(request, test_workspace)

        assert job.workspace_id == test_workspace.id
        assert job.priority == 3
        assert job.max_retries == 2
        assert job.status == IndexingJobStatus.QUEUED
        assert job.id in indexing_manager._jobs

    def test_create_duplicate_job_fails(
        self, indexing_manager: IndexingManager, test_workspace: Workspace
    ):
        """Test that creating duplicate job for workspace fails."""
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)

        # Create first job
        indexing_manager.create_indexing_job(request, test_workspace)

        # Try to create second job for same workspace
        with pytest.raises(ValueError, match="already has an active indexing job"):
            indexing_manager.create_indexing_job(request, test_workspace)

    def test_create_job_for_non_ready_workspace_fails(self, indexing_manager: IndexingManager):
        """Test creating job for workspace not ready for indexing fails."""
        config = WorkspaceConfig(
            name="indexing-workspace",
            description="Test workspace",
            data_path="/test/data",
            output_path=None,
            llm_model_override=None,
            embedding_model_override=None,
        )

        workspace = Workspace(
            id=str(uuid.uuid4()),
            config=config,
            status=WorkspaceStatus.INDEXING,  # Not ready for indexing
            last_error=None,
            workspace_path=None,
            config_file_path=None,
            expires_at=None,
        )

        request = IndexingJobCreate(workspace_id=workspace.id, priority=5, max_retries=3)

        with pytest.raises(ValueError, match="not ready for indexing"):
            indexing_manager.create_indexing_job(request, workspace)

    def test_get_job_by_id(self, indexing_manager: IndexingManager, test_workspace: Workspace):
        """Test retrieving job by ID."""
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        created_job = indexing_manager.create_indexing_job(request, test_workspace)

        # Test successful retrieval
        retrieved_job = indexing_manager.get_job(created_job.id)
        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id

        # Test retrieval of non-existent job
        non_existent = indexing_manager.get_job("non-existent-id")
        assert non_existent is None

    def test_get_jobs_for_workspace(
        self, indexing_manager: IndexingManager, test_workspace: Workspace
    ):
        """Test getting jobs for a workspace."""
        # Create multiple jobs for same workspace
        request1 = IndexingJobCreate(workspace_id=test_workspace.id, priority=1, max_retries=3)
        request2 = IndexingJobCreate(workspace_id=test_workspace.id, priority=2, max_retries=3)

        job1 = indexing_manager.create_indexing_job(request1, test_workspace)

        # Complete first job to allow second job
        job1.complete_job()

        job2 = indexing_manager.create_indexing_job(request2, test_workspace)

        jobs = indexing_manager.get_jobs_for_workspace(test_workspace.id)

        assert len(jobs) == 2
        job_ids = {job.id for job in jobs}
        assert job1.id in job_ids
        assert job2.id in job_ids

    def test_list_jobs_with_status_filter(
        self, indexing_manager: IndexingManager, test_workspace: Workspace
    ):
        """Test listing jobs with status filter."""
        # Create jobs with different statuses
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        job = indexing_manager.create_indexing_job(request, test_workspace)

        # Initially queued
        queued_jobs = indexing_manager.list_jobs(status=IndexingJobStatus.QUEUED)
        assert len(queued_jobs) == 1
        assert queued_jobs[0].id == job.id

        # Mark as running
        job.start_job()
        running_jobs = indexing_manager.list_jobs(status=IndexingJobStatus.RUNNING)
        assert len(running_jobs) == 1

        # No queued jobs now
        queued_jobs = indexing_manager.list_jobs(status=IndexingJobStatus.QUEUED)
        assert len(queued_jobs) == 0

    def test_cancel_job(self, indexing_manager: IndexingManager, test_workspace: Workspace):
        """Test job cancellation."""
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        job = indexing_manager.create_indexing_job(request, test_workspace)

        # Test successful cancellation
        success = indexing_manager.cancel_job(job.id)
        assert success
        assert job.status == IndexingJobStatus.CANCELLED

        # Test cancelling non-existent job
        success = indexing_manager.cancel_job("non-existent-id")
        assert not success

    def test_retry_job(self, indexing_manager: IndexingManager, test_workspace: Workspace):
        """Test job retry functionality."""
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=2)
        job = indexing_manager.create_indexing_job(request, test_workspace)

        # Fail the job
        job.fail_job("Test error")

        # Test successful retry
        success = indexing_manager.retry_job(job.id)
        assert success
        assert job.status == IndexingJobStatus.QUEUED
        assert job.retry_count == 1

        # Exhaust retries
        job.fail_job("Test error 2")
        indexing_manager.retry_job(job.id)  # Second retry
        job.fail_job("Test error 3")

        # Should not be able to retry again
        success = indexing_manager.retry_job(job.id)
        assert not success

    def test_indexing_stats(self, indexing_manager: IndexingManager, test_workspace: Workspace):
        """Test indexing statistics calculation."""
        # Initial stats
        stats = indexing_manager.get_indexing_stats()
        assert stats.total_jobs == 0

        # Create jobs with different statuses
        request1 = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        job1 = indexing_manager.create_indexing_job(request1, test_workspace)

        # Complete first job to create second
        job1.complete_job()

        request2 = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        job2 = indexing_manager.create_indexing_job(request2, test_workspace)
        job2.fail_job("Test error")

        # Get updated stats
        stats = indexing_manager.get_indexing_stats()
        assert stats.total_jobs == 2
        assert stats.completed_jobs == 1
        assert stats.failed_jobs == 1
        assert stats.success_rate == 0.5  # 1 success out of 2 finished jobs

    def test_job_persistence(self, indexing_manager: IndexingManager, test_workspace: Workspace):
        """Test job persistence across manager instances."""
        # Create job
        request = IndexingJobCreate(workspace_id=test_workspace.id, priority=5, max_retries=3)
        job = indexing_manager.create_indexing_job(request, test_workspace)
        job_id = job.id

        # Create new manager instance (simulating restart)
        new_manager = IndexingManager.__new__(IndexingManager)
        new_manager.settings = indexing_manager.settings
        new_manager.jobs_dir = indexing_manager.jobs_dir
        new_manager.jobs_index_file = indexing_manager.jobs_index_file
        new_manager._jobs = {}
        new_manager._active_tasks = {}
        new_manager._running_jobs = set()
        new_manager.max_concurrent_jobs = 2
        new_manager.job_cleanup_hours = 48
        new_manager._queue_processor_task = None
        new_manager._shutdown_event = asyncio.Event()
        new_manager._load_jobs_index()

        # Verify job persisted
        persisted_job = new_manager.get_job(job_id)
        assert persisted_job is not None
        assert persisted_job.workspace_id == test_workspace.id
