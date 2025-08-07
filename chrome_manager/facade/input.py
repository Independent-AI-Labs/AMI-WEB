import asyncio
from datetime import datetime

from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..core.instance import BrowserInstance
from ..models.browser import ClickOptions
from ..utils.exceptions import InputError


class InputController:
    def __init__(self, instance: BrowserInstance):
        self.instance = instance
        self.driver = instance.driver

    async def _perform_click(self, element: WebElement, options: ClickOptions, loop: asyncio.AbstractEventLoop) -> None:
        if options.offset_x is not None or options.offset_y is not None:
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(element, options.offset_x or 0, options.offset_y or 0)
            for _ in range(options.click_count):
                if options.button == "right":
                    actions.context_click()
                elif options.button == "middle":
                    actions.click(on_element=None)
                else:
                    actions.click()
                if options.delay > 0:
                    actions.pause(options.delay / 1000)
            await loop.run_in_executor(None, actions.perform)
        else:
            for i in range(options.click_count):
                if options.button == "right":
                    actions = ActionChains(self.driver)

                    def context_click_perform(act=actions, el=element):  # type: ignore[misc]
                        return act.context_click(el).perform()

                    await loop.run_in_executor(None, context_click_perform)
                else:
                    await loop.run_in_executor(None, element.click)
                if i < options.click_count - 1 and options.delay > 0:
                    await asyncio.sleep(options.delay / 1000)

    async def click(self, selector: str, options: ClickOptions | None = None, wait: bool = True, timeout: int = 10) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        options = options or ClickOptions()

        try:
            element = await self._find_element(selector, wait, timeout)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            await self._perform_click(element, options, loop)

            if options.wait_after > 0:
                await asyncio.sleep(options.wait_after / 1000)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Clicked element: {selector}")

        except Exception as e:
            logger.error(f"Click failed for {selector}: {e}")
            raise InputError(f"Failed to click {selector}: {e}") from e

    async def type_text(self, selector: str, text: str, clear: bool = True, delay: int = 0, wait: bool = True, timeout: int = 10) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector, wait, timeout)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()

            if clear:
                await loop.run_in_executor(None, element.clear)

            if delay > 0:
                for char in text:
                    await loop.run_in_executor(None, element.send_keys, char)
                    await asyncio.sleep(delay / 1000)
            else:
                await loop.run_in_executor(None, element.send_keys, text)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Typed text into: {selector}")

        except Exception as e:
            logger.error(f"Type text failed for {selector}: {e}")
            raise InputError(f"Failed to type into {selector}: {e}") from e

    async def _apply_modifiers(self, actions: ActionChains, modifiers: list[str], key_down: bool) -> None:
        mod_list = modifiers if key_down else reversed(modifiers)
        for mod in mod_list:
            mod_key = getattr(Keys, mod.upper(), None)
            if mod_key:
                if key_down:
                    actions.key_down(mod_key)
                else:
                    actions.key_up(mod_key)

    async def keyboard_event(self, key: str, modifiers: list[str] | None = None, element: str | None = None) -> None:
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
                await self._apply_modifiers(actions, modifiers, key_down=True)

            key_value = getattr(Keys, key.upper(), key)
            actions.send_keys(key_value)

            if modifiers:
                await self._apply_modifiers(actions, modifiers, key_down=False)

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Sent keyboard event: {key} with modifiers {modifiers}")

        except Exception as e:
            logger.error(f"Keyboard event failed: {e}")
            raise InputError(f"Failed to send keyboard event: {e}") from e

    async def mouse_move(self, x: int | None = None, y: int | None = None, element: str | None = None, steps: int = 1) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)

            if element:
                target = await self._find_element(element)
                if not target:
                    raise InputError(f"Element not found: {element}")

                if x is not None or y is not None:
                    actions.move_to_element_with_offset(target, x or 0, y or 0)
                else:
                    actions.move_to_element(target)
            elif x is not None and y is not None:
                actions.move_by_offset(x, y)

            if steps > 1:
                actions.pause(0.1 * steps)

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Moved mouse to x={x}, y={y}, element={element}")

        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            raise InputError(f"Failed to move mouse: {e}") from e

    async def drag_and_drop(self, source: str, target: str, duration: float = 0.5) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            source_element = await self._find_element(source)
            target_element = await self._find_element(target)

            if not source_element or not target_element:
                raise InputError("Source or target element not found")

            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)

            actions.click_and_hold(source_element)
            actions.pause(duration)
            actions.move_to_element(target_element)
            actions.release()

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Dragged from {source} to {target}")

        except Exception as e:
            logger.error(f"Drag and drop failed: {e}")
            raise InputError(f"Failed to drag and drop: {e}") from e

    async def hover(self, selector: str, duration: float = 0, wait: bool = True, timeout: int = 10) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector, wait, timeout)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)
            actions.move_to_element(element)

            if duration > 0:
                actions.pause(duration)

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Hovered over: {selector}")

        except Exception as e:
            logger.error(f"Hover failed for {selector}: {e}")
            raise InputError(f"Failed to hover over {selector}: {e}") from e

    async def select_option(self, selector: str, value: str | None = None, text: str | None = None, index: int | None = None) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            select = Select(element)

            if value is not None:
                await loop.run_in_executor(None, select.select_by_value, value)
            elif text is not None:
                await loop.run_in_executor(None, select.select_by_visible_text, text)
            elif index is not None:
                await loop.run_in_executor(None, select.select_by_index, index)
            else:
                raise InputError("Must specify value, text, or index")

            self.instance.last_activity = datetime.now()
            logger.debug(f"Selected option in: {selector}")

        except Exception as e:
            logger.error(f"Select option failed for {selector}: {e}")
            raise InputError(f"Failed to select option in {selector}: {e}") from e

    async def upload_file(self, selector: str, file_path: str) -> None:
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, element.send_keys, file_path)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Uploaded file to: {selector}")

        except Exception as e:
            logger.error(f"File upload failed for {selector}: {e}")
            raise InputError(f"Failed to upload file to {selector}: {e}") from e

    async def _find_element(self, selector: str, wait: bool = True, timeout: int = 10) -> WebElement | None:
        try:
            by, value = self._parse_selector(selector)

            if wait:
                wait_obj = WebDriverWait(self.driver, timeout)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, wait_obj.until, EC.presence_of_element_located((by, value)))
            return self.driver.find_element(by, value)

        except Exception as e:
            logger.warning(f"Element not found: {selector}: {e}")
            return None

    def _parse_selector(self, selector: str) -> tuple:
        if selector.startswith("//"):
            return (By.XPATH, selector)
        if selector.startswith("#"):
            return (By.ID, selector[1:])
        if selector.startswith("."):
            return (By.CLASS_NAME, selector[1:])
        if selector.startswith("[name="):
            name = selector[6:-1]
            return (By.NAME, name)
        return (By.CSS_SELECTOR, selector)
