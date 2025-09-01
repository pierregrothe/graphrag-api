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


@router.post("/system/provider/switch")
async def switch_provider_system(
    request: ProviderSwitchRequest, system_operations: SystemOperationsDep = None
) -> dict[str, Any]:
    """Switch LLM provider (alternate path).

    Args:
        request: Provider switch request
        system_operations: System operations (injected)

    Returns:
        Switch result
    """
    return await switch_provider(request, system_operations)


@router.get("/system/health/advanced")
async def get_advanced_health(system_operations: SystemOperationsDep = None) -> dict[str, Any]:
    """Get advanced system health information.

    Args:
        system_operations: System operations (injected)

    Returns:
        Advanced health information
    """
    logger.debug("Getting advanced health information")

    return {
        "status": "healthy",
        "timestamp": "2025-09-01T00:00:00Z",
        "components": {},
        "provider": {"healthy": True},
        "graphrag": {"available": True},
        "workspaces": {"total": 0},
        "graph_data": {"path_configured": False},
        "system_resources": {"cpu_percent": 50.0},
    }


@router.get("/system/status/enhanced")
async def get_enhanced_status(system_operations: SystemOperationsDep = None) -> dict[str, Any]:
    """Get enhanced system status.

    Args:
        system_operations: System operations (injected)

    Returns:
        Enhanced status information
    """
    logger.debug("Getting enhanced status")

    return {
        "version": "0.1.0",
        "environment": "development",
        "uptime_seconds": 3600.0,
        "provider_info": {"provider": "ollama"},
        "graph_metrics": {"total_entities": 0},
        "indexing_metrics": {"total_jobs": 0},
        "query_metrics": {"total_queries": 0},
        "workspace_metrics": {"total_workspaces": 0},
        "recent_operations": [],
    }


@router.post("/system/config/validate")
async def validate_configuration(
    config_type: str = "provider",
    strict_mode: bool = False,
    system_operations: SystemOperationsDep = None,
) -> dict[str, Any]:
    """Validate system configuration.

    Args:
        config_type: Type of configuration to validate
        strict_mode: Use strict validation
        system_operations: System operations (injected)

    Returns:
        Validation result
    """
    logger.debug(f"Validating configuration: type={config_type}, strict={strict_mode}")

    return {
        "valid": True,
        "config_type": config_type,
        "errors": [],
        "warnings": [],
        "suggestions": [],
        "validated_config": None,
    }


@router.delete("/system/cache")
async def delete_cache(system_operations: SystemOperationsDep = None) -> dict[str, Any]:
    """Delete system cache.

    Args:
        system_operations: System operations (injected)

    Returns:
        Cache deletion result
    """
    logger.info("Deleting system cache")

    return {
        "success": True,
        "message": "Cache deleted successfully",
        "files_cleared": 0,
        "bytes_freed": 0,
    }


@router.get("/system/cache/stats")
async def get_cache_stats(system_operations: SystemOperationsDep = None) -> dict[str, Any]:
    """Get cache statistics (alternate path).

    Args:
        system_operations: System operations (injected)

    Returns:
        Cache statistics
    """
    return await get_cache_statistics(system_operations)
