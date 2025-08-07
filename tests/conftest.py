"""Pytest configuration and shared fixtures."""

import atexit
import contextlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chrome_manager.core.instance import BrowserInstance  # noqa: E402
from chrome_manager.core.manager import ChromeManager  # noqa: E402
from tests.fixtures.test_server import HTMLTestServer  # noqa: E402
from tests.fixtures.threaded_server import ThreadedHTMLServer  # noqa: E402

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Test configuration - can be overridden by environment variable
HEADLESS = os.environ.get("TEST_HEADLESS", "false").lower() == "true"
logger.info(f"Test browser mode: {'headless' if HEADLESS else 'visible'}")

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def test_html_server():
    """Start test HTML server in a separate thread for all tests."""
    server = ThreadedHTMLServer(port=8889)
    base_url = server.start()  # Starts in thread
    yield base_url
    server.stop()  # Stops the thread


@pytest_asyncio.fixture(scope="session")
async def test_server():
    """Start test HTTP server for the entire test session."""
    server = HTMLTestServer(port=8888)
    try:
        base_url = await server.start()
        logger.info(f"Test server started at {base_url}")
    except OSError as e:
        if "10048" in str(e) or "Address already in use" in str(e):
            # Server already running, just use it
            base_url = "http://localhost:8888"
            server = None
            logger.info("Using existing server at http://localhost:8888")
        else:
            raise

    yield base_url

    if server:
        await server.stop()
        logger.info("Test server stopped")


@pytest_asyncio.fixture(scope="class")
async def browser():
    """Create a browser instance shared by all tests in a class."""
    instance = BrowserInstance()
    await instance.launch(headless=HEADLESS)
    logger.info(f"Browser instance {instance.id} launched for test class")

    # Keep only the initial tab
    initial_tab = instance.driver.current_window_handle
    logger.info(f"Initial tab: {initial_tab}")

    yield instance

    # Close all extra tabs before terminating
    try:
        all_tabs = instance.driver.window_handles
        for tab in all_tabs:
            if tab != initial_tab:
                instance.driver.switch_to.window(tab)
                instance.driver.close()
        instance.driver.switch_to.window(initial_tab)
    except Exception as e:
        logger.warning(f"Error cleaning up tabs: {e}")

    await instance.terminate()
    logger.info(f"Browser instance {instance.id} terminated")


@pytest_asyncio.fixture(scope="class")
async def chrome_manager():
    """Create a Chrome manager for testing - one per test class."""
    manager = ChromeManager()
    await manager.start()

    yield manager

    await manager.stop()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


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


def cleanup_processes():
    """Kill any remaining browser or server processes."""
    with contextlib.suppress(Exception):
        # Only log if logger is still available
        logger.info("Cleaning up browser and server processes")

    with contextlib.suppress(Exception):
        if sys.platform == "win32":
            # Kill Chrome and ChromeDriver processes on Windows
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, check=False)
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], capture_output=True, check=False)
        else:
            # Kill Chrome and ChromeDriver processes on Unix
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, check=False)
            subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True, check=False)


# Register cleanup at exit
atexit.register(cleanup_processes)


@pytest.fixture(scope="session", autouse=True)
def cleanup_at_exit():
    """Ensure cleanup happens at the end of the test session."""
    yield
    cleanup_processes()
