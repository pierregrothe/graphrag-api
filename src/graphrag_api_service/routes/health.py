# src/graphrag_api_service/routes/health.py
# Health check and monitoring endpoints
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Health check and monitoring endpoints."""

import platform
import time
from datetime import UTC, datetime
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..dependencies import get_service_container


class HealthStatus(BaseModel):
    """Health check status model."""

    status: str
    timestamp: str
    uptime: float
    version: str
    environment: str


class DetailedHealth(BaseModel):
    """Detailed health check model."""

    status: str
    timestamp: str
    uptime: float
    version: str
    environment: str
    system: dict[str, Any]
    services: dict[str, Any]
    performance: dict[str, Any]


class SystemInfo(BaseModel):
    """System information model."""

    platform: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    memory_percent: float
    disk_usage: dict[str, Any]


# Track application start time
START_TIME = time.time()


def create_health_router() -> APIRouter:
    """Create health check router."""
    router = APIRouter(prefix="/health", tags=["Health"])

    @router.get("/", response_model=HealthStatus)
    async def health_check() -> HealthStatus:
        """Basic health check endpoint."""
        return HealthStatus(
            status="healthy",
            timestamp=datetime.now(UTC).isoformat(),
            uptime=time.time() - START_TIME,
            version=settings.app_version,
            environment="production" if not settings.debug else "development",
        )

    @router.get("/live", response_model=dict)
    async def liveness_probe() -> dict:
        """Kubernetes liveness probe endpoint."""
        return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}

    @router.get("/ready", response_model=dict)
    async def readiness_probe(container=Depends(get_service_container)) -> dict:
        """Kubernetes readiness probe endpoint."""
        # Check if all services are ready
        checks = {
            "api": True,
            "database": False,
            "cache": False,
            "llm_provider": False,
        }

        # Check database
        try:
            if hasattr(container, "database_manager") and container.database_manager:
                # Simple connectivity check
                checks["database"] = True
        except Exception:
            pass

        # Check cache
        try:
            if hasattr(container, "cache_manager"):
                checks["cache"] = True
        except Exception:
            pass

        # Check LLM provider
        try:
            if hasattr(container, "graph_operations") and container.graph_operations:
                checks["llm_provider"] = True
        except Exception:
            pass

        # Determine overall readiness
        ready = all(checks.values()) or (checks["api"] and checks["llm_provider"])

        if not ready:
            raise HTTPException(status_code=503, detail={"ready": False, "checks": checks})

        return {
            "ready": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": checks,
        }

    @router.get("/detailed", response_model=DetailedHealth)
    async def detailed_health(container=Depends(get_service_container)) -> DetailedHealth:
        """Detailed health check with system metrics."""
        # Collect system information
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "used": psutil.disk_usage("/").used,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
        }

        # Check services
        services = {
            "api": "healthy",
            "database": "unknown",
            "cache": "unknown",
            "llm_provider": "unknown",
        }

        # Check database health
        try:
            if hasattr(container, "database_manager") and container.database_manager:
                services["database"] = "healthy"
        except Exception as e:
            services["database"] = f"unhealthy: {str(e)}"

        # Check cache health
        try:
            if hasattr(container, "cache_manager"):
                services["cache"] = "healthy"
        except Exception as e:
            services["cache"] = f"unhealthy: {str(e)}"

        # Check LLM provider health
        try:
            if hasattr(container, "graph_operations") and container.graph_operations:
                services["llm_provider"] = "healthy"
        except Exception as e:
            services["llm_provider"] = f"unhealthy: {str(e)}"

        # Collect performance metrics
        performance = {
            "uptime_seconds": time.time() - START_TIME,
            "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "thread_count": psutil.Process().num_threads(),
            "open_files": len(psutil.Process().open_files()),
            "connections": len(psutil.Process().connections()),
        }

        return DetailedHealth(
            status="healthy" if services["api"] == "healthy" else "degraded",
            timestamp=datetime.now(UTC).isoformat(),
            uptime=time.time() - START_TIME,
            version=settings.app_version,
            environment="production" if not settings.debug else "development",
            system=system_info,
            services=services,
            performance=performance,
        )

    @router.get("/metrics", response_model=dict)
    async def metrics_endpoint() -> dict:
        """Prometheus-compatible metrics endpoint."""
        metrics = []

        # System metrics
        metrics.append("# HELP graphrag_up Application up status")
        metrics.append("# TYPE graphrag_up gauge")
        metrics.append("graphrag_up 1")

        metrics.append("# HELP graphrag_uptime_seconds Application uptime in seconds")
        metrics.append("# TYPE graphrag_uptime_seconds gauge")
        metrics.append(f"graphrag_uptime_seconds {time.time() - START_TIME}")

        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append("# HELP graphrag_memory_usage_bytes Memory usage in bytes")
        metrics.append("# TYPE graphrag_memory_usage_bytes gauge")
        metrics.append(f"graphrag_memory_usage_bytes {memory.used}")

        metrics.append("# HELP graphrag_memory_percent Memory usage percentage")
        metrics.append("# TYPE graphrag_memory_percent gauge")
        metrics.append(f"graphrag_memory_percent {memory.percent}")

        # CPU metrics
        metrics.append("# HELP graphrag_cpu_percent CPU usage percentage")
        metrics.append("# TYPE graphrag_cpu_percent gauge")
        metrics.append(f"graphrag_cpu_percent {psutil.cpu_percent(interval=0.1)}")

        # Process metrics
        process = psutil.Process()
        metrics.append("# HELP graphrag_process_threads Number of threads")
        metrics.append("# TYPE graphrag_process_threads gauge")
        metrics.append(f"graphrag_process_threads {process.num_threads()}")

        metrics.append("# HELP graphrag_process_open_files Number of open files")
        metrics.append("# TYPE graphrag_process_open_files gauge")
        metrics.append(f"graphrag_process_open_files {len(process.open_files())}")

        return {
            "metrics": "\n".join(metrics),
            "content_type": "text/plain; version=0.0.4",
        }

    @router.get("/system", response_model=SystemInfo)
    async def system_info() -> SystemInfo:
        """Get system information."""
        return SystemInfo(
            platform=platform.platform(),
            python_version=platform.python_version(),
            cpu_count=psutil.cpu_count() or 0,
            memory_total=psutil.virtual_memory().total,
            memory_available=psutil.virtual_memory().available,
            memory_percent=psutil.virtual_memory().percent,
            disk_usage={
                "total": psutil.disk_usage("/").total,
                "used": psutil.disk_usage("/").used,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
        )

    return router
