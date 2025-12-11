"""Browser storage management (localStorage and sessionStorage)."""

import asyncio
from typing import Any

from loguru import logger

from browser.backend.controllers.base import BaseController
from browser.backend.utils.exceptions import NavigationError


class StorageController(BaseController):
    """Controller for browser storage operations."""

    async def get_local_storage(self, key: str | None = None) -> dict[str, Any] | str | None:
        """Get localStorage data.

        Args:
            key: Specific key to retrieve, or None for all items

        Returns:
            Value for the key (str or None), or dict of all items if key is None
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if key:
                script = f"return localStorage.getItem('{key}');"
            else:
                script = """
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
                """

            if self._is_in_thread_context():
                raw_result = self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                raw_result = await loop.run_in_executor(None, self.driver.execute_script, script)

            if raw_result is not None:
                result: dict[str, str] | str | None = raw_result
                return result
            return {} if key is None else None

        except Exception as e:
            logger.error(f"Failed to get localStorage: {e}")
            raise NavigationError(f"Failed to get localStorage: {e}") from e

    async def set_local_storage(self, key: str, value: str) -> None:
        """Set a localStorage item.

        Args:
            key: Storage key
            value: Value to store (will be converted to string)
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = f"localStorage.setItem('{key}', '{value}');"

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Set localStorage['{key}']")

        except Exception as e:
            logger.error(f"Failed to set localStorage: {e}")
            raise NavigationError(f"Failed to set localStorage: {e}") from e

    async def remove_local_storage(self, key: str) -> None:
        """Remove a localStorage item.

        Args:
            key: Storage key to remove
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = f"localStorage.removeItem('{key}');"

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Removed localStorage['{key}']")

        except Exception as e:
            logger.error(f"Failed to remove localStorage item: {e}")
            raise NavigationError(f"Failed to remove localStorage item: {e}") from e

    async def clear_local_storage(self) -> None:
        """Clear all localStorage items."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = "localStorage.clear();"

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug("Cleared all localStorage")

        except Exception as e:
            logger.error(f"Failed to clear localStorage: {e}")
            raise NavigationError(f"Failed to clear localStorage: {e}") from e

    async def get_session_storage(self, key: str | None = None) -> dict[str, Any] | str | None:
        """Get sessionStorage data.

        Args:
            key: Specific key to retrieve, or None for all items

        Returns:
            Value for the key (str or None), or dict of all items if key is None
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if key:
                script = f"return sessionStorage.getItem('{key}');"
            else:
                script = """
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
                """

            if self._is_in_thread_context():
                raw_result = self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                raw_result = await loop.run_in_executor(None, self.driver.execute_script, script)

            if raw_result is not None:
                result: dict[str, str] | str | None = raw_result
                return result
            return {} if key is None else None

        except Exception as e:
            logger.error(f"Failed to get sessionStorage: {e}")
            raise NavigationError(f"Failed to get sessionStorage: {e}") from e

    async def set_session_storage(self, key: str, value: str) -> None:
        """Set a sessionStorage item.

        Args:
            key: Storage key
            value: Value to store (will be converted to string)
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = f"sessionStorage.setItem('{key}', '{value}');"

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Set sessionStorage['{key}']")

        except Exception as e:
            logger.error(f"Failed to set sessionStorage: {e}")
            raise NavigationError(f"Failed to set sessionStorage: {e}") from e
