# tests/fixtures/mocks.py
# Mock objects for testing
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Mock objects and fixtures for testing."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_workspace_manager() -> AsyncMock:
    """Mock workspace manager for testing."""
    manager = AsyncMock()
    manager.create_workspace = AsyncMock(
        return_value={
            "id": "test-workspace-id",
            "name": "test-workspace",
            "status": "active",
            "created_at": "2025-09-02T00:00:00Z",
        }
    )
    manager.list_workspaces = AsyncMock(return_value=[])
    manager.get_workspace = AsyncMock(return_value=None)
    manager.delete_workspace = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Mock LLM provider for testing."""
    provider = MagicMock()
    provider.validate_connection = AsyncMock(return_value=True)
    provider.generate_text = AsyncMock(return_value="Generated text response")
    provider.generate_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    provider.get_model_info = MagicMock(
        return_value={
            "name": "test-model",
            "version": "1.0",
            "max_tokens": 4096,
        }
    )
    return provider


@pytest.fixture
def mock_indexing_manager() -> AsyncMock:
    """Mock indexing manager for testing."""
    manager = AsyncMock()
    manager.start_indexing = AsyncMock(
        return_value={
            "job_id": "test-job-id",
            "status": "started",
            "workspace_id": "test-workspace-id",
        }
    )
    manager.get_job_status = AsyncMock(
        return_value={
            "job_id": "test-job-id",
            "status": "completed",
            "progress": 100,
        }
    )
    return manager
