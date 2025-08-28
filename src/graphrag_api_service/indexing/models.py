# src/graphrag_api_service/indexing/models.py
# GraphRAG indexing data models
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Data models for GraphRAG indexing operations."""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IndexingJobStatus(str, Enum):
    """Status of an indexing job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IndexingStage(str, Enum):
    """Stages of the indexing process."""

    INITIALIZATION = "initialization"
    TEXT_PROCESSING = "text_processing"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    COMMUNITY_DETECTION = "community_detection"
    EMBEDDING_GENERATION = "embedding_generation"
    INDEX_CREATION = "index_creation"
    FINALIZATION = "finalization"


class IndexingProgress(BaseModel):
    """Progress tracking for indexing operations."""

    # Current stage information
    current_stage: IndexingStage = Field(
        default=IndexingStage.INITIALIZATION, description="Current processing stage"
    )
    stage_progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Progress within current stage (0-1)"
    )
    overall_progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall job progress (0-1)"
    )

    # File processing statistics
    total_files: int = Field(default=0, description="Total number of files to process")
    processed_files: int = Field(default=0, description="Number of files processed")

    # Entity and relationship statistics
    entities_extracted: int = Field(default=0, description="Number of entities extracted")
    relationships_extracted: int = Field(default=0, description="Number of relationships extracted")
    communities_detected: int = Field(default=0, description="Number of communities detected")

    # Performance metrics
    processing_rate: float | None = Field(None, description="Files processed per second")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")

    # Stage details
    stage_details: dict[str, Any] = Field(
        default_factory=dict, description="Stage-specific details"
    )


class IndexingJob(BaseModel):
    """Represents an indexing job for a GraphRAG workspace."""

    # Job identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job ID")
    workspace_id: str = Field(..., description="ID of the workspace being indexed")

    # Job status and timing
    status: IndexingJobStatus = Field(
        default=IndexingJobStatus.QUEUED, description="Current job status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Job creation timestamp"
    )
    started_at: datetime | None = Field(None, description="Job start timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")

    # Progress tracking
    progress: IndexingProgress = Field(
        default_factory=lambda: IndexingProgress(processing_rate=None, estimated_completion=None),
        description="Current progress information",
    )

    # Error handling
    error_message: str | None = Field(None, description="Error message if job failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    # Configuration
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1=highest, 10=lowest)")

    def start_job(self) -> None:
        """Mark job as started."""
        self.status = IndexingJobStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete_job(self) -> None:
        """Mark job as completed."""
        self.status = IndexingJobStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.progress.overall_progress = 1.0

    def fail_job(self, error_message: str) -> None:
        """Mark job as failed with error message."""
        self.status = IndexingJobStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error_message = error_message

    def cancel_job(self) -> None:
        """Mark job as cancelled."""
        self.status = IndexingJobStatus.CANCELLED
        self.completed_at = datetime.now(UTC)

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.status == IndexingJobStatus.FAILED and self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry count and reset status."""
        if self.can_retry():
            self.retry_count += 1
            self.status = IndexingJobStatus.QUEUED
            self.started_at = None
            self.completed_at = None
            self.error_message = None

    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in [IndexingJobStatus.QUEUED, IndexingJobStatus.RUNNING]

    @property
    def is_finished(self) -> bool:
        """Check if job has finished (completed, failed, or cancelled)."""
        return self.status in [
            IndexingJobStatus.COMPLETED,
            IndexingJobStatus.FAILED,
            IndexingJobStatus.CANCELLED,
        ]

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None

        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()


class IndexingJobSummary(BaseModel):
    """Summary information for an indexing job."""

    id: str = Field(..., description="Job ID")
    workspace_id: str = Field(..., description="Workspace ID")
    status: IndexingJobStatus = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Creation time")
    started_at: datetime | None = Field(None, description="Start time")
    completed_at: datetime | None = Field(None, description="Completion time")
    overall_progress: float = Field(..., description="Overall progress (0-1)")
    current_stage: IndexingStage = Field(..., description="Current processing stage")
    error_message: str | None = Field(None, description="Error message if failed")


class IndexingJobCreate(BaseModel):
    """Request model for creating an indexing job."""

    workspace_id: str = Field(..., description="ID of workspace to index")
    priority: int | None = Field(5, ge=1, le=10, description="Job priority (1=highest, 10=lowest)")
    max_retries: int | None = Field(3, ge=0, le=10, description="Maximum retry attempts")


class IndexingStats(BaseModel):
    """Statistics for indexing operations."""

    total_jobs: int = Field(..., description="Total number of jobs")
    queued_jobs: int = Field(..., description="Number of queued jobs")
    running_jobs: int = Field(..., description="Number of running jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    cancelled_jobs: int = Field(..., description="Number of cancelled jobs")

    avg_completion_time: float | None = Field(
        None, description="Average completion time in seconds"
    )
    success_rate: float = Field(..., description="Success rate (0-1)")

    # Recent activity (last 24 hours)
    recent_jobs: int = Field(default=0, description="Jobs created in last 24 hours")
    recent_completions: int = Field(default=0, description="Jobs completed in last 24 hours")
