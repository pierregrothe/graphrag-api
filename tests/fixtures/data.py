# tests/fixtures/data.py
# Test data fixtures
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Test data fixtures for GraphRAG API Service tests."""

import tempfile
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def test_data_path() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir)
        # Create some sample files
        (path / "sample.txt").write_text("Sample text for testing")
        (path / "data.txt").write_text("More test data")
        yield path


@pytest.fixture
def sample_workspace_config() -> dict:
    """Sample workspace configuration for testing."""
    return {
        "name": f"test-workspace-{uuid.uuid4().hex[:8]}",
        "description": "Test workspace for automated testing",
        "chunk_size": 1200,
        "chunk_overlap": 100,
        "max_entities": 1000,
        "max_relationships": 2000,
        "community_levels": 4,
    }


@pytest.fixture
def sample_query_request() -> dict:
    """Sample GraphRAG query request."""
    return {
        "query": "What are the main topics discussed?",
        "query_type": "local",
        "community_level": 2,
        "response_type": "Multiple Paragraphs",
        "max_tokens": 2000,
    }


@pytest.fixture
def sample_graph_data() -> dict:
    """Sample graph data for testing."""
    return {
        "entities": [
            {"id": "1", "name": "Entity1", "type": "person", "description": "Test entity 1"},
            {"id": "2", "name": "Entity2", "type": "organization", "description": "Test entity 2"},
            {"id": "3", "name": "Entity3", "type": "location", "description": "Test entity 3"},
        ],
        "relationships": [
            {"source": "1", "target": "2", "type": "works_for", "weight": 0.8},
            {"source": "2", "target": "3", "type": "located_in", "weight": 0.9},
        ],
        "communities": [
            {"id": 0, "level": 0, "entities": ["1", "2"]},
            {"id": 1, "level": 1, "entities": ["1", "2", "3"]},
        ],
    }
