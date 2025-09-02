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

    if not system_operations:
        return {
            "success": False,
            "message": "System operations not available",
            "files_cleared": 0,
            "bytes_freed": 0,
            "error": "System operations not configured",
        }

    try:
        # Clear cache using system operations
        result = await system_operations.clear_cache(namespace=namespace)

        return {
            "success": True,
            "message": result.get("message", "Cache cleared successfully"),
            "files_cleared": result.get("files_cleared", 0),
            "bytes_freed": result.get("bytes_freed", 0),
            "namespace": namespace,
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return {
            "success": False,
            "message": f"Cache clear failed: {str(e)}",
            "files_cleared": 0,
            "bytes_freed": 0,
            "error": str(e),
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

    if not system_operations:
        return {
            "total_size_bytes": 0,
            "total_files": 0,
            "cache_hit_rate": 0.0,
            "last_cleared": None,
            "cache_types": {},
            "error": "System operations not available",
        }

    try:
        # Get cache statistics from system operations
        result = await system_operations.get_cache_statistics()

        return {
            "total_size_bytes": result.get("total_size_bytes", 0),
            "total_files": result.get("total_files", 0),
            "cache_hit_rate": result.get("cache_hit_rate", 0.0),
            "last_cleared": result.get("last_cleared"),
            "cache_types": result.get("cache_types", {}),
            "namespaces": result.get("namespaces", []),
        }

    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        return {
            "total_size_bytes": 0,
            "total_files": 0,
            "cache_hit_rate": 0.0,
            "last_cleared": None,
            "cache_types": {},
            "error": str(e),
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

    if not system_operations:
        return {
            "success": False,
            "previous_provider": None,
            "current_provider": request.provider,
            "message": "System operations not available",
            "validation_result": None,
            "error": "System operations not configured",
        }

    try:
        # Switch provider using system operations
        result = await system_operations.switch_llm_provider(request.provider)

        return {
            "success": True,
            "previous_provider": result.get("previous_provider"),
            "current_provider": request.provider,
            "message": result.get("message", f"Switched to {request.provider}"),
            "validation_result": result.get("validation_result"),
            "provider_config": result.get("provider_config"),
        }

    except Exception as e:
        logger.error(f"Failed to switch provider: {e}")
        return {
            "success": False,
            "previous_provider": None,
            "current_provider": request.provider,
            "message": f"Provider switch failed: {str(e)}",
            "validation_result": None,
            "error": str(e),
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

    if not system_operations:
        return {
            "status": "degraded",
            "timestamp": "2025-09-01T00:00:00Z",
            "components": {},
            "provider": {"healthy": False, "error": "System operations not available"},
            "graphrag": {"available": False},
            "workspaces": {"total": 0},
            "graph_data": {"path_configured": False},
            "system_resources": {"cpu_percent": 0.0},
            "error": "System operations not configured",
        }

    try:
        # Get advanced health information from system operations
        result = await system_operations.get_advanced_health()

        return {
            "status": result.get("status", "healthy"),
            "timestamp": result.get("timestamp"),
            "components": result.get("components", {}),
            "provider": result.get("provider", {"healthy": True}),
            "graphrag": result.get("graphrag", {"available": True}),
            "workspaces": result.get("workspaces", {"total": 0}),
            "graph_data": result.get("graph_data", {"path_configured": False}),
            "system_resources": result.get("system_resources", {"cpu_percent": 0.0}),
            "database": result.get("database", {"connected": False}),
            "cache": result.get("cache", {"available": False}),
        }

    except Exception as e:
        logger.error(f"Failed to get advanced health: {e}")
        return {
            "status": "error",
            "timestamp": "2025-09-01T00:00:00Z",
            "components": {},
            "provider": {"healthy": False, "error": str(e)},
            "graphrag": {"available": False},
            "workspaces": {"total": 0},
            "graph_data": {"path_configured": False},
            "system_resources": {"cpu_percent": 0.0},
            "error": str(e),
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

    if not system_operations:
        return {
            "version": "0.1.0",
            "environment": "development",
            "uptime_seconds": 0.0,
            "provider_info": {"provider": "unknown", "error": "System operations not available"},
            "graph_metrics": {"total_entities": 0},
            "indexing_metrics": {"total_jobs": 0},
            "query_metrics": {"total_queries": 0},
            "workspace_metrics": {"total_workspaces": 0},
            "recent_operations": [],
            "error": "System operations not configured",
        }

    try:
        # Get enhanced status from system operations
        result = await system_operations.get_enhanced_status()

        return {
            "version": result.get("version", "0.1.0"),
            "environment": result.get("environment", "development"),
            "uptime_seconds": result.get("uptime_seconds", 0.0),
            "provider_info": result.get("provider_info", {"provider": "unknown"}),
            "graph_metrics": result.get("graph_metrics", {"total_entities": 0}),
            "indexing_metrics": result.get("indexing_metrics", {"total_jobs": 0}),
            "query_metrics": result.get("query_metrics", {"total_queries": 0}),
            "workspace_metrics": result.get("workspace_metrics", {"total_workspaces": 0}),
            "recent_operations": result.get("recent_operations", []),
            "database_info": result.get("database_info", {"connected": False}),
            "cache_info": result.get("cache_info", {"available": False}),
        }

    except Exception as e:
        logger.error(f"Failed to get enhanced status: {e}")
        return {
            "version": "0.1.0",
            "environment": "development",
            "uptime_seconds": 0.0,
            "provider_info": {"provider": "unknown", "error": str(e)},
            "graph_metrics": {"total_entities": 0},
            "indexing_metrics": {"total_jobs": 0},
            "query_metrics": {"total_queries": 0},
            "workspace_metrics": {"total_workspaces": 0},
            "recent_operations": [],
            "error": str(e),
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

    if not system_operations:
        return {
            "valid": False,
            "config_type": config_type,
            "errors": ["System operations not available"],
            "warnings": [],
            "suggestions": ["Configure system operations"],
            "validated_config": None,
            "error": "System operations not configured",
        }

    try:
        # Validate configuration using system operations
        result = await system_operations.validate_configuration(
            config_type=config_type, strict_mode=strict_mode
        )

        return {
            "valid": result.get("valid", True),
            "config_type": config_type,
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "suggestions": result.get("suggestions", []),
            "validated_config": result.get("validated_config"),
            "validation_details": result.get("validation_details", {}),
        }

    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        return {
            "valid": False,
            "config_type": config_type,
            "errors": [str(e)],
            "warnings": [],
            "suggestions": [],
            "validated_config": None,
            "error": str(e),
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

    if not system_operations:
        return {
            "success": False,
            "message": "System operations not available",
            "files_cleared": 0,
            "bytes_freed": 0,
            "error": "System operations not configured",
        }

    try:
        # Delete cache using system operations
        result = await system_operations.delete_cache()

        return {
            "success": True,
            "message": result.get("message", "Cache deleted successfully"),
            "files_cleared": result.get("files_cleared", 0),
            "bytes_freed": result.get("bytes_freed", 0),
            "cache_types_cleared": result.get("cache_types_cleared", []),
        }

    except Exception as e:
        logger.error(f"Failed to delete cache: {e}")
        return {
            "success": False,
            "message": f"Cache deletion failed: {str(e)}",
            "files_cleared": 0,
            "bytes_freed": 0,
            "error": str(e),
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
