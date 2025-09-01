# src/graphrag_api_service/routes/__init__.py
# Route modules for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Route modules for organizing API endpoints."""

from .graph import router as graph_router
from .graphrag import router as graphrag_router
from .indexing import router as indexing_router
from .system import router as system_router
from .workspace import router as workspace_router

__all__ = [
    "graphrag_router",
    "workspace_router",
    "indexing_router",
    "graph_router",
    "system_router",
]
