# src/graphrag_api_service/indexing/manager.py
# GraphRAG indexing manager implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Manager for GraphRAG indexing operations with job queuing and background processing."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..config import Settings
from ..workspace.models import Workspace, WorkspaceConfig
from .models import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobStatus,
    IndexingJobSummary,
    IndexingStats,
)
from .tasks import IndexingTask

logger = logging.getLogger(__name__)


class IndexingManager:
    """Manager for GraphRAG indexing operations."""

    def __init__(self, settings: Settings):
        """Initialize indexing manager.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.jobs_dir = Path("indexing_jobs")
        self.jobs_index_file = self.jobs_dir / "jobs.json"

        # Ensure jobs directory exists
        self.jobs_dir.mkdir(exist_ok=True)

        # Job storage and tracking
        self._jobs: dict[str, IndexingJob] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._running_jobs: set[str] = set()

        # Configuration
        self.max_concurrent_jobs = 2  # Maximum concurrent indexing jobs
        self.job_cleanup_hours = 48  # Hours to keep completed job records

        # Background task for processing queue
        self._queue_processor_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Load existing jobs
        self._load_jobs_index()

    async def start(self) -> None:
        """Start the indexing manager and queue processor."""
        logger.info("Starting indexing manager")

        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Stop the indexing manager and cancel running jobs."""
        logger.info("Stopping indexing manager")

        self._shutdown_event.set()

        # Cancel queue processor
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass

        # Cancel active indexing tasks
        for job_id, task in self._active_tasks.items():
            if not task.done():
                logger.info(f"Cancelling indexing job {job_id}")
                task.cancel()

                # Mark job as cancelled
                if job_id in self._jobs:
                    self._jobs[job_id].cancel_job()

        # Wait for tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)

        self._active_tasks.clear()
        self._running_jobs.clear()

        # Save final state
        self._save_jobs_index()

    def create_indexing_job(self, request: IndexingJobCreate, workspace: Workspace) -> IndexingJob:
        """Create a new indexing job.

        Args:
            request: Job creation request
            workspace: Workspace to index

        Returns:
            Created indexing job

        Raises:
            ValueError: If workspace is not ready for indexing
        """
        if not workspace.is_ready_for_indexing():
            raise ValueError(
                f"Workspace {workspace.config.name} is not ready for indexing "
                f"(status: {workspace.status})"
            )

        # Check if workspace already has a running job
        existing_job = self.get_active_job_for_workspace(request.workspace_id)
        if existing_job:
            raise ValueError(
                f"Workspace {workspace.config.name} already has an active indexing job"
            )

        # Create job
        job = IndexingJob(
            workspace_id=request.workspace_id,
            priority=request.priority or 5,
            max_retries=request.max_retries or 3,
            started_at=None,
            completed_at=None,
            error_message=None,
        )

        # Store job
        self._jobs[job.id] = job
        self._save_jobs_index()

        logger.info(f"Created indexing job {job.id} for workspace {workspace.config.name}")
        return job

    def get_job(self, job_id: str) -> IndexingJob | None:
        """Get indexing job by ID.

        Args:
            job_id: Job ID

        Returns:
            Indexing job or None if not found
        """
        return self._jobs.get(job_id)

    def get_jobs_for_workspace(self, workspace_id: str) -> list[IndexingJob]:
        """Get all jobs for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of indexing jobs
        """
        return [job for job in self._jobs.values() if job.workspace_id == workspace_id]

    def get_active_job_for_workspace(self, workspace_id: str) -> IndexingJob | None:
        """Get active job for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            Active indexing job or None
        """
        for job in self._jobs.values():
            if job.workspace_id == workspace_id and job.is_active:
                return job
        return None

    def list_jobs(
        self, status: IndexingJobStatus | None = None, limit: int = 100
    ) -> list[IndexingJobSummary]:
        """List indexing jobs with optional status filter.

        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return

        Returns:
            List of job summaries
        """
        jobs = list(self._jobs.values())

        if status:
            jobs = [job for job in jobs if job.status == status]

        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Limit results
        jobs = jobs[:limit]

        # Convert to summaries
        summaries = []
        for job in jobs:
            summary = IndexingJobSummary(
                id=job.id,
                workspace_id=job.workspace_id,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                overall_progress=job.progress.overall_progress,
                current_stage=job.progress.current_stage,
                error_message=job.error_message,
            )
            summaries.append(summary)

        return summaries

    def cancel_job(self, job_id: str) -> bool:
        """Cancel an indexing job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status == IndexingJobStatus.RUNNING:
            # Cancel active task
            task = self._active_tasks.get(job_id)
            if task and not task.done():
                task.cancel()

            self._running_jobs.discard(job_id)

        job.cancel_job()
        self._save_jobs_index()

        logger.info(f"Cancelled indexing job {job_id}")
        return True

    def retry_job(self, job_id: str) -> bool:
        """Retry a failed indexing job.

        Args:
            job_id: Job ID to retry

        Returns:
            True if job was queued for retry
        """
        job = self._jobs.get(job_id)
        if not job or not job.can_retry():
            return False

        job.increment_retry()
        self._save_jobs_index()

        logger.info(f"Queued job {job_id} for retry (attempt {job.retry_count})")
        return True

    def get_indexing_stats(self) -> IndexingStats:
        """Get indexing statistics.

        Returns:
            Indexing statistics
        """
        jobs = list(self._jobs.values())
        total_jobs = len(jobs)

        # Count by status
        status_counts = {
            IndexingJobStatus.QUEUED: 0,
            IndexingJobStatus.RUNNING: 0,
            IndexingJobStatus.COMPLETED: 0,
            IndexingJobStatus.FAILED: 0,
            IndexingJobStatus.CANCELLED: 0,
        }

        completed_jobs = []
        recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent_jobs = 0
        recent_completions = 0

        for job in jobs:
            status_counts[job.status] += 1

            if job.status == IndexingJobStatus.COMPLETED:
                completed_jobs.append(job)

            if job.created_at >= recent_cutoff:
                recent_jobs += 1

                if job.completed_at and job.completed_at >= recent_cutoff:
                    recent_completions += 1

        # Calculate average completion time
        avg_completion_time = None
        if completed_jobs:
            completion_times = [
                job.duration_seconds for job in completed_jobs if job.duration_seconds
            ]
            if completion_times:
                avg_completion_time = sum(completion_times) / len(completion_times)

        # Calculate success rate
        finished_jobs = (
            status_counts[IndexingJobStatus.COMPLETED] + status_counts[IndexingJobStatus.FAILED]
        )
        success_rate = 0.0
        if finished_jobs > 0:
            success_rate = status_counts[IndexingJobStatus.COMPLETED] / finished_jobs

        return IndexingStats(
            total_jobs=total_jobs,
            queued_jobs=status_counts[IndexingJobStatus.QUEUED],
            running_jobs=status_counts[IndexingJobStatus.RUNNING],
            completed_jobs=status_counts[IndexingJobStatus.COMPLETED],
            failed_jobs=status_counts[IndexingJobStatus.FAILED],
            cancelled_jobs=status_counts[IndexingJobStatus.CANCELLED],
            avg_completion_time=avg_completion_time,
            success_rate=success_rate,
            recent_jobs=recent_jobs,
            recent_completions=recent_completions,
        )

    async def _process_queue(self) -> None:
        """Background task to process the job queue."""
        logger.info("Starting indexing queue processor")

        try:
            while not self._shutdown_event.is_set():
                # Clean up old jobs
                self._cleanup_old_jobs()

                # Process queued jobs
                await self._process_queued_jobs()

                # Clean up completed tasks
                self._cleanup_completed_tasks()

                # Wait before next iteration
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=5.0)
                    break  # Shutdown requested
                except TimeoutError:
                    continue  # Continue processing

        except Exception as e:
            logger.error(f"Queue processor error: {e}")

        logger.info("Queue processor stopped")

    async def _process_queued_jobs(self) -> None:
        """Process queued jobs up to the concurrency limit."""
        if len(self._running_jobs) >= self.max_concurrent_jobs:
            return

        # Get queued jobs sorted by priority and creation time
        queued_jobs = [job for job in self._jobs.values() if job.status == IndexingJobStatus.QUEUED]

        queued_jobs.sort(key=lambda j: (j.priority, j.created_at))

        # Start jobs up to concurrency limit
        for job in queued_jobs:
            if len(self._running_jobs) >= self.max_concurrent_jobs:
                break

            try:
                await self._start_indexing_job(job)
            except Exception as e:
                logger.error(f"Failed to start job {job.id}: {e}")
                job.fail_job(f"Failed to start: {e}")

    async def _start_indexing_job(self, job: IndexingJob) -> None:
        """Start an indexing job.

        Args:
            job: Job to start
        """
        # Get workspace (would be injected in real implementation)
        # For now, create a mock workspace with minimal config
        mock_config = WorkspaceConfig(
            name=f"workspace-{job.workspace_id}",
            description="Mock workspace for indexing",
            data_path="/tmp/mock_data",
            output_path=None,
            llm_model_override=None,
            embedding_model_override=None,
        )
        workspace = Workspace(
            id=job.workspace_id,
            config=mock_config,
            last_error=None,
            workspace_path=None,
            config_file_path=None,
            expires_at=None,
        )

        # Create indexing task
        indexing_task = IndexingTask(self.settings, workspace)

        # Create and start background task
        task = asyncio.create_task(self._execute_job(job, indexing_task))
        self._active_tasks[job.id] = task
        self._running_jobs.add(job.id)

        logger.info(f"Started indexing job {job.id}")

    async def _execute_job(self, job: IndexingJob, indexing_task: IndexingTask) -> None:
        """Execute an indexing job with error handling.

        Args:
            job: Job to execute
            indexing_task: Task executor
        """
        try:
            await indexing_task.execute_indexing(job)
            logger.info(f"Job {job.id} completed successfully")

        except asyncio.CancelledError:
            logger.info(f"Job {job.id} was cancelled")
            job.cancel_job()

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.fail_job(str(e))

        finally:
            self._running_jobs.discard(job.id)
            self._save_jobs_index()

    def _cleanup_completed_tasks(self) -> None:
        """Clean up completed asyncio tasks."""
        completed_job_ids = []

        for job_id, task in self._active_tasks.items():
            if task.done():
                completed_job_ids.append(job_id)

        for job_id in completed_job_ids:
            del self._active_tasks[job_id]

    def _cleanup_old_jobs(self) -> None:
        """Remove old completed job records."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=self.job_cleanup_hours)

        job_ids_to_remove = []
        for job_id, job in self._jobs.items():
            if job.is_finished and job.completed_at and job.completed_at < cutoff_time:
                job_ids_to_remove.append(job_id)

        if job_ids_to_remove:
            for job_id in job_ids_to_remove:
                del self._jobs[job_id]

            self._save_jobs_index()
            logger.info(f"Cleaned up {len(job_ids_to_remove)} old job records")

    def _load_jobs_index(self) -> None:
        """Load jobs index from disk."""
        if not self.jobs_index_file.exists():
            self._save_jobs_index()
            return

        try:
            with open(self.jobs_index_file, encoding="utf-8") as f:
                data = json.load(f)

            for job_data in data.get("jobs", []):
                job = IndexingJob(**job_data)
                self._jobs[job.id] = job

                # Reset running jobs to queued on startup
                if job.status == IndexingJobStatus.RUNNING:
                    job.status = IndexingJobStatus.QUEUED
                    job.started_at = None

            logger.info(f"Loaded {len(self._jobs)} indexing jobs from disk")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load jobs index: {e}")
            self._jobs = {}

    def _save_jobs_index(self) -> None:
        """Save jobs index to disk."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(UTC).isoformat(),
            "jobs": [job.model_dump() for job in self._jobs.values()],
        }

        with open(self.jobs_index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
