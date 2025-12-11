"""Utilities for handling async/sync execution in controllers."""

import asyncio
from collections.abc import Callable
import time
from typing import Any, TypeVar

from selenium.webdriver.remote.webdriver import WebDriver

from browser.backend.utils.threading import is_in_thread_context


T = TypeVar("T")


class AsyncSyncExecutor:
    """Utility class for executing operations in both sync and async contexts."""

    def __init__(self, driver: WebDriver):
        self.driver = driver

    async def execute_script(self, script: str, *args: Any) -> Any:
        """Execute JavaScript script handling both sync and async contexts."""
        if self._is_in_thread_context():
            return self.driver.execute_script(script, *args)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.driver.execute_script, script, *args)

    def _is_in_thread_context(self) -> bool:
        """Check if we're running in a non-main thread with its own event loop."""

        return is_in_thread_context()

    async def wait_for_condition(self, condition_func: Callable[[], bool], timeout: float = 10.0) -> bool:
        """Wait for a condition to be true in both sync and async contexts."""

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_in_thread_context():
                if condition_func():
                    return True
                time.sleep(0.1)
            else:
                if condition_func():
                    return True
                await asyncio.sleep(0.1)

        return False

    async def sleep(self, duration: float) -> None:
        """Sleep for a duration handling both sync and async contexts."""

        if self._is_in_thread_context():
            time.sleep(duration)
        else:
            await asyncio.sleep(duration)
