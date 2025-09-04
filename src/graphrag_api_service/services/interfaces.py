"""
Service interfaces and protocols for GraphRAG API Service.

This module defines abstract interfaces for all services to improve
testability, dependency injection, and maintainability.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol

from ..exceptions import GraphRAGServiceError


class GraphQueryServiceProtocol(Protocol):
    """Protocol for graph query operations."""

    async def get_entities(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get entities from the knowledge graph."""
        ...

    async def get_relationships(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get relationships from the knowledge graph."""
        ...

    async def search_entities(
        self, workspace_id: str, query: str, limit: int = 50
    ) -> dict[str, Any]:
        """Search entities by text query."""
        ...


class GraphAnalyticsServiceProtocol(Protocol):
    """Protocol for graph analytics operations."""

    async def get_community_analysis(
        self, workspace_id: str, community_level: int = 0
    ) -> dict[str, Any]:
        """Get community analysis results."""
        ...

    async def get_centrality_metrics(
        self, workspace_id: str, metric_type: str = "degree"
    ) -> dict[str, Any]:
        """Get centrality metrics for entities."""
        ...

    async def get_graph_statistics(self, workspace_id: str) -> dict[str, Any]:
        """Get overall graph statistics."""
        ...


class GraphExportServiceProtocol(Protocol):
    """Protocol for graph export operations."""

    async def export_to_csv(
        self, workspace_id: str, export_type: str, filters: dict[str, Any] | None = None
    ) -> str:
        """Export graph data to CSV format."""
        ...

    async def export_to_json(
        self, workspace_id: str, export_type: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Export graph data to JSON format."""
        ...

    async def export_to_graphml(self, workspace_id: str, include_attributes: bool = True) -> str:
        """Export graph to GraphML format."""
        ...


class WorkspaceServiceProtocol(Protocol):
    """Protocol for workspace management operations."""

    async def create_workspace(
        self,
        name: str,
        description: str | None = None,
        owner_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new workspace."""
        ...

    async def get_workspace(self, workspace_id: str, user_id: str) -> dict[str, Any]:
        """Get workspace details."""
        ...

    async def update_workspace(
        self, workspace_id: str, updates: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        """Update workspace configuration."""
        ...

    async def delete_workspace(self, workspace_id: str, user_id: str) -> bool:
        """Delete a workspace."""
        ...

    async def list_user_workspaces(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List workspaces for a user."""
        ...


class WorkspacePermissionServiceProtocol(Protocol):
    """Protocol for workspace permission management."""

    async def check_permission(self, user_id: str, workspace_id: str, permission: str) -> bool:
        """Check if user has permission for workspace."""
        ...

    async def grant_permission(
        self, user_id: str, workspace_id: str, permission: str, granted_by: str
    ) -> bool:
        """Grant permission to user for workspace."""
        ...

    async def revoke_permission(
        self, user_id: str, workspace_id: str, permission: str, revoked_by: str
    ) -> bool:
        """Revoke permission from user for workspace."""
        ...

    async def list_workspace_permissions(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all permissions for a workspace."""
        ...


class WorkspaceResourceServiceProtocol(Protocol):
    """Protocol for workspace resource management."""

    async def get_resource_usage(self, workspace_id: str) -> dict[str, Any]:
        """Get current resource usage for workspace."""
        ...

    async def check_quota(
        self, workspace_id: str, resource_type: str, requested_amount: float
    ) -> dict[str, Any]:
        """Check if resource request is within quota."""
        ...

    async def update_quota(
        self, workspace_id: str, resource_type: str, new_limit: float, updated_by: str
    ) -> bool:
        """Update resource quota for workspace."""
        ...


class AuthenticationServiceProtocol(Protocol):
    """Protocol for authentication operations."""

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate user with email and password."""
        ...

    async def authenticate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Authenticate user with API key."""
        ...

    async def create_access_token(self, user_data: dict[str, Any]) -> str:
        """Create JWT access token for user."""
        ...

    async def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token."""
        ...


class CacheServiceProtocol(Protocol):
    """Protocol for caching operations."""

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        ...


# Abstract base classes for concrete implementations


class BaseService(ABC):
    """Base class for all services with common functionality."""

    def __init__(self, logger_name: str | None = None):
        import logging

        self.logger = logging.getLogger(logger_name or self.__class__.__name__)

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform service health check."""
        pass

    def _handle_service_error(self, error: Exception, operation: str) -> GraphRAGServiceError:
        """Convert generic exceptions to service-specific errors."""
        self.logger.error(f"Error in {operation}: {error}")

        if isinstance(error, GraphRAGServiceError):
            return error

        # Convert to appropriate service error
        from ..exceptions import ProcessingError

        return ProcessingError(
            message=f"Service operation failed: {operation}",
            operation=operation,
            details={"original_error": str(error)},
        )
