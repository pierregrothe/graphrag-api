# tests/conftest.py
# Pytest configuration and shared fixtures
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Pytest configuration and shared fixtures for all tests."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all fixtures from the fixtures module
from tests.fixtures.clients import async_test_client, sync_test_client, test_client
from tests.fixtures.data import (
    sample_graph_data,
    sample_query_request,
    sample_workspace_config,
    test_data_path,
)
from tests.fixtures.mocks import mock_indexing_manager, mock_llm_provider, mock_workspace_manager

# Make fixtures available to all tests
__all__ = [
    "test_client",
    "async_test_client",
    "sync_test_client",
    "sample_workspace_config",
    "sample_query_request",
    "sample_graph_data",
    "test_data_path",
    "mock_workspace_manager",
    "mock_llm_provider",
    "mock_indexing_manager",
]