# src/graphrag_api_service/routes/system.py
# System API route handlers
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""System API route handlers for health checks, info, and system operations."""

import gc
import time
from typing import Any

import psutil
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..logging_config import get_logger

logger = get_logger(__name__)

# Create router for system endpoints
router = APIRouter(prefix="/api", tags=["System"])


# Dependency injection function (to be called from main.py)
def setup_system_routes(workspace_manager, system_operations=None):
    """Setup system routes with dependencies."""

    @router.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Dict containing health status
        """
        logger.debug("Health check accessed")
        return {"status": "healthy"}

    @router.get("/health/detailed", tags=["Health"])
    async def detailed_health_check() -> dict[str, Any]:
        """Detailed health check with component status.

        Returns:
            Dict containing detailed health information
        """
        logger.info("Detailed health check requested")

        try:
            # Get system metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu_percent = psutil.cpu_percent(interval=1)

            # Check workspace manager
            workspace_stats = workspace_manager.get_workspace_stats()

            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "system": {
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used,
                    },
                    "disk": {
                        "total": disk.total,
                        "free": disk.free,
                        "used": disk.used,
                        "percent": (disk.used / disk.total) * 100,
                    },
                    "cpu_percent": cpu_percent,
                },
                "components": {
                    "workspace_manager": {
                        "status": "healthy",
                        "workspaces": workspace_stats,
                    },
                    "graphrag": {
                        "status": "configured" if settings.graphrag_data_path else "not_configured",
                        "data_path": settings.graphrag_data_path,
                    },
                },
            }

            return health_data

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e),
            }

    @router.get("/health/database", tags=["Health"])
    async def database_health_check() -> dict[str, Any]:
        """Database connectivity health check.

        Returns:
            Dict containing database health status
        """
        logger.info("Database health check requested")

        try:
            # For now, return basic status since we're using file-based storage
            return {
                "status": "healthy",
                "type": "file_based",
                "message": "Using file-based storage for workspaces and jobs",
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    @router.get("/health/memory", tags=["Health"])
    async def memory_health_check() -> dict[str, Any]:
        """Memory usage health check.

        Returns:
            Dict containing memory health status
        """
        logger.info("Memory health check requested")

        try:
            memory = psutil.virtual_memory()

            # Determine status based on memory usage
            if memory.percent > 90:
                status = "critical"
            elif memory.percent > 80:
                status = "warning"
            else:
                status = "healthy"

            return {
                "status": status,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "thresholds": {
                    "warning": 80,
                    "critical": 90,
                },
            }
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @router.get("/info", tags=["Information"])
    async def get_info() -> dict[str, Any]:
        """Get application information and configuration.

        Returns:
            Dict containing application information
        """
        logger.info("Application info requested")

        return {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.log_level,
            "graphrag_config_path": settings.graphrag_config_path,
            "graphrag_data_path": settings.graphrag_data_path,
            "llm_provider_info": settings.get_provider_info(),
        }

    @router.post("/system/memory/optimize", tags=["System"])
    async def optimize_memory() -> dict[str, Any]:
        """Trigger memory optimization and garbage collection.

        Returns:
            Dict containing optimization results
        """
        logger.info("Memory optimization requested")

        try:
            # Get memory before optimization
            memory_before = psutil.virtual_memory()

            # Force garbage collection
            collected = gc.collect()

            # Get memory after optimization
            memory_after = psutil.virtual_memory()

            return {
                "status": "completed",
                "objects_collected": collected,
                "memory_before": {
                    "used": memory_before.used,
                    "percent": memory_before.percent,
                },
                "memory_after": {
                    "used": memory_after.used,
                    "percent": memory_after.percent,
                },
                "memory_freed": memory_before.used - memory_after.used,
            }
        except Exception as e:
            logger.error(f"Failed to optimize memory: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to optimize memory: {e}")

    return router
