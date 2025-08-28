# tests/test_indexing_api.py
# Tests for GraphRAG indexing API endpoints
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for GraphRAG indexing API endpoints."""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.graphrag_api_service.indexing.models import (
    IndexingJob,
    IndexingJobStatus,
    IndexingStats,
)
from src.graphrag_api_service.main import app
from src.graphrag_api_service.workspace.models import Workspace, WorkspaceConfig, WorkspaceStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_workspace():
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


@pytest.fixture
def test_job(test_workspace):
    """Create test indexing job."""
    return IndexingJob(
        workspace_id=test_workspace.id,
        started_at=None,
        completed_at=None,
        error_message=None,
    )


class TestIndexingJobEndpoints:
    """Test indexing job API endpoints."""

    @patch("src.graphrag_api_service.main.indexing_manager")
    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_create_indexing_job_success(
        self, mock_workspace_manager, mock_indexing_manager, client, test_workspace, test_job
    ):
        """Test successful indexing job creation."""
        # Setup mocks
        mock_workspace_manager.get_workspace.return_value = test_workspace
        mock_indexing_manager.create_indexing_job.return_value = test_job
        mock_workspace_manager._save_workspaces_index.return_value = None

        # Make request
        request_data = {"workspace_id": test_workspace.id, "priority": 3, "max_retries": 2}

        response = client.post("/api/indexing/jobs", json=request_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == test_workspace.id
        assert data["status"] == "queued"

        # Verify mocks called correctly
        mock_workspace_manager.get_workspace.assert_called_once_with(test_workspace.id)
        mock_indexing_manager.create_indexing_job.assert_called_once()

    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_create_indexing_job_workspace_not_found(self, mock_workspace_manager, client):
        """Test indexing job creation with non-existent workspace."""
        # Setup mocks
        mock_workspace_manager.get_workspace.return_value = None

        # Make request
        request_data = {"workspace_id": "non-existent-workspace", "priority": 5}

        response = client.post("/api/indexing/jobs", json=request_data)

        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_create_indexing_job_workspace_not_ready(
        self, mock_workspace_manager, mock_indexing_manager, client, test_workspace
    ):
        """Test indexing job creation with workspace not ready for indexing."""
        # Setup mocks
        test_workspace.status = WorkspaceStatus.INDEXING  # Not ready
        mock_workspace_manager.get_workspace.return_value = test_workspace
        mock_indexing_manager.create_indexing_job.side_effect = ValueError("not ready for indexing")

        # Make request
        request_data = {"workspace_id": test_workspace.id, "priority": 5}

        response = client.post("/api/indexing/jobs", json=request_data)

        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert "not ready for indexing" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_list_indexing_jobs(self, mock_indexing_manager, client, test_job):
        """Test listing indexing jobs."""
        from src.graphrag_api_service.indexing.models import IndexingJobSummary, IndexingStage

        # Setup mocks
        job_summary = IndexingJobSummary(
            id=test_job.id,
            workspace_id=test_job.workspace_id,
            status=test_job.status,
            created_at=test_job.created_at,
            started_at=test_job.started_at,
            completed_at=test_job.completed_at,
            overall_progress=test_job.progress.overall_progress,
            current_stage=IndexingStage.INITIALIZATION,
            error_message=test_job.error_message,
        )
        mock_indexing_manager.list_jobs.return_value = [job_summary]

        # Make request
        response = client.get("/api/indexing/jobs")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_job.id
        assert data[0]["workspace_id"] == test_job.workspace_id

        # Test with status filter
        response = client.get("/api/indexing/jobs?status=queued&limit=50")
        assert response.status_code == 200

        # Verify mock called with parameters
        mock_indexing_manager.list_jobs.assert_called_with(
            status=IndexingJobStatus.QUEUED, limit=50
        )

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_get_indexing_job_by_id(self, mock_indexing_manager, client, test_job):
        """Test getting indexing job by ID."""
        # Setup mocks
        mock_indexing_manager.get_job.return_value = test_job

        # Make request
        response = client.get(f"/api/indexing/jobs/{test_job.id}")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_job.id
        assert data["workspace_id"] == test_job.workspace_id

        # Verify mock called
        mock_indexing_manager.get_job.assert_called_once_with(test_job.id)

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_get_indexing_job_not_found(self, mock_indexing_manager, client):
        """Test getting non-existent indexing job."""
        # Setup mocks
        mock_indexing_manager.get_job.return_value = None

        # Make request
        response = client.get("/api/indexing/jobs/non-existent-id")

        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_cancel_indexing_job(self, mock_indexing_manager, client, test_job):
        """Test cancelling indexing job."""
        # Setup mocks
        mock_indexing_manager.get_job.return_value = test_job
        mock_indexing_manager.cancel_job.return_value = True

        # Make request
        response = client.delete(f"/api/indexing/jobs/{test_job.id}")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == test_job.id
        assert data["cancelled"] is True
        assert "cancelled" in data["message"]

        # Verify mocks called
        mock_indexing_manager.get_job.assert_called_once_with(test_job.id)
        mock_indexing_manager.cancel_job.assert_called_once_with(test_job.id)

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_cancel_indexing_job_not_found(self, mock_indexing_manager, client):
        """Test cancelling non-existent indexing job."""
        # Setup mocks
        mock_indexing_manager.get_job.return_value = None

        # Make request
        response = client.delete("/api/indexing/jobs/non-existent-id")

        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_retry_indexing_job(self, mock_indexing_manager, client, test_job):
        """Test retrying indexing job."""
        # Setup job as failed but retryable
        test_job.fail_job("Test error")

        # Setup mocks
        mock_indexing_manager.get_job.return_value = test_job
        mock_indexing_manager.retry_job.return_value = True

        # Make request
        response = client.post(f"/api/indexing/jobs/{test_job.id}/retry")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_job.id

        # Verify mocks called
        mock_indexing_manager.get_job.assert_called_with(test_job.id)
        mock_indexing_manager.retry_job.assert_called_once_with(test_job.id)

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_retry_indexing_job_cannot_retry(self, mock_indexing_manager, client, test_job):
        """Test retrying job that cannot be retried."""
        # Setup job as completed (cannot retry)
        test_job.complete_job()

        # Setup mocks
        mock_indexing_manager.get_job.return_value = test_job

        # Make request
        response = client.post(f"/api/indexing/jobs/{test_job.id}/retry")

        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert "cannot be retried" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_get_workspace_indexing_jobs(
        self, mock_workspace_manager, mock_indexing_manager, client, test_workspace, test_job
    ):
        """Test getting indexing jobs for a workspace."""
        # Setup mocks
        mock_workspace_manager.get_workspace.return_value = test_workspace
        mock_indexing_manager.get_jobs_for_workspace.return_value = [test_job]

        # Make request
        response = client.get(f"/api/indexing/workspaces/{test_workspace.id}/jobs")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_job.id

        # Verify mocks called
        mock_workspace_manager.get_workspace.assert_called_once_with(test_workspace.id)
        mock_indexing_manager.get_jobs_for_workspace.assert_called_once_with(test_workspace.id)

    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_get_workspace_indexing_jobs_workspace_not_found(self, mock_workspace_manager, client):
        """Test getting jobs for non-existent workspace."""
        # Setup mocks
        mock_workspace_manager.get_workspace.return_value = None

        # Make request
        response = client.get("/api/indexing/workspaces/non-existent-id/jobs")

        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("error", data.get("detail", ""))

    @patch("src.graphrag_api_service.main.indexing_manager")
    def test_get_indexing_stats(self, mock_indexing_manager, client):
        """Test getting indexing statistics."""
        # Setup mocks
        stats = IndexingStats(
            total_jobs=5,
            queued_jobs=1,
            running_jobs=1,
            completed_jobs=2,
            failed_jobs=1,
            cancelled_jobs=0,
            avg_completion_time=120.5,
            success_rate=0.67,
            recent_jobs=3,
            recent_completions=2,
        )
        mock_indexing_manager.get_indexing_stats.return_value = stats

        # Make request
        response = client.get("/api/indexing/stats")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 5
        assert data["queued_jobs"] == 1
        assert data["running_jobs"] == 1
        assert data["completed_jobs"] == 2
        assert data["failed_jobs"] == 1
        assert data["success_rate"] == 0.67

        # Verify mock called
        mock_indexing_manager.get_indexing_stats.assert_called_once()


class TestIndexingAPIIntegration:
    """Integration tests for indexing API endpoints."""

    @patch("src.graphrag_api_service.main.indexing_manager")
    @patch("src.graphrag_api_service.main.workspace_manager")
    def test_complete_indexing_workflow(
        self, mock_workspace_manager, mock_indexing_manager, client, test_workspace
    ):
        """Test complete indexing workflow through API."""
        # Setup workspace
        mock_workspace_manager.get_workspace.return_value = test_workspace
        mock_workspace_manager._save_workspaces_index.return_value = None

        # Create job
        test_job = IndexingJob(
            workspace_id=test_workspace.id,
            started_at=None,
            completed_at=None,
            error_message=None,
        )
        mock_indexing_manager.create_indexing_job.return_value = test_job
        mock_indexing_manager.get_job.return_value = test_job

        # Step 1: Create indexing job
        create_response = client.post(
            "/api/indexing/jobs", json={"workspace_id": test_workspace.id, "priority": 5}
        )
        assert create_response.status_code == 200
        job_data = create_response.json()
        job_id = job_data["id"]

        # Step 2: Get job status
        get_response = client.get(f"/api/indexing/jobs/{job_id}")
        assert get_response.status_code == 200

        # Step 3: Simulate job failure and retry
        test_job.fail_job("Test error")
        mock_indexing_manager.retry_job.return_value = True

        retry_response = client.post(f"/api/indexing/jobs/{job_id}/retry")
        assert retry_response.status_code == 200

        # Step 4: Cancel job
        mock_indexing_manager.cancel_job.return_value = True

        cancel_response = client.delete(f"/api/indexing/jobs/{job_id}")
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert cancel_data["cancelled"] is True
