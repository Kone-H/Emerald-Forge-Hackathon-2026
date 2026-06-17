"""
pytest fixtures shared across all backend tests.
Mocks Redis and the CV polling task so tests run without
any external services.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture(scope="session", autouse=True)
def mock_redis():
    """Replace the live Redis client with a mock for all tests."""
    mock = MagicMock()
    mock.get.return_value = None   # no cached data — areas default to count 0
    with patch("cache.r", mock):
        yield mock


@pytest.fixture(scope="session")
def client(mock_redis):
    """Return a TestClient with the background CV poller mocked out."""
    with patch("main.poll_and_store", new=AsyncMock()):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as c:
            yield c
