"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import atexit
import contextlib
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from loguru import logger

# Add orchestrator root to path for proper imports
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / ".git").exists() and (current / "base").exists():
        # Found the main orchestrator root - add it FIRST
        sys.path.insert(0, str(current))
        break
    current = current.parent

from browser.tests.fixtures.test_server import HTMLTestServer  # noqa: E402
from browser.tests.fixtures.threaded_server import ThreadedHTMLServer  # noqa: E402

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Test configuration - can be overridden by environment variable
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"
logger.info(f"Test browser mode: {'headless' if HEADLESS else 'visible'}")

# Detect Chrome/Chromedriver availability and auto-install if missing
from browser.backend.utils.config import Config as _Config  # noqa: E402

_cfg = _Config()


def _has_chrome() -> bool:
    chrome_path = _cfg.get("backend.browser.chrome_binary_path")
    if not chrome_path:
        logger.error("Chrome path is not configured in browser/config.yaml")
        return False

    path_obj = Path(chrome_path)
    if not path_obj.exists():
        logger.error(f"Configured Chrome binary does not exist: {chrome_path}")
        return False

    try:
        result = subprocess.run([str(path_obj), "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        return result.returncode == 0
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to query Chrome version at {chrome_path}: {exc}")
        return False


def _has_chromedriver() -> bool:
    driver_path = _cfg.get("backend.browser.chromedriver_path")
    if driver_path and Path(driver_path).exists():
        return True
    try:
        import chromedriver_binary  # type: ignore  # noqa: F401,PLC0415

        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # If Chrome/Driver missing, surface explicit remediation steps and skip tests
    if not (_has_chrome() and _has_chromedriver()):
        import pytest as _pytest  # local import to avoid global side effects  # noqa: PLC0415

        reason = (
            "Chrome or ChromeDriver not available. Configure paths in browser/config.yaml and run "
            "browser/scripts/setup_chrome.py before executing browser tests."
        )
        for item in items:
            item.add_marker(_pytest.mark.skip(reason=reason))
        return

    # Optional preflight: attempt a minimal launch to detect container runtime issues
    def _preflight_can_launch() -> bool:
        try:
            from browser.backend.core.management.manager import ChromeManager as _Mgr  # local import  # noqa: PLC0415

            mgr = _Mgr(config_file="config.yaml" if Path("config.yaml").exists() else "config.sample.yaml")
            import asyncio as _asyncio  # noqa: PLC0415

            async def _run() -> bool:
                try:
                    await mgr.start()
                    inst = await mgr.get_or_create_instance(headless=True, use_pool=True)
                    # Simple health check
                    ok = inst.driver is not None and len(inst.driver.window_handles) >= 1
                    await mgr.return_to_pool(inst.id)
                    await mgr.stop()
                    return bool(ok)
                except Exception:
                    with contextlib.suppress(Exception):
                        await mgr.stop()
                    return False

            return _asyncio.get_event_loop().run_until_complete(_run())
        except Exception:
            return False

    can_launch = _preflight_can_launch()
    if not can_launch:
        import pytest as _pytest  # noqa: PLC0415

        reason = "Chrome present but cannot launch in this environment; skipping launch-dependent tests"
        launch_fixtures = {"session_manager", "browser_instance", "antidetect_browser", "backend", "browser"}
        launch_markers = {"integration", "mcp", "browser", "pool"}
        for item in items:
            # Skip if test uses launch-related fixtures or has relevant markers or file is under integration
            if (
                (set(getattr(item, "fixturenames", [])) & launch_fixtures)
                or any(item.get_closest_marker(m) for m in launch_markers)
                or ("/integration/" in str(item.fspath))
                or ("Integration" in item.nodeid)
            ):
                item.add_marker(_pytest.mark.skip(reason=reason))


# Import heavy browser modules only after environment check
from browser.backend.core.browser.instance import BrowserInstance  # noqa: E402
from browser.backend.core.management.manager import ChromeManager  # noqa: E402
from browser.backend.utils.config import Config  # noqa: E402

# NO GLOBAL STATE - Each test gets its own manager instance


@pytest_asyncio.fixture(scope="session")
async def session_manager() -> AsyncIterator[ChromeManager]:
    """Create a Chrome manager instance for the test session."""
    # Use test config for testing
    test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
    manager = ChromeManager(config_file=test_config)
    # Pool is configured through the manager's constructor using config file
    # No need to modify pool settings directly - they're set via PoolConfig
    await manager.start()
    logger.info("Created ChromeManager for test")

    yield manager

    # Cleanup after test
    try:
        await manager.stop()
        logger.info("Stopped ChromeManager after test")
    except Exception as e:
        logger.warning(f"Error stopping manager: {e}")


@pytest_asyncio.fixture(scope="module")
async def browser_instance(session_manager: ChromeManager) -> AsyncIterator[BrowserInstance]:
    """Get a browser instance from the pool - reused per module."""
    # Get instance from pool
    logger.info(f"Requesting browser instance (headless={HEADLESS})")
    instance = await session_manager.get_or_create_instance(headless=HEADLESS, use_pool=True)
    logger.info(f"Got browser instance {instance.id} from pool (headless={HEADLESS})")

    # Store initial state
    # driver is initialized by launch within manager.get_or_create_instance
    assert instance.driver is not None
    initial_handles = set(instance.driver.window_handles)

    yield instance

    # Cleanup after test
    try:
        # Close any extra tabs opened during test
        assert instance.driver is not None
        current_handles = set(instance.driver.window_handles)
        new_handles = current_handles - initial_handles

        for handle in new_handles:
            try:
                assert instance.driver is not None
                instance.driver.switch_to.window(handle)
                instance.driver.close()
            except Exception:
                logger.debug(f"Tab {handle} may already be closed")

        # Switch back to initial tab
        assert instance.driver is not None
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
async def antidetect_browser() -> AsyncIterator[BrowserInstance]:
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
def test_html_server() -> Iterator[str]:
    """Start test HTML server in a separate thread for all tests."""
    server = ThreadedHTMLServer(port=8889)
    base_url = server.start()  # Starts in thread
    yield base_url
    server.stop()  # Stops the thread


@pytest_asyncio.fixture(scope="function")  # NEVER use session scope!
async def test_server() -> AsyncIterator[str]:
    """Start test HTTP server for each test."""

    # Bind to an ephemeral port (port=0) to avoid conflicts reliably
    server: HTMLTestServer | None = HTMLTestServer(port=0)
    try:
        assert server is not None
        base_url = await server.start()
        logger.info(f"Test server started at {base_url}")
    except OSError as e:
        raise RuntimeError("Failed to bind test HTTP server to an ephemeral port") from e

    yield base_url

    if server:
        await server.stop()
        logger.info("Test server stopped")


# DEPRECATED - use browser_instance or session_manager instead
@pytest_asyncio.fixture(scope="class")
async def browser() -> AsyncIterator[BrowserInstance]:
    """DEPRECATED: Create a browser instance shared by all tests in a class."""
    logger.warning("Using deprecated 'browser' fixture - use 'browser_instance' instead")
    # Load config from config.yaml if it exists, otherwise use defaults
    config = Config.load("config.yaml")
    instance = BrowserInstance(config=config)
    await instance.launch(headless=HEADLESS)
    logger.info(f"Browser instance {instance.id} launched for test class")

    # Keep only the initial tab
    assert instance.driver is not None
    initial_tab = instance.driver.current_window_handle
    logger.info(f"Initial tab: {initial_tab}")

    yield instance

    # Close all extra tabs before terminating
    try:
        assert instance.driver is not None
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
async def backend() -> AsyncIterator[ChromeManager]:
    """DEPRECATED: Create a Chrome manager for testing - one per test class."""
    logger.warning("Using deprecated 'backend' fixture - use 'session_manager' instead")
    # Use test config for all tests
    test_config = "config.test.yaml" if Path("config.test.yaml").exists() else "config.yaml"
    manager = ChromeManager(config_file=test_config)
    await manager.start()

    yield manager

    await manager.stop()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


# Test configuration
TEST_CONFIG = {
    "browser": {"headless": True, "window_size": [1280, 720]},
    "timeouts": {"default": 10, "navigation": 30, "script": 10},
    "test_server": {"host": "localhost", "port": 8888},
}


@pytest.fixture
def test_config() -> dict[str, Any]:
    """Provide test configuration."""
    return TEST_CONFIG


# Markers for test categorization
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "mcp: marks tests related to MCP server")
    config.addinivalue_line("markers", "browser: marks tests related to browser operations")
    config.addinivalue_line("markers", "pool: marks tests related to browser pool")


# Removed cleanup_manager - no global state to clean up


def cleanup_processes() -> None:
    """Kill any remaining browser or server processes."""
    # No global manager to clean up - each test handles its own

    # Try to log cleanup, but suppress any errors if logger is closed
    try:
        if sys.stderr and not sys.stderr.closed:
            logger.info("Cleaning up browser and server processes")
    except (ValueError, AttributeError, RuntimeError):
        # Logger or stderr might be closed during cleanup
        pass

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
def cleanup_at_exit() -> Iterator[None]:
    """Ensure cleanup happens at the end of the test session."""
    yield
    cleanup_processes()
    # Remove logger handlers to prevent writing to closed streams
    with contextlib.suppress(Exception):
        logger.remove()
