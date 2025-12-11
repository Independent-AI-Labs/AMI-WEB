"""Wait conditions and element waiting functionality."""

import asyncio

from loguru import logger
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.controllers.base import BaseController
from browser.backend.models.browser import WaitCondition
from browser.backend.utils.exceptions import NavigationError


class Waiter(BaseController):
    """Handles wait conditions and element waiting."""

    async def wait_for_navigation(self, timeout: int = 30) -> None:
        """Wait for page navigation to complete."""
        await self._wait_for_load(timeout)

    async def wait_for_element(self, selector: str, timeout: int = 30, visible: bool = True) -> bool:
        """Wait for an element to be present or visible.

        Args:
            selector: CSS selector, XPath, or other selector format
            timeout: Maximum time to wait in seconds
            visible: If True, wait for visibility; if False, wait for presence

        Returns:
            True if element found, False otherwise
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            wait = WebDriverWait(self.driver, timeout)
            by, value = self._parse_selector(selector)
            condition = (
                expected_conditions.visibility_of_element_located((by, value)) if visible else expected_conditions.presence_of_element_located((by, value))
            )

            if self._is_in_thread_context():
                element = wait.until(condition)
            else:
                loop = asyncio.get_event_loop()
                element = await loop.run_in_executor(None, wait.until, condition)

            return element is not None

        except Exception as e:
            logger.warning(f"Element wait failed for {selector}: {e}")
            return False

    def _wait_for_load_sync(self, timeout: int = 30) -> None:
        """Synchronous version of _wait_for_load for thread context."""
        if not self.driver:
            raise NavigationError("Browser not initialized")
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
        except Exception as e:
            logger.warning(f"Page load wait timeout: {e}")

    def _wait_for_condition_sync(self, condition: WaitCondition, timeout: int) -> None:
        """Synchronous version of _wait_for_condition for thread context."""
        if not self.driver:
            raise NavigationError("Browser not initialized")
        wait = WebDriverWait(self.driver, timeout, poll_frequency=condition.poll_frequency)

        if condition.type == "load":
            self._wait_for_load_sync(timeout)

        elif condition.type == "networkidle":
            wait.until(
                lambda driver: driver.execute_script(
                    """
                    return performance.getEntriesByType('resource')
                        .filter(r => !r.responseEnd).length === 0
                """,
                ),
            )

        elif condition.type == "element" and condition.target:
            by, value = self._parse_selector(condition.target)
            wait.until(expected_conditions.presence_of_element_located((by, value)))

        elif condition.type == "function" and condition.target:
            target_script = condition.target
            if target_script is not None:
                wait.until(lambda driver: driver.execute_script(target_script))

    async def _wait_for_load(self, timeout: int = 30) -> None:
        """Wait for page to finish loading."""
        if not self.driver:
            raise NavigationError("Browser not initialized")
        try:
            wait = WebDriverWait(self.driver, timeout)
            loop = asyncio.get_event_loop()

            await loop.run_in_executor(
                None,
                wait.until,
                lambda driver: driver.execute_script("return document.readyState") == "complete",
            )
        except Exception as e:
            logger.warning(f"Page load wait timeout: {e}")

    async def _wait_for_condition(self, condition: WaitCondition, timeout: int) -> None:
        """Wait for a specific condition to be met."""
        if not self.driver:
            raise NavigationError("Browser not initialized")
        wait = WebDriverWait(self.driver, timeout, poll_frequency=condition.poll_frequency)
        loop = asyncio.get_event_loop()

        if condition.type == "load":
            await self._wait_for_load(timeout)

        elif condition.type == "networkidle":
            await loop.run_in_executor(
                None,
                wait.until,
                lambda driver: driver.execute_script(
                    """
                    return performance.getEntriesByType('resource')
                        .filter(r => !r.responseEnd).length === 0
                """,
                ),
            )

        elif condition.type == "element" and condition.target:
            by, value = self._parse_selector(condition.target)
            await loop.run_in_executor(None, wait.until, expected_conditions.presence_of_element_located((by, value)))

        elif condition.type == "function" and condition.target:
            target_script = condition.target
            if target_script is not None:
                await loop.run_in_executor(
                    None,
                    wait.until,
                    lambda driver: driver.execute_script(target_script),
                )

    async def wait_for_url_change(self, current_url: str, timeout: int = 30) -> str:
        """Wait for the URL to change from the current one.

        Args:
            current_url: The current URL to wait for change from
            timeout: Maximum time to wait

        Returns:
            The new URL after change
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            wait = WebDriverWait(self.driver, timeout)

            if self._is_in_thread_context():
                wait.until(lambda driver: driver.current_url != current_url)
                return str(self.driver.current_url)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, wait.until, lambda driver: driver.current_url != current_url)
            return str(self.driver.current_url)

        except Exception as e:
            logger.warning(f"URL change wait timeout: {e}")
            raise NavigationError(f"URL did not change from {current_url} within {timeout} seconds") from e
