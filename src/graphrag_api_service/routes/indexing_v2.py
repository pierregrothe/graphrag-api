# src/graphrag_api_service/routes/indexing_v2.py
# Indexing API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Indexing API route handlers with proper dependency injection."""

from typing import Any

from fastapi import APIRouter

from ..deps import IndexingManagerDep, WorkspaceManagerDep
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for indexing endpoints
router = APIRouter(prefix="/api/indexing", tags=["Indexing"])


@router.get("/jobs")
async def get_indexing_jobs(indexing_manager: IndexingManagerDep = None) -> list[dict[str, Any]]:
    """Get indexing jobs.

    Args:
        indexing_manager: Indexing manager (injected)

    Returns:
        List of indexing jobs
    """
    logger.debug("Getting indexing jobs")

    # Return empty list for now
    return []
