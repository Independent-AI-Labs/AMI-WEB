"""Base controller class for facade controllers."""

import asyncio
import threading
from typing import Any

from loguru import logger
from selenium.webdriver.common.by import By

from ..core.browser.instance import BrowserInstance


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
        try:
            # Check if we're in the main thread
            current_thread = threading.current_thread()
            main_thread = threading.main_thread()

            # Log the thread info for debugging
            logger.debug(f"Thread check: current={current_thread.name}, " f"main={main_thread.name}, is_main={current_thread is main_thread}")

            if current_thread is not main_thread:
                # Check if this thread has an event loop
                try:
                    loop = asyncio.get_event_loop()
                    is_running = loop.is_running()
                    logger.debug(f"Thread has event loop, running={is_running}")
                    return is_running
                except RuntimeError as e:
                    logger.debug(f"Thread has no event loop: {e}")
                    return False
            return False
        except Exception as e:
            logger.debug(f"Error in thread check: {e}")
            return False

    def _parse_selector(self, selector: str) -> tuple[Any, str]:  # noqa: PLR0911
        """Parse a selector string into a Selenium By locator.

        Supports various selector formats:
        - CSS selectors (default)
        - XPath selectors (starting with // or /)
        - ID selectors (starting with #)
        - Class selectors (starting with .)
        - Name selectors (starting with name=)
        - Tag selectors (simple tag names)

        Args:
            selector: The selector string to parse

        Returns:
            Tuple[By, str]: The By locator type and the selector value
        """
        if selector.startswith(("//", "/")):
            return (By.XPATH, selector)
        if selector.startswith("#"):
            # ID selector - use By.ID for better performance
            return (By.ID, selector[1:])
        if selector.startswith("."):
            # Class selector - use By.CLASS_NAME for single classes
            class_name = selector[1:]
            if " " not in class_name and "." not in class_name:
                return (By.CLASS_NAME, class_name)
            # Multiple classes or complex selector - use CSS
            return (By.CSS_SELECTOR, selector)
        if selector.startswith("name="):
            return (By.NAME, selector[5:])

        tag_names = {
            "a",
            "button",
            "div",
            "span",
            "input",
            "select",
            "textarea",
            "img",
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "li",
            "table",
            "tr",
            "td",
            "th",
            "form",
            "label",
        }
        if selector.lower() in tag_names:
            # Simple tag name
            return (By.TAG_NAME, selector)
        # Default to CSS selector
        return (By.CSS_SELECTOR, selector)
