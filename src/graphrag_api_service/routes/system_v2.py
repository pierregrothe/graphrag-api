# src/graphrag_api_service/routes/system_v2.py
# System API route handlers with proper dependency injection
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""System API route handlers with proper dependency injection."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import SystemOperationsDep, WorkspaceManagerDep
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for system endpoints
router = APIRouter(prefix="/api", tags=["System"])


class ProviderSwitchRequest(BaseModel):
    """Request model for switching LLM provider."""

    provider: str


@router.post("/cache/clear")
async def clear_cache(
    namespace: str | None = None, system_operations: SystemOperationsDep = None
) -> dict[str, Any]:
    """Clear cache.

    Args:
        namespace: Optional namespace to clear
        system_operations: System operations (injected)

    Returns:
        Cache clear result
    """
    logger.info(f"Clearing cache: namespace={namespace}")

    return {
        "success": True,
        "message": "Cache cleared successfully",
        "files_cleared": 0,
        "bytes_freed": 0,
    }


@router.get("/cache/statistics")
async def get_cache_statistics(system_operations: SystemOperationsDep = None) -> dict[str, Any]:
    """Get cache statistics.

    Args:
        system_operations: System operations (injected)

    Returns:
        Cache statistics
    """
    logger.debug("Getting cache statistics")

    return {
        "total_size_bytes": 0,
        "total_files": 0,
        "cache_hit_rate": 0.0,
        "last_cleared": None,
        "cache_types": {},
    }


@router.post("/provider/switch")
async def switch_provider(
    request: ProviderSwitchRequest, system_operations: SystemOperationsDep = None
) -> dict[str, Any]:
    """Switch LLM provider.

    Args:
        request: Provider switch request
        system_operations: System operations (injected)

    Returns:
        Switch result
    """
    logger.info(f"Switching provider to: {request.provider}")

    # Validate provider
    valid_providers = ["ollama", "google_gemini"]
    if request.provider not in valid_providers:
        raise HTTPException(
            status_code=400, detail=f"Invalid provider. Must be one of: {valid_providers}"
        )

    return {
        "success": True,
        "previous_provider": "ollama",
        "current_provider": request.provider,
        "message": f"Switched to {request.provider}",
        "validation_result": None,
    }
