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

from backend.core.browser.instance import BrowserInstance  # noqa: E402
from backend.core.management.manager import ChromeManager  # noqa: E402
from backend.utils.config import Config  # noqa: E402
from tests.fixtures.test_server import HTMLTestServer  # noqa: E402
from tests.fixtures.threaded_server import ThreadedHTMLServer  # noqa: E402

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Test configuration - can be overridden by environment variable
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"  # Default to headless mode
logger.info(f"Test browser mode: {'headless' if HEADLESS else 'visible'}")

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

# Global manager instance for all tests
_GLOBAL_MANAGER = None


@pytest_asyncio.fixture(scope="session")
async def session_manager():
    """Create a single Chrome manager for the entire test session."""
    global _GLOBAL_MANAGER  # noqa: PLW0603
    if _GLOBAL_MANAGER is None:
        # Use test config for testing
        test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
        _GLOBAL_MANAGER = ChromeManager(config_file=test_config)
        # Configure pool for testing - smaller pool, faster cleanup
        _GLOBAL_MANAGER.pool.min_instances = 1
        _GLOBAL_MANAGER.pool.max_instances = 3  # Limit max instances for tests
        _GLOBAL_MANAGER.pool.warm_instances = 1
        _GLOBAL_MANAGER.pool.health_check_interval = 60  # Less frequent health checks during tests
        await _GLOBAL_MANAGER.start()
        logger.info("Created global ChromeManager for test session with optimized pool settings")

    yield _GLOBAL_MANAGER

    # Cleanup will happen in cleanup_at_exit


@pytest_asyncio.fixture
async def browser_instance(session_manager):
    """Get a browser instance from the pool for each test."""
    # Get instance from pool
    logger.info(f"Requesting browser instance (headless={HEADLESS})")
    instance = await session_manager.get_or_create_instance(headless=HEADLESS, use_pool=True)
    logger.info(f"Got browser instance {instance.id} from pool (headless={HEADLESS})")

    # Store initial state
    initial_handles = set(instance.driver.window_handles)

    yield instance

    # Cleanup after test
    try:
        # Close any extra tabs opened during test
        current_handles = set(instance.driver.window_handles)
        new_handles = current_handles - initial_handles

        for handle in new_handles:
            try:
                instance.driver.switch_to.window(handle)
                instance.driver.close()
            except Exception:
                logger.debug(f"Tab {handle} may already be closed")

        # Switch back to initial tab
        if instance.driver.window_handles:
            instance.driver.switch_to.window(instance.driver.window_handles[0])
            # Navigate to about:blank to clear state
            instance.driver.get("about:blank")
            # Clear cookies for clean state
            instance.driver.delete_all_cookies()
    except Exception as e:
        logger.warning(f"Error cleaning up instance {instance.id}: {e}")

    # Return instance to pool
    await session_manager.return_to_pool(instance.id)
    logger.info(f"Returned instance {instance.id} to pool")


@pytest_asyncio.fixture
async def antidetect_browser():
    """Get an anti-detect browser instance from the pool."""
    # Create a new instance with anti-detect enabled
    # Use test config for testing
    test_config_file = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
    config = Config.load(test_config_file)
    instance = BrowserInstance(config=config)
    await instance.launch(headless=HEADLESS, anti_detect=True)
    logger.info(f"Created anti-detect browser instance {instance.id}")

    yield instance

    # Terminate this instance (don't return to pool since it has special config)
    await instance.terminate()
    logger.info(f"Terminated anti-detect instance {instance.id}")


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


# DEPRECATED - use browser_instance or session_manager instead
@pytest_asyncio.fixture(scope="class")
async def browser():
    """DEPRECATED: Create a browser instance shared by all tests in a class."""
    logger.warning("Using deprecated 'browser' fixture - use 'browser_instance' instead")
    # Load config from config.yaml if it exists, otherwise use defaults
    config = Config.load("config.yaml")
    instance = BrowserInstance(config=config)
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


# DEPRECATED - use session_manager instead
@pytest_asyncio.fixture(scope="class")
async def backend():
    """DEPRECATED: Create a Chrome manager for testing - one per test class."""
    logger.warning("Using deprecated 'backend' fixture - use 'session_manager' instead")
    # Use test config for all tests
    test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
    manager = ChromeManager(config_file=test_config)
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


async def cleanup_manager():
    """Properly shutdown the global manager."""
    global _GLOBAL_MANAGER  # noqa: PLW0603
    if _GLOBAL_MANAGER:
        try:
            logger.info("Shutting down global ChromeManager")
            await _GLOBAL_MANAGER.shutdown()
            _GLOBAL_MANAGER = None
        except Exception as e:
            logger.error(f"Error shutting down manager: {e}")


def cleanup_processes():
    """Kill any remaining browser or server processes."""
    # First try to properly shutdown the manager
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cleanup_manager())
        else:
            loop.run_until_complete(cleanup_manager())
    except Exception:  # noqa: S110
        pass

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
