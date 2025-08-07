import asyncio
import threading
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

    def _is_in_thread_context(self) -> bool:
        """Check if we're running in a non-main thread with its own event loop."""
        try:
            if threading.current_thread() is not threading.main_thread():
                try:
                    loop = asyncio.get_event_loop()
                    return loop.is_running()
                except RuntimeError:
                    return False
            return False
        except Exception:
            return False

    def _perform_click_sync(self, element: WebElement, options: ClickOptions) -> None:
        """Synchronous version of click for thread context."""
        import time

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
            actions.perform()
        else:
            for i in range(options.click_count):
                if options.button == "right":
                    actions = ActionChains(self.driver)
                    actions.context_click(element).perform()
                else:
                    element.click()
                if i < options.click_count - 1 and options.delay > 0:
                    time.sleep(options.delay / 1000)

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

            if self._is_in_thread_context():
                # Synchronous operation in thread context
                import time

                self._perform_click_sync(element, options)
                if options.wait_after > 0:
                    time.sleep(options.wait_after / 1000)
            else:
                # Normal async operation
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

            if self._is_in_thread_context():
                # Synchronous operation in thread context
                import time

                if clear:
                    element.clear()

                if delay > 0:
                    for char in text:
                        element.send_keys(char)
                        time.sleep(delay / 1000)
                else:
                    element.send_keys(text)
            else:
                # Normal async operation
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
                if self._is_in_thread_context():
                    # Synchronous operation in thread context
                    return wait_obj.until(EC.presence_of_element_located((by, value)))
                # Normal async operation
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

    async def click_at_coordinates(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        """Click at specific screen coordinates.

        Args:
            x: X coordinate relative to viewport
            y: Y coordinate relative to viewport
            button: Mouse button to use ("left", "right", "middle")
            click_count: Number of clicks (1 for single, 2 for double)
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)

            # Move to the absolute position and click
            # We use JavaScript to get the element at the coordinates
            script = f"return document.elementFromPoint({x}, {y})"
            element = await loop.run_in_executor(None, self.driver.execute_script, script)

            if element:
                # Get the element's position and calculate offset
                rect = await loop.run_in_executor(None, self.driver.execute_script, "return arguments[0].getBoundingClientRect()", element)
                offset_x = x - rect["left"]
                offset_y = y - rect["top"]

                actions.move_to_element_with_offset(element, offset_x, offset_y)
            else:
                # No element at coordinates, use body as reference
                body = self.driver.find_element(By.TAG_NAME, "body")
                actions.move_to_element_with_offset(body, x, y)

            for _ in range(click_count):
                if button == "right":
                    actions.context_click()
                elif button == "middle":
                    actions.click(on_element=None)
                else:
                    actions.click()

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Clicked at coordinates: ({x}, {y})")

        except Exception as e:
            logger.error(f"Click at coordinates failed: {e}")
            raise InputError(f"Failed to click at ({x}, {y}): {e}") from e

    async def drag_from_to(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        """Drag from one coordinate to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of the drag in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            actions = ActionChains(self.driver)

            # Get element at start position
            script = f"return document.elementFromPoint({start_x}, {start_y})"
            start_element = await loop.run_in_executor(None, self.driver.execute_script, script)

            if start_element:
                rect = await loop.run_in_executor(None, self.driver.execute_script, "return arguments[0].getBoundingClientRect()", start_element)
                offset_x = start_x - rect["left"]
                offset_y = start_y - rect["top"]
                actions.move_to_element_with_offset(start_element, offset_x, offset_y)
            else:
                body = self.driver.find_element(By.TAG_NAME, "body")
                actions.move_to_element_with_offset(body, start_x, start_y)

            # Click and hold
            actions.click_and_hold()
            actions.pause(duration / 2)

            # Calculate drag distance
            drag_x = end_x - start_x
            drag_y = end_y - start_y

            # Drag to end position
            actions.move_by_offset(drag_x, drag_y)
            actions.pause(duration / 2)
            actions.release()

            await loop.run_in_executor(None, actions.perform)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        except Exception as e:
            logger.error(f"Drag from coordinates failed: {e}")
            raise InputError(f"Failed to drag from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}") from e

    async def zoom(self, scale: float, center_x: int | None = None, center_y: int | None = None) -> None:
        """Perform a zoom gesture using JavaScript.

        Args:
            scale: Zoom scale (1.0 = 100%, 2.0 = 200%, 0.5 = 50%)
            center_x: X coordinate of zoom center (defaults to viewport center)
            center_y: Y coordinate of zoom center (defaults to viewport center)
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Get viewport dimensions if center not specified
            if center_x is None or center_y is None:
                viewport = await loop.run_in_executor(None, self.driver.execute_script, "return {width: window.innerWidth, height: window.innerHeight}")
                center_x = center_x or viewport["width"] // 2
                center_y = center_y or viewport["height"] // 2

            # Use CSS transform for zooming
            script = f"""
            document.body.style.transformOrigin = '{center_x}px {center_y}px';
            document.body.style.transform = 'scale({scale})';
            """
            await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Zoomed to {scale}x at ({center_x}, {center_y})")

        except Exception as e:
            logger.error(f"Zoom failed: {e}")
            raise InputError(f"Failed to zoom: {e}") from e

    async def pinch_zoom(self, scale: float, center_x: int | None = None, center_y: int | None = None) -> None:
        """Simulate a pinch zoom gesture (for touch-enabled pages).

        Args:
            scale: Zoom scale (>1 for zoom in, <1 for zoom out)
            center_x: X coordinate of zoom center
            center_y: Y coordinate of zoom center
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Get viewport center if not specified
            if center_x is None or center_y is None:
                viewport = await loop.run_in_executor(None, self.driver.execute_script, "return {width: window.innerWidth, height: window.innerHeight}")
                center_x = center_x or viewport["width"] // 2
                center_y = center_y or viewport["height"] // 2

            # Simulate pinch zoom using touch events
            script = f"""
            const centerX = {center_x};
            const centerY = {center_y};
            const scale = {scale};

            // Create touch event
            const createTouch = (x, y, id) => {{
                return new Touch({{
                    identifier: id,
                    target: document.elementFromPoint(x, y) || document.body,
                    clientX: x,
                    clientY: y,
                    pageX: x,
                    pageY: y,
                    screenX: x,
                    screenY: y
                }});
            }};

            // Initial touch points
            const distance = 100;
            const touch1Start = createTouch(centerX - distance/2, centerY, 1);
            const touch2Start = createTouch(centerX + distance/2, centerY, 2);

            // End touch points (scaled)
            const newDistance = distance * scale;
            const touch1End = createTouch(centerX - newDistance/2, centerY, 1);
            const touch2End = createTouch(centerX + newDistance/2, centerY, 2);

            // Dispatch touch events
            const target = document.elementFromPoint(centerX, centerY) || document.body;

            const startEvent = new TouchEvent('touchstart', {{
                touches: [touch1Start, touch2Start],
                targetTouches: [touch1Start, touch2Start],
                changedTouches: [touch1Start, touch2Start],
                bubbles: true,
                cancelable: true
            }});

            const moveEvent = new TouchEvent('touchmove', {{
                touches: [touch1End, touch2End],
                targetTouches: [touch1End, touch2End],
                changedTouches: [touch1End, touch2End],
                bubbles: true,
                cancelable: true
            }});

            const endEvent = new TouchEvent('touchend', {{
                touches: [],
                targetTouches: [],
                changedTouches: [touch1End, touch2End],
                bubbles: true,
                cancelable: true
            }});

            target.dispatchEvent(startEvent);
            target.dispatchEvent(moveEvent);
            target.dispatchEvent(endEvent);

            return true;
            """

            await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.last_activity = datetime.now()
            logger.debug(f"Pinch zoomed to {scale}x at ({center_x}, {center_y})")

        except Exception as e:
            logger.error(f"Pinch zoom failed: {e}")
            raise InputError(f"Failed to pinch zoom: {e}") from e

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> None:
        """Perform a swipe gesture.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of the swipe in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Simulate swipe using touch events
            script = f"""
            const startX = {start_x};
            const startY = {start_y};
            const endX = {end_x};
            const endY = {end_y};
            const duration = {duration * 1000};  // Convert to milliseconds

            const startElement = document.elementFromPoint(startX, startY) || document.body;
            const endElement = document.elementFromPoint(endX, endY) || document.body;

            // Create touch events
            const touchStart = new TouchEvent('touchstart', {{
                touches: [new Touch({{
                    identifier: 1,
                    target: startElement,
                    clientX: startX,
                    clientY: startY,
                    pageX: startX,
                    pageY: startY
                }})],
                bubbles: true,
                cancelable: true
            }});

            const touchMove = new TouchEvent('touchmove', {{
                touches: [new Touch({{
                    identifier: 1,
                    target: endElement,
                    clientX: endX,
                    clientY: endY,
                    pageX: endX,
                    pageY: endY
                }})],
                bubbles: true,
                cancelable: true
            }});

            const touchEnd = new TouchEvent('touchend', {{
                touches: [],
                changedTouches: [new Touch({{
                    identifier: 1,
                    target: endElement,
                    clientX: endX,
                    clientY: endY,
                    pageX: endX,
                    pageY: endY
                }})],
                bubbles: true,
                cancelable: true
            }});

            // Dispatch events
            startElement.dispatchEvent(touchStart);
            setTimeout(() => {{
                startElement.dispatchEvent(touchMove);
                setTimeout(() => {{
                    endElement.dispatchEvent(touchEnd);
                }}, duration / 2);
            }}, duration / 2);

            return true;
            """

            await loop.run_in_executor(None, self.driver.execute_script, script)
            await asyncio.sleep(duration)  # Wait for swipe to complete

            self.instance.last_activity = datetime.now()
            logger.debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        except Exception as e:
            logger.error(f"Swipe failed: {e}")
            raise InputError(f"Failed to swipe: {e}") from e
