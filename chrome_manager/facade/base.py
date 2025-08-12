"""Base controller class for facade controllers."""

from typing import Any

from selenium.webdriver.common.by import By

from ..core.browser.instance import BrowserInstance
from ..utils import is_in_thread_context, parse_selector


class BaseController:
    """Base class for all facade controllers with common functionality."""

    def __init__(self, instance: BrowserInstance):
        """Initialize the base controller.

        Args:
            instance: The browser instance to control
        """
        self.instance = instance
        self.driver = instance.driver

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
