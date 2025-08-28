# src/graphrag_api_service/workspace/__init__.py
# GraphRAG workspace management module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""GraphRAG workspace management module for multi-project support."""

from .manager import WorkspaceManager
from .models import Workspace, WorkspaceConfig, WorkspaceStatus

__all__ = ["WorkspaceManager", "Workspace", "WorkspaceConfig", "WorkspaceStatus"]
