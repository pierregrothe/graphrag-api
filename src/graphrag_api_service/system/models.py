# src/graphrag_api_service/system/models.py
# System management data models
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Data models for system management and enhanced monitoring."""

from typing import Any

from pydantic import BaseModel, Field


class ProviderSwitchRequest(BaseModel):
    """Request model for switching LLM provider."""

    provider: str = Field(..., description="Target provider: 'ollama' or 'google_gemini'")
    validate_connection: bool = Field(
        default=True, description="Validate provider connection before switching"
    )


class ProviderSwitchResponse(BaseModel):
    """Response model for provider switch operation."""

    success: bool = Field(..., description="Whether the switch was successful")
    previous_provider: str = Field(..., description="Previous provider name")
    current_provider: str = Field(..., description="Current provider name")
    message: str = Field(..., description="Status message")
    validation_result: dict[str, Any] | None = Field(
        None, description="Provider validation results if requested"
    )


class AdvancedHealthResponse(BaseModel):
    """Response model for advanced health check."""

    status: str = Field(..., description="Overall system status: healthy, degraded, unhealthy")
    timestamp: str = Field(..., description="Health check timestamp")
    components: dict[str, Any] = Field(..., description="Component health statuses")
    provider: dict[str, Any] = Field(..., description="LLM provider health")
    graphrag: dict[str, Any] = Field(..., description="GraphRAG integration health")
    workspaces: dict[str, Any] = Field(..., description="Workspace management health")
    graph_data: dict[str, Any] = Field(..., description="Graph data availability")
    system_resources: dict[str, Any] = Field(..., description="System resource metrics")


class EnhancedStatusResponse(BaseModel):
    """Response model for enhanced status reporting."""

    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment (development/production)")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    provider_info: dict[str, Any] = Field(..., description="Current provider information")
    graph_metrics: dict[str, Any] = Field(..., description="Graph operation metrics")
    indexing_metrics: dict[str, Any] = Field(..., description="Indexing operation metrics")
    query_metrics: dict[str, Any] = Field(..., description="Query operation metrics")
    workspace_metrics: dict[str, Any] = Field(..., description="Workspace metrics")
    recent_operations: list[dict[str, Any]] = Field(..., description="Recent operation history")


class ConfigValidationRequest(BaseModel):
    """Request model for configuration validation."""

    config_type: str = Field(
        ..., description="Configuration type: 'provider', 'graphrag', 'workspace', 'all'"
    )
    config_data: dict[str, Any] | None = Field(
        None, description="Optional configuration data to validate"
    )
    strict_mode: bool = Field(
        default=False, description="Enable strict validation (fail on warnings)"
    )


class ConfigValidationResponse(BaseModel):
    """Response model for configuration validation."""

    valid: bool = Field(..., description="Whether configuration is valid")
    config_type: str = Field(..., description="Type of configuration validated")
    errors: list[str] = Field(..., description="List of validation errors")
    warnings: list[str] = Field(..., description="List of validation warnings")
    suggestions: list[str] = Field(..., description="Configuration improvement suggestions")
    validated_config: dict[str, Any] | None = Field(
        None, description="Validated and normalized configuration"
    )
