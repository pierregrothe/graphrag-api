# src/graphrag_api_service/routes/indexing.py
# Indexing API route handlers
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Indexing API route handlers for job management and statistics."""

from typing import Any

from fastapi import APIRouter, HTTPException

from ..indexing.models import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobStatus,
    IndexingJobSummary,
    IndexingStats,
)
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for indexing endpoints
router = APIRouter(prefix="/api", tags=["Indexing"])


# Dependency injection function (to be called from main.py)
def setup_indexing_routes(indexing_manager, workspace_manager):
    """Setup indexing routes with dependencies."""

    @router.post("/indexing/jobs", response_model=IndexingJob)
    async def create_indexing_job(request: IndexingJobCreate) -> IndexingJob:
        """Create a new indexing job for a workspace.

        Args:
            request: Job creation request

        Returns:
            Created indexing job

        Raises:
            HTTPException: If workspace not found or not ready for indexing
        """
        logger.info(f"Creating indexing job for workspace {request.workspace_id}")

        # Get workspace
        workspace = await workspace_manager.get_workspace(request.workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=404, detail=f"Workspace not found: {request.workspace_id}"
            )

        try:
            job = indexing_manager.create_indexing_job(request, workspace)

            # Update workspace status
            workspace.update_status(workspace.status)  # Trigger timestamp update
            workspace_manager._save_workspaces_index()

            logger.info(f"Created indexing job {job.id}")
            return job

        except ValueError as e:
            logger.error(f"Failed to create indexing job: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.get("/indexing/jobs", response_model=list[IndexingJobSummary])
    async def list_indexing_jobs(
        status: IndexingJobStatus | None = None, limit: int = 100
    ) -> list[IndexingJobSummary]:
        """List indexing jobs with optional status filter.

        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return

        Returns:
            List of job summaries
        """
        logger.info(f"Listing indexing jobs (status: {status}, limit: {limit})")

        jobs = indexing_manager.list_jobs(status=status, limit=limit)
        return jobs

    @router.get("/indexing/jobs/{job_id}", response_model=IndexingJob)
    async def get_indexing_job(job_id: str) -> IndexingJob:
        """Get indexing job by ID.

        Args:
            job_id: Job ID

        Returns:
            Indexing job details

        Raises:
            HTTPException: If job not found
        """
        logger.info(f"Getting indexing job {job_id}")

        job = indexing_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

        return job

    @router.delete("/indexing/jobs/{job_id}")
    async def cancel_indexing_job(job_id: str) -> dict[str, Any]:
        """Cancel an indexing job.

        Args:
            job_id: Job ID to cancel

        Returns:
            Cancellation result

        Raises:
            HTTPException: If job not found
        """
        logger.info(f"Cancelling indexing job {job_id}")

        job = indexing_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

        success = indexing_manager.cancel_job(job_id)

        return {
            "job_id": job_id,
            "cancelled": success,
            "message": f"Job {job_id} {'cancelled' if success else 'could not be cancelled'}",
        }

    @router.post("/indexing/jobs/{job_id}/retry", response_model=IndexingJob)
    async def retry_indexing_job(job_id: str) -> IndexingJob:
        """Retry a failed indexing job.

        Args:
            job_id: Job ID to retry

        Returns:
            Updated indexing job

        Raises:
            HTTPException: If job not found or cannot be retried
        """
        logger.info(f"Retrying indexing job {job_id}")

        job = indexing_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Indexing job not found: {job_id}")

        if not job.can_retry():
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} cannot be retried (status: {job.status}, retries: {job.retry_count}/{job.max_retries})",
            )

        success = indexing_manager.retry_job(job_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to retry job {job_id}")

        retried_job = indexing_manager.get_job(job_id)
        if not retried_job:
            raise HTTPException(status_code=404, detail=f"Job not found after retry: {job_id}")

        return retried_job

    @router.get("/indexing/workspaces/{workspace_id}/jobs", response_model=list[IndexingJob])
    async def get_workspace_indexing_jobs(workspace_id: str) -> list[IndexingJob]:
        """Get all indexing jobs for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of indexing jobs for the workspace

        Raises:
            HTTPException: If workspace not found
        """
        logger.info(f"Getting indexing jobs for workspace {workspace_id}")

        # Verify workspace exists
        workspace = await workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")

        jobs = indexing_manager.get_jobs_for_workspace(workspace_id)
        return jobs

    @router.get("/indexing/stats", response_model=IndexingStats)
    async def get_indexing_stats() -> IndexingStats:
        """Get indexing system statistics.

        Returns:
            Indexing statistics
        """
        logger.info("Getting indexing statistics")

        stats = indexing_manager.get_indexing_stats()
        return stats

    return router
