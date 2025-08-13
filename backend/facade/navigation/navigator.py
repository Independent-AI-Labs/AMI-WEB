"""Core navigation functionality for browser control."""

import asyncio
import time

from loguru import logger

from ...models.browser import PageResult, WaitCondition
from ...utils.exceptions import NavigationError
from ..base import BaseController


class Navigator(BaseController):
    """Handles core browser navigation operations."""

    async def navigate(self, url: str, wait_for: WaitCondition | None = None, timeout: int = 30) -> PageResult:
        """Navigate to a URL with optional wait conditions.

        Args:
            url: The URL to navigate to
            wait_for: Optional wait condition to apply after navigation
            timeout: Maximum time to wait in seconds

        Returns:
            PageResult with navigation details

        Raises:
            NavigationError: If navigation fails
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        in_thread = self._is_in_thread_context()
        logger.debug(f"Navigator.navigate: in_thread={in_thread}, url={url}")

        if in_thread:
            return self._navigate_sync(url, wait_for, timeout)
        return await self._navigate_async(url, wait_for, timeout)

    def _navigate_sync(self, url: str, wait_for: WaitCondition | None, timeout: int) -> PageResult:
        """Synchronous navigation for thread context."""
        start_time = time.time()

        try:
            logger.debug(f"Calling driver.get synchronously for {url}")
            self.driver.get(url)
            logger.debug(f"driver.get completed for {url}")

            if wait_for:
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                waiter._wait_for_condition_sync(wait_for, timeout)
            else:
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                waiter._wait_for_load_sync(timeout)

            load_time = time.time() - start_time

            title = self.driver.title
            current_url = self.driver.current_url
            content_length = self.driver.execute_script("return document.documentElement.innerHTML.length")

            self.instance.update_activity()

            result = PageResult(url=current_url, title=title, status_code=200, load_time=load_time, content_length=content_length)
            logger.debug(f"Navigation result: {result}")
            return result

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def _navigate_async(self, url: str, wait_for: WaitCondition | None, timeout: int) -> PageResult:
        """Asynchronous navigation for normal context."""
        start_time = asyncio.get_event_loop().time()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.get, url)

            if wait_for:
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                await waiter._wait_for_condition(wait_for, timeout)
            else:
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                await waiter._wait_for_load(timeout)

            load_time = asyncio.get_event_loop().time() - start_time

            title = self.driver.title
            current_url = self.driver.current_url

            content_length = await loop.run_in_executor(None, self.driver.execute_script, "return document.documentElement.innerHTML.length")

            self.instance.update_activity()

            return PageResult(url=current_url, title=title, status_code=200, load_time=load_time, content_length=content_length)

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def back(self) -> None:
        """Navigate back in browser history."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                self.driver.back()
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                waiter._wait_for_load_sync()
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.back)
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                await waiter._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go back: {e}") from e

    async def forward(self) -> None:
        """Navigate forward in browser history."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                self.driver.forward()
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                waiter._wait_for_load_sync()
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.forward)
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                await waiter._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to go forward: {e}") from e

    async def refresh(self, force: bool = False) -> None:
        """Refresh the current page.

        Args:
            force: If True, force reload from server (bypass cache)
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                if force:
                    self.driver.execute_script("location.reload(true)")
                else:
                    self.driver.refresh()
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                waiter._wait_for_load_sync()
            else:
                loop = asyncio.get_event_loop()
                if force:
                    await loop.run_in_executor(None, self.driver.execute_script, "location.reload(true)")
                else:
                    await loop.run_in_executor(None, self.driver.refresh)
                from .waiter import Waiter

                waiter = Waiter(self.instance)
                await waiter._wait_for_load()
        except Exception as e:
            raise NavigationError(f"Failed to refresh: {e}") from e
