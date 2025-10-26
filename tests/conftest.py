"""
Pytest configuration and fixtures.
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import os
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for testing."""
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_notion_client():
    """Mock Notion client."""
    mock_client = AsyncMock()

    # Mock database query
    mock_client.databases.query.return_value = {
        "results": [
            {
                "id": "test-page-id",
                "properties": {"Name": {"title": [{"text": {"content": "Test Farm"}}]}},
            }
        ]
    }

    # Mock page create
    mock_client.pages.create.return_value = {
        "id": "new-page-id",
        "url": "https://notion.so/test-page",
    }

    return mock_client


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload for testing."""
    return {
        "id": "01234567-89ab-cdef-0123-456789abcdef",
        "timestamp": "2024-01-01T12:00:00.000Z",
        "workspace_id": "98765432-10fe-dcba-9876-543210fedcba",
        "workspace_name": "Test Workspace",
        "subscription_id": "11111111-2222-3333-4444-555555555555",
        "integration_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "type": "page.created",
        "authors": [{"id": "user-123", "type": "person"}],
        "attempt_number": 1,
        "entity": {"id": "page-456", "type": "page"},
        "data": {"additional": "data"},
    }


@pytest.fixture
def sample_plot_data():
    """Sample plot data for testing."""
    return {
        "farm_name": "Test Farm",
        "plots": [
            {"plot_number": "001", "area": 10.5, "crop": "Corn", "status": "Active"},
            {"plot_number": "002", "area": 8.2, "crop": "Wheat", "status": "Planned"},
        ],
        "total_area": 18.7,
        "active_plots": 1,
    }


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    import os

    # Store original values
    original_env = {}
    test_env = {
        "NOTION_API_TOKEN": "test-token-123",
        "VERCEL_BLOB_STORE_ID": "test-store-id",
        "VERCEL_BLOB_TOKEN": "test-blob-token",
        "NOTION_DATABASE_ID": "test-database-id",
    }

    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
