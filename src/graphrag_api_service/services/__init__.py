# src/graphrag_api_service/services/__init__.py
# Services module initialization
# Author: Pierre Grothé
# Creation Date: 2025-09-05

"""Services module for GraphRAG API Service."""

from .auth_service import AuthService
from .graph_query import GraphQueryService
from .interfaces import (
    AuthenticationServiceProtocol,
    BaseService,
    CacheServiceProtocol,
    GraphAnalyticsServiceProtocol,
    GraphExportServiceProtocol,
    GraphQueryServiceProtocol,
    WorkspacePermissionServiceProtocol,
    WorkspaceResourceServiceProtocol,
    WorkspaceServiceProtocol,
)

__all__ = [
    "AuthService",
    "GraphQueryService",
    "BaseService",
    "AuthenticationServiceProtocol",
    "CacheServiceProtocol",
    "GraphAnalyticsServiceProtocol",
    "GraphExportServiceProtocol",
    "GraphQueryServiceProtocol",
    "WorkspacePermissionServiceProtocol",
    "WorkspaceResourceServiceProtocol",
    "WorkspaceServiceProtocol",
]
