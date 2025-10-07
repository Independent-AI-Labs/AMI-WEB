"""Keyboard input control and text entry."""

import asyncio
import time

from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.facade.base import BaseController
from browser.backend.utils.exceptions import InputError

# Minimum number of keys required for a key combination
MIN_KEYS_FOR_COMBINATION = 2


class KeyboardController(BaseController):
    """Handles keyboard input and text entry operations."""

    async def _type_text_sync(
        self, element: WebElement, text: str, clear: bool, delay: int
    ) -> None:
        """Type text synchronously in thread context."""
        if clear:
            element.clear()

        if delay > 0:
            for char in text:
                element.send_keys(char)
                time.sleep(delay / 1000)
        else:
            element.send_keys(text)

    async def _type_text_async(
        self, element: WebElement, text: str, clear: bool, delay: int
    ) -> None:
        """Type text asynchronously."""
        loop = asyncio.get_event_loop()

        if clear:
            await loop.run_in_executor(None, element.clear)

        if delay > 0:
            for char in text:
                await loop.run_in_executor(None, element.send_keys, char)
                await asyncio.sleep(delay / 1000)
        else:
            await loop.run_in_executor(None, element.send_keys, text)

    async def type_text(
        self,
        selector: str,
        text: str,
        clear: bool = True,
        delay: int = 0,
        wait: bool = True,
        timeout: int = 10,
    ) -> None:
        """Type text into an element.

        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear: Whether to clear existing text first
            delay: Delay between keystrokes in milliseconds
            wait: Whether to wait for element
            timeout: Maximum wait time in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector, wait, timeout)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                await self._type_text_sync(element, text, clear, delay)
            else:
                await self._type_text_async(element, text, clear, delay)

            self.instance.update_activity()
            logger.debug(f"Typed text into: {selector}")

        except Exception as e:
            logger.error(f"Type text failed for {selector}: {e}")
            raise InputError(f"Failed to type into {selector}: {e}") from e

    async def keyboard_event(
        self,
        key: str,
        modifiers: list[str | None] | None = None,
        element: str | None = None,
    ) -> None:
        """Send a keyboard event.

        Args:
            key: Key to press (can be special key like 'ENTER', 'TAB', etc.)
            modifiers: List of modifier keys ('SHIFT', 'CTRL', 'ALT')
            element: Optional CSS selector to focus before sending key
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)

            if element:
                target = await self._find_element(element)
                if target:
                    actions.move_to_element(target)

            if modifiers:
                clean_modifiers = [mod for mod in modifiers if mod is not None]
                await self._apply_modifiers(actions, clean_modifiers, key_down=True)

            key_value = getattr(Keys, key.upper(), key)
            actions.send_keys(key_value)

            if modifiers:
                clean_modifiers = [mod for mod in modifiers if mod is not None]
                await self._apply_modifiers(actions, clean_modifiers, key_down=False)

            await loop.run_in_executor(None, actions.perform)

            self.instance.update_activity()
            logger.debug(f"Sent keyboard event: {key} with modifiers {modifiers}")

        except Exception as e:
            logger.error(f"Keyboard event failed: {e}")
            raise InputError(f"Failed to send keyboard event: {e}") from e

    async def press_key(self, key: str) -> None:
        """Press a single key.

        Args:
            key: Key to press (can be special key like 'ENTER', 'TAB', etc.)
        """
        await self.keyboard_event(key)

    async def key_combination(self, *keys: str) -> None:
        """Press a key combination.

        Args:
            *keys: Keys to press together (e.g., 'CTRL', 'A')
        """
        if len(keys) < MIN_KEYS_FOR_COMBINATION:
            raise InputError("Key combination requires at least 2 keys")

        modifiers: list[str | None] = list(keys[:-1])
        key = keys[-1]
        await self.keyboard_event(key, modifiers)

    async def clear_input(self, selector: str) -> None:
        """Clear the text in an input element.

        Args:
            selector: CSS selector for the input element
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                element.clear()
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, element.clear)

            self.instance.update_activity()
            logger.debug(f"Cleared input: {selector}")

        except Exception as e:
            logger.error(f"Clear input failed for {selector}: {e}")
            raise InputError(f"Failed to clear {selector}: {e}") from e

    async def _apply_modifiers(
        self, actions: ActionChains, modifiers: list[str], key_down: bool
    ) -> None:
        """Apply or release modifier keys.

        Args:
            actions: ActionChains instance
            modifiers: List of modifier keys
            key_down: True to press, False to release
        """
        mod_list = modifiers if key_down else reversed(modifiers)
        for mod in mod_list:
            mod_key = getattr(Keys, mod.upper(), None)
            if mod_key:
                if key_down:
                    actions.key_down(mod_key)
                else:
                    actions.key_up(mod_key)

    async def _find_element(
        self, selector: str, wait: bool = True, timeout: int = 10
    ) -> WebElement | None:
        """Find an element on the page."""
        if not self.driver:
            raise InputError("Browser not initialized")
        try:
            by, value = self._parse_selector(selector)

            if wait:
                wait_obj = WebDriverWait(self.driver, timeout)
                if self._is_in_thread_context():
                    return wait_obj.until(EC.presence_of_element_located((by, value)))
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, wait_obj.until, EC.presence_of_element_located((by, value))
                )
            return self.driver.find_element(by, value)

        except Exception as e:
            logger.warning(f"Element not found: {selector}: {e}")
            return None
