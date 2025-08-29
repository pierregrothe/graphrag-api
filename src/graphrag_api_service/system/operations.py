# src/graphrag_api_service/system/operations.py
# System management operations implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""System management operations for enhanced monitoring and control."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from ..config import Settings
from ..graph.operations import GraphOperations
from ..graphrag_integration import GraphRAGIntegration
from ..indexing.manager import IndexingManager
from ..logging_config import get_logger
from ..providers.factory import LLMProviderFactory
from ..workspace.manager import WorkspaceManager

logger = get_logger(__name__)


class SystemOperationsError(Exception):
    """Base exception for system operations."""

    pass


class SystemOperations:
    """System operations for enhanced monitoring and control."""

    def __init__(
        self,
        settings: Settings,
        provider_factory: LLMProviderFactory | None = None,
        graphrag_integration: GraphRAGIntegration | None = None,
        workspace_manager: WorkspaceManager | None = None,
        indexing_manager: IndexingManager | None = None,
        graph_operations: GraphOperations | None = None,
    ):
        """Initialize system operations.

        Args:
            settings: Application settings
            provider_factory: Optional LLM provider factory
            graphrag_integration: Optional GraphRAG integration
            workspace_manager: Optional workspace manager
            indexing_manager: Optional indexing manager
            graph_operations: Optional graph operations
        """
        self.settings = settings
        self.provider_factory = provider_factory or LLMProviderFactory()
        self.graphrag_integration = graphrag_integration
        self.workspace_manager = workspace_manager or WorkspaceManager(settings)
        self.indexing_manager = indexing_manager or IndexingManager(settings)
        self.graph_operations = graph_operations or GraphOperations(settings)
        self.start_time = datetime.now(UTC)
        self.operation_history: list[dict[str, Any]] = []
        self.metrics = {
            "graph_queries": 0,
            "graph_exports": 0,
            "indexing_jobs": 0,
            "workspace_operations": 0,
            "provider_switches": 0,
        }

    async def switch_provider(
        self, provider_name: str, validate_connection: bool = True
    ) -> dict[str, Any]:
        """Switch the active LLM provider.

        Args:
            provider_name: Name of the provider to switch to
            validate_connection: Whether to validate provider connection

        Returns:
            Dictionary containing switch operation results

        Raises:
            SystemOperationsError: If provider switch fails
        """
        try:
            previous_provider = self.settings.llm_provider.value

            # Update settings
            from ..config import LLMProvider

            self.settings.llm_provider = LLMProvider(provider_name)

            # Create new provider instance
            new_provider = self.provider_factory.create_provider(self.settings)

            validation_result = None
            if validate_connection:
                # Validate new provider
                health = await new_provider.health_check()
                if not health.healthy:
                    # Rollback on validation failure
                    self.settings.llm_provider = LLMProvider(previous_provider)
                    raise SystemOperationsError(f"Provider validation failed: Provider is not healthy")
                validation_result = health.model_dump()

            # Update GraphRAG integration if available
            if self.graphrag_integration:
                self.graphrag_integration.provider = new_provider

            # Record operation
            self.metrics["provider_switches"] += 1
            self._record_operation(
                "provider_switch",
                {"from": previous_provider, "to": provider_name, "validated": validate_connection},
            )

            return {
                "success": True,
                "previous_provider": previous_provider,
                "current_provider": provider_name,
                "message": f"Successfully switched from {previous_provider} to {provider_name}",
                "validation_result": validation_result,
            }

        except Exception as e:
            logger.error(f"Provider switch failed: {e}")
            raise SystemOperationsError(f"Provider switch failed: {e}") from e

    async def get_advanced_health(self) -> dict[str, Any]:
        """Get comprehensive system health status.

        Returns:
            Dictionary containing detailed health information
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "components": {},
                "provider": {},
                "graphrag": {},
                "workspaces": {},
                "graph_data": {},
                "system_resources": {},
            }

            # Check provider health
            try:
                provider = self.provider_factory.create_provider(self.settings)
                provider_health = await provider.health_check()
                health_status["provider"] = {
                    "name": self.settings.llm_provider.value,
                    "healthy": provider_health.healthy,
                    "models": getattr(provider_health, 'available_models', []),
                    "error": getattr(provider_health, 'error', None),
                    "metadata": getattr(provider_health, 'metadata', {}),
                }
                if not provider_health.healthy:
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["provider"] = {"healthy": False, "error": str(e)}
                health_status["status"] = "degraded"

            # Check GraphRAG integration
            if self.graphrag_integration:
                health_status["graphrag"] = {
                    "available": True,
                    "provider_connected": self.graphrag_integration.provider is not None,
                }
            else:
                health_status["graphrag"] = {"available": False}
                health_status["status"] = "degraded"

            # Check workspace health
            workspaces = self.workspace_manager.list_workspaces()
            health_status["workspaces"] = {
                "total": len(workspaces),
                "active": sum(1 for w in workspaces if getattr(w, 'status', None) == "active"),
            }

            # Check graph data availability
            if self.settings.graphrag_data_path:
                data_path = Path(self.settings.graphrag_data_path)
                entities_exist = (
                    data_path / "output" / "artifacts" / "create_final_entities.parquet"
                ).exists()
                relationships_exist = (
                    data_path / "output" / "artifacts" / "create_final_relationships.parquet"
                ).exists()

                health_status["graph_data"] = {
                    "path_configured": True,
                    "entities_available": entities_exist,
                    "relationships_available": relationships_exist,
                }
            else:
                health_status["graph_data"] = {"path_configured": False}

            # System resources
            health_status["system_resources"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }

            # Component statuses
            health_status["components"] = {
                "api": "healthy",
                "workspace_manager": "healthy" if workspaces else "idle",
                "indexing_manager": "healthy",
                "graph_operations": (
                    "healthy" if health_status["graph_data"]["path_configured"] else "unconfigured"
                ),
            }

            # Determine overall status
            if health_status["status"] == "degraded":
                pass  # Already set
            elif health_status["system_resources"]["memory_percent"] > 90:
                health_status["status"] = "degraded"
            elif health_status["system_resources"]["cpu_percent"] > 90:
                health_status["status"] = "degraded"

            return health_status

        except Exception as e:
            logger.error(f"Advanced health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            }

    async def get_enhanced_status(self) -> dict[str, Any]:
        """Get enhanced system status with metrics.

        Returns:
            Dictionary containing comprehensive status information
        """
        try:
            uptime = (datetime.now(UTC) - self.start_time).total_seconds()

            # Get provider info
            provider_info = {}
            try:
                provider = self.provider_factory.create_provider(self.settings)
                provider_info = provider.get_configuration_info()
            except Exception as e:
                provider_info = {"error": str(e)}

            # Get graph metrics if available
            graph_metrics = {}
            if self.settings.graphrag_data_path:
                try:
                    stats = await self.graph_operations.get_graph_statistics(
                        self.settings.graphrag_data_path
                    )
                    graph_metrics = {
                        "total_entities": stats.get("total_entities", 0),
                        "total_relationships": stats.get("total_relationships", 0),
                        "total_communities": stats.get("total_communities", 0),
                        "queries_processed": self.metrics["graph_queries"],
                        "exports_generated": self.metrics["graph_exports"],
                    }
                except Exception:
                    graph_metrics = {"available": False}

            # Get indexing metrics
            indexing_stats = self.indexing_manager.get_indexing_stats()
            indexing_metrics = {
                "total_jobs": indexing_stats.total_jobs,
                "active_jobs": indexing_stats.running_jobs,
                "queued_jobs": indexing_stats.queued_jobs,
                "completed_jobs": indexing_stats.completed_jobs,
                "failed_jobs": indexing_stats.failed_jobs,
            }

            # Get workspace metrics
            workspaces = self.workspace_manager.list_workspaces()
            workspace_metrics = {
                "total_workspaces": len(workspaces),
                "operations_performed": self.metrics["workspace_operations"],
            }

            # Get recent operations (last 10)
            recent_operations = self.operation_history[-10:] if self.operation_history else []

            return {
                "version": "1.0.0",
                "environment": "development" if self.settings.debug else "production",
                "uptime_seconds": uptime,
                "provider_info": provider_info,
                "graph_metrics": graph_metrics,
                "indexing_metrics": indexing_metrics,
                "query_metrics": {
                    "total_queries": self.metrics.get("graph_queries", 0),
                },
                "workspace_metrics": workspace_metrics,
                "recent_operations": recent_operations,
            }

        except Exception as e:
            logger.error(f"Enhanced status generation failed: {e}")
            raise SystemOperationsError(f"Enhanced status generation failed: {e}") from e

    async def validate_configuration(
        self, config_type: str, config_data: dict[str, Any] | None = None, strict_mode: bool = False
    ) -> dict[str, Any]:
        """Validate system configuration.

        Args:
            config_type: Type of configuration to validate
            config_data: Optional configuration data to validate
            strict_mode: Whether to fail on warnings

        Returns:
            Dictionary containing validation results
        """
        errors = []
        warnings = []
        suggestions = []
        validated_config = None

        try:
            if config_type in ["provider", "all"]:
                # Validate provider configuration
                if not self.settings.llm_provider:
                    errors.append("No LLM provider configured")
                elif self.settings.llm_provider and self.settings.llm_provider.value not in [
                    "ollama",
                    "google_gemini",
                ]:
                    errors.append(f"Invalid provider: {self.settings.llm_provider.value}")

                if self.settings.llm_provider and self.settings.llm_provider.value == "ollama":
                    if not self.settings.ollama_base_url:
                        errors.append("Ollama base URL not configured")
                    if not self.settings.ollama_llm_model:
                        warnings.append("Ollama LLM model not specified, using default")
                elif (
                    self.settings.llm_provider
                    and self.settings.llm_provider.value == "google_gemini"
                ):
                    if not self.settings.google_api_key:
                        errors.append("Google API key not configured")
                    if not self.settings.gemini_model:
                        warnings.append("Gemini model not specified, using default")

            if config_type in ["graphrag", "all"]:
                # Validate GraphRAG configuration
                if not self.settings.graphrag_data_path:
                    warnings.append("GraphRAG data path not configured")
                    suggestions.append("Set GRAPHRAG_DATA_PATH to enable graph operations")
                elif not Path(self.settings.graphrag_data_path).exists():
                    warnings.append(
                        f"GraphRAG data path does not exist: {self.settings.graphrag_data_path}"
                    )

                if not self.settings.graphrag_config_path:
                    warnings.append("GraphRAG config path not configured")
                elif (
                    self.settings.graphrag_config_path
                    and not Path(self.settings.graphrag_config_path).exists()
                ):
                    warnings.append(
                        f"GraphRAG config path does not exist: {self.settings.graphrag_config_path}"
                    )

            if config_type in ["workspace", "all"]:
                # Validate workspace configuration
                workspaces = self.workspace_manager.list_workspaces()
                if not workspaces:
                    suggestions.append("No workspaces configured - create one to start indexing")

            # Check for additional config data to validate
            if config_data:
                validated_config = config_data.copy()
                # Add specific validation for provided config data
                if "provider" in config_data:
                    if config_data["provider"] not in ["ollama", "google_gemini"]:
                        errors.append(f"Invalid provider in config data: {config_data['provider']}")

            # Determine if configuration is valid
            valid = len(errors) == 0
            if strict_mode and len(warnings) > 0:
                valid = False

            return {
                "valid": valid,
                "config_type": config_type,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "validated_config": validated_config,
            }

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {
                "valid": False,
                "config_type": config_type,
                "errors": [str(e)],
                "warnings": [],
                "suggestions": [],
                "validated_config": None,
            }

    def _record_operation(self, operation_type: str, details: dict[str, Any] | None = None):
        """Record an operation in history.

        Args:
            operation_type: Type of operation
            details: Optional operation details
        """
        operation = {
            "type": operation_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details or {},
        }
        self.operation_history.append(operation)

        # Keep only last 100 operations
        if len(self.operation_history) > 100:
            self.operation_history = self.operation_history[-100:]

    def update_metrics(self, metric_type: str, increment: int = 1):
        """Update system metrics.

        Args:
            metric_type: Type of metric to update
            increment: Amount to increment by
        """
        if metric_type in self.metrics:
            self.metrics[metric_type] += increment
