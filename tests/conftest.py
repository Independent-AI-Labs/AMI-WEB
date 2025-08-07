"""Pytest configuration and shared fixtures."""

import asyncio
import sys
from pathlib import Path

import pytest
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
async def cleanup_browser():
    """Fixture to ensure browser cleanup after tests."""
    instances = []

    def register(instance):
        instances.append(instance)

    yield register

    # Cleanup all registered instances
    for instance in instances:
        try:
            await instance.terminate(force=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup browser instance: {e}")


# Test configuration
TEST_CONFIG = {
    "browser": {"headless": True, "window_size": [1280, 720]},
    "timeouts": {"default": 10, "navigation": 30, "script": 10},
    "test_server": {"host": "localhost", "port": 8888},
}


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "mcp: marks tests related to MCP server")
    config.addinivalue_line("markers", "browser: marks tests related to browser operations")
    config.addinivalue_line("markers", "pool: marks tests related to browser pool")
