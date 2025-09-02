# tests/fixtures/clients.py
# Test client fixtures
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Test client fixtures for API testing."""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.graphrag_api_service.main import app


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a synchronous test client with proper lifespan handling."""
    with patch.dict(
        os.environ,
        {
            "TESTING": "true",
            "RATE_LIMITING_ENABLED": "false",
            "LOG_LEVEL": "WARNING",
        },
    ):
        with TestClient(app) as client:
            yield client


@pytest.fixture
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client."""
    from httpx import ASGITransport

    with patch.dict(
        os.environ,
        {
            "TESTING": "true",
            "RATE_LIMITING_ENABLED": "false",
            "LOG_LEVEL": "WARNING",
        },
    ):
        with TestClient(app):  # This handles the lifespan
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client


@pytest.fixture
def sync_test_client() -> Generator[httpx.Client, None, None]:
    """Create a sync HTTP client for external API testing."""
    with httpx.Client(base_url="http://localhost:8001") as client:
        yield client