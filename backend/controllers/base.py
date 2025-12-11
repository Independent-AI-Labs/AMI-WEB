"""Base controller class for facade controllers."""

import asyncio
from collections.abc import Callable
import time
from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


if TYPE_CHECKING:
    from browser.backend.core.browser.instance import BrowserInstance

from browser.backend.utils.exceptions import NavigationError
from browser.backend.utils.selectors import parse_selector
from browser.backend.utils.threading import is_in_thread_context


class BaseController:
    """Base class for all facade controllers with common functionality."""

    def __init__(self, instance: "BrowserInstance"):
        """Initialize the base controller.

        Args:
            instance: The browser instance to control
        """
        self.instance: BrowserInstance = instance
        self.driver: WebDriver | None = instance.driver

    def _is_in_thread_context(self) -> bool:
        """Check if we're running in a non-main thread with its own event loop.

        This is used to determine whether to use sync or async operations.

        Returns:
            bool: True if running in a thread with an active event loop
        """
        return is_in_thread_context()

    def _parse_selector(self, selector: str) -> tuple[Any, str]:
        """Parse a selector string into a Selenium By locator.

        Supports various selector formats:
        - CSS selectors (default)
        - XPath selectors (starting with // or /)
        - ID selectors (starting with #)
        - Class selectors (starting with .)
        - Name selectors (starting with @)
        - Tag selectors (simple tag names)

        Args:
            selector: The selector string to parse

        Returns:
            Tuple[By, str]: The By locator type and the selector value
        """
        by_str, value = parse_selector(selector)

        # Convert string By type to actual By constant
        by_map = {
            "xpath": By.XPATH,
            "id": By.ID,
            "class name": By.CLASS_NAME,
            "name": By.NAME,
            "tag name": By.TAG_NAME,
            "css selector": By.CSS_SELECTOR,
        }

        return by_map.get(by_str, By.CSS_SELECTOR), value

    async def _execute_in_context(self, sync_func: Callable[..., Any], async_func: Callable[..., Any] | None = None, *args: Any, **kwargs: Any) -> Any:
        """Execute function in appropriate context (sync or async).

        Args:
            sync_func: The synchronous version of the function to call
            async_func: Optional async version (if different from sync). If None, runs sync in executor
            *args, **kwargs: Arguments to pass to the function
        """
        if self._is_in_thread_context():
            # Run in sync context
            return sync_func(*args, **kwargs)
        # Run in async context
        if async_func:
            return await async_func(*args, **kwargs)
        # Run sync function in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)

    async def _sleep_in_context(self, duration: float) -> None:
        """Sleep for a duration handling both sync and async contexts."""

        if self._is_in_thread_context():
            time.sleep(duration)
        else:
            await asyncio.sleep(duration)

    def _ensure_driver(self) -> WebDriver:
        """Ensure driver is available and return it, helping with type checking.

        Returns:
            The WebDriver instance

        Raises:
            NavigationError: If driver is not initialized
        """
        if self.driver is None:
            raise NavigationError("Browser not initialized")
        return self.driver
