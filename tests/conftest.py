# tests/conftest.py
# Pytest configuration and shared fixtures
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Pytest configuration and shared fixtures for all tests."""

import os
import sys
from pathlib import Path

# Import all fixtures from the fixtures module
from tests.fixtures.clients import async_test_client, sync_test_client, test_client
from tests.fixtures.data import (
    sample_graph_data,
    sample_query_request,
    sample_workspace_config,
    test_data_path,
)
from tests.fixtures.mocks import (
    mock_indexing_manager,
    mock_llm_provider,
    mock_workspace_manager,
)

# Add src to path for imports (after imports to avoid E402)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set testing environment variables
os.environ["TESTING"] = "true"
os.environ["RATE_LIMITING_ENABLED"] = "false"

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
