"""Browser utilities for tests."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger

from chrome_manager.core.instance import BrowserInstance


class TabManager:
    """Manages browser tabs for tests."""

    def __init__(self, browser: BrowserInstance):
        self.browser = browser
        self.original_tab = None

    async def __aenter__(self):
        """Create a new tab and switch to it."""
        # Save current tab
        self.original_tab = self.browser.driver.current_window_handle
        original_tabs = self.browser.driver.window_handles

        # Create new tab
        self.browser.driver.execute_script("window.open('about:blank', '_blank');")

        # Get the new tab handle
        all_tabs = self.browser.driver.window_handles
        new_tab = [t for t in all_tabs if t not in original_tabs][0]

        # Switch to new tab
        self.browser.driver.switch_to.window(new_tab)
        logger.debug(f"Created and switched to new tab: {new_tab}")

        return self.browser

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the tab and switch back to original."""
        try:
            # Close current tab
            self.browser.driver.close()
            # Switch back to original tab
            self.browser.driver.switch_to.window(self.original_tab)
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
    original_tab = browser.driver.current_window_handle
    original_tabs = browser.driver.window_handles

    # Create new tab
    browser.driver.execute_script("window.open('about:blank', '_blank');")

    # Get the new tab handle
    all_tabs = browser.driver.window_handles
    new_tab_handle = [t for t in all_tabs if t not in original_tabs][0]

    # Switch to new tab
    browser.driver.switch_to.window(new_tab_handle)
    logger.debug(f"Created and switched to new tab: {new_tab_handle}")

    try:
        yield browser
    finally:
        # Close tab and switch back
        try:
            browser.driver.close()
            browser.driver.switch_to.window(original_tab)
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
    original_tabs = browser.driver.window_handles

    # Create new tab
    browser.driver.execute_script("window.open('about:blank', '_blank');")

    # Get the new tab handle
    all_tabs = browser.driver.window_handles
    new_tab = [t for t in all_tabs if t not in original_tabs][0]

    logger.debug(f"Created new tab: {new_tab}")
    return new_tab


def switch_to_tab(browser: BrowserInstance, tab_handle: str):
    """Switch to a specific tab.
    
    Args:
        browser: The browser instance
        tab_handle: The handle of the tab to switch to
    """
    browser.driver.switch_to.window(tab_handle)
    logger.debug(f"Switched to tab: {tab_handle}")


def close_tab(browser: BrowserInstance, switch_to: str | None = None):
    """Close the current tab and optionally switch to another.
    
    Args:
        browser: The browser instance
        switch_to: Optional tab handle to switch to after closing
    """
    try:
        # Close current tab
        browser.driver.close()

        # Switch to specified tab or first available
        if switch_to:
            browser.driver.switch_to.window(switch_to)
        else:
            remaining_tabs = browser.driver.window_handles
            if remaining_tabs:
                browser.driver.switch_to.window(remaining_tabs[0])

        logger.debug("Closed tab")
    except Exception as e:
        logger.warning(f"Error closing tab: {e}")


def close_all_tabs_except(browser: BrowserInstance, keep_tab: str):
    """Close all tabs except the specified one.
    
    Args:
        browser: The browser instance
        keep_tab: The handle of the tab to keep open
    """
    current_tab = browser.driver.current_window_handle
    all_tabs = browser.driver.window_handles

    for tab in all_tabs:
        if tab != keep_tab:
            browser.driver.switch_to.window(tab)
            browser.driver.close()

    # Switch to the kept tab
    browser.driver.switch_to.window(keep_tab)
    logger.debug(f"Closed all tabs except: {keep_tab}")
