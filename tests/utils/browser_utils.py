"""Browser utilities for tests."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger
from selenium.webdriver.remote.webdriver import WebDriver

from browser.backend.core.browser.instance import BrowserInstance


class TabManager:
    """Manages browser tabs for tests."""

    def __init__(self, browser: BrowserInstance) -> None:
        self.browser = browser
        self.original_tab: str | None = None

    async def __aenter__(self) -> BrowserInstance:
        """Create a new tab and switch to it."""
        driver = _get_driver(self.browser)
        # Save current tab
        self.original_tab = driver.current_window_handle
        original_tabs = driver.window_handles

        # Create new tab
        driver.execute_script("window.open('about:blank', '_blank');")

        # Get the new tab handle
        all_tabs = driver.window_handles
        new_tab = [t for t in all_tabs if t not in original_tabs][0]

        # Switch to new tab
        driver.switch_to.window(new_tab)
        logger.debug(f"Created and switched to new tab: {new_tab}")

        return self.browser

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Close the tab and switch back to original."""
        driver = _get_driver(self.browser)
        try:
            # Close current tab
            driver.close()
            # Switch back to original tab
            if self.original_tab is not None:
                driver.switch_to.window(self.original_tab)
            logger.debug("Closed tab and switched back to original")
        except Exception as e:
            logger.warning(f"Error closing tab: {e}")


@asynccontextmanager
async def new_tab(browser: BrowserInstance) -> AsyncGenerator[BrowserInstance, None]:
    """Context manager for creating a new tab.

    Usage:
        async with new_tab(browser) as tab_browser:
            nav = NavigationController(tab_browser)
            await nav.navigate("https://example.com")
    """
    # Save current tab
    driver = _get_driver(browser)
    original_tab = driver.current_window_handle
    original_tabs = driver.window_handles

    # Create new tab
    driver.execute_script("window.open('about:blank', '_blank');")

    # Get the new tab handle
    all_tabs = driver.window_handles
    new_tab_handle = [t for t in all_tabs if t not in original_tabs][0]

    # Switch to new tab
    driver.switch_to.window(new_tab_handle)
    logger.debug(f"Created and switched to new tab: {new_tab_handle}")

    try:
        yield browser
    finally:
        # Close tab and switch back
        try:
            driver.close()
            driver.switch_to.window(original_tab)
            logger.debug("Closed tab and switched back to original")
        except Exception as e:
            logger.warning(f"Error closing tab: {e}")


def create_tab(browser: BrowserInstance) -> str:
    """Create a new tab and return its handle.

    Args:
        browser: The browser instance

    Returns:
        The handle of the new tab
    """
    driver = _get_driver(browser)
    original_tabs = driver.window_handles

    # Create new tab
    driver.execute_script("window.open('about:blank', '_blank');")

    # Get the new tab handle
    all_tabs = driver.window_handles
    new_tab = [t for t in all_tabs if t not in original_tabs][0]

    logger.debug(f"Created new tab: {new_tab}")
    return str(new_tab)


def switch_to_tab(browser: BrowserInstance, tab_handle: str) -> None:
    """Switch to a specific tab.

    Args:
        browser: The browser instance
        tab_handle: The handle of the tab to switch to
    """
    _get_driver(browser).switch_to.window(tab_handle)
    logger.debug(f"Switched to tab: {tab_handle}")


def close_tab(browser: BrowserInstance, switch_to: str | None = None) -> None:
    """Close the current tab and optionally switch to another.

    Args:
        browser: The browser instance
        switch_to: Optional tab handle to switch to after closing
    """
    try:
        # Close current tab
        driver = _get_driver(browser)
        driver.close()

        # Switch to specified tab or first available
        if switch_to:
            driver.switch_to.window(switch_to)
        else:
            remaining_tabs = driver.window_handles
            if remaining_tabs:
                driver.switch_to.window(remaining_tabs[0])

        logger.debug("Closed tab")
    except Exception as e:
        logger.warning(f"Error closing tab: {e}")


def close_all_tabs_except(browser: BrowserInstance, keep_tab: str) -> None:
    """Close all tabs except the specified one.

    Args:
        browser: The browser instance
        keep_tab: The handle of the tab to keep open
    """
    driver = _get_driver(browser)
    all_tabs = driver.window_handles

    for tab in all_tabs:
        if tab != keep_tab:
            driver.switch_to.window(tab)
            driver.close()

    # Switch to the kept tab
    driver.switch_to.window(keep_tab)
    logger.debug(f"Closed all tabs except: {keep_tab}")


def _get_driver(browser: BrowserInstance) -> WebDriver:
    """Get WebDriver, ensuring it's initialized for mypy and runtime."""
    driver = browser.driver
    if driver is None:
        raise RuntimeError("Browser driver is not initialized")
    return driver
