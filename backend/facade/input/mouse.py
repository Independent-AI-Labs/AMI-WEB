"""Mouse input control and gesture handling."""

import asyncio
import time

from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.facade.base import BaseController
from browser.backend.facade.utils import parameterized_js_execution
from browser.backend.models.browser import ClickOptions
from browser.backend.utils.exceptions import InputError


class MouseController(BaseController):
    """Handles mouse operations and gestures."""

    def _perform_click_sync(self, element: WebElement, options: ClickOptions) -> None:
        """Synchronous version of click for thread context."""
        if not self.driver:
            raise InputError("Browser not initialized")
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
        """Asynchronous click operation."""
        if not self.driver:
            raise InputError("Browser not initialized")

        if options.offset_x is not None or options.offset_y is not None:
            await self._perform_offset_click(element, options, loop)
        else:
            await self._perform_standard_click(element, options, loop)

    async def _perform_offset_click(self, element: WebElement, options: ClickOptions, loop: asyncio.AbstractEventLoop) -> None:
        """Perform click with offset using ActionChains."""
        if not self.driver:
            raise InputError("Browser not initialized")
        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(element, options.offset_x or 0, options.offset_y or 0)

        for _ in range(options.click_count):
            self._add_click_action(actions, options.button)
            if options.delay > 0:
                actions.pause(options.delay / 1000)

        await loop.run_in_executor(None, actions.perform)

    async def _perform_standard_click(self, element: WebElement, options: ClickOptions, loop: asyncio.AbstractEventLoop) -> None:
        """Perform standard click without offset."""
        for i in range(options.click_count):
            if options.button == "right":
                await self._perform_context_click(element, loop)
            else:
                await loop.run_in_executor(None, element.click)

            if i < options.click_count - 1 and options.delay > 0:
                await asyncio.sleep(options.delay / 1000)

    def _add_click_action(self, actions: ActionChains, button: str) -> None:
        """Add appropriate click action based on button type."""
        if button == "right":
            actions.context_click()
        elif button == "middle":
            actions.click(on_element=None)
        else:
            actions.click()

    async def _perform_context_click(self, element: WebElement, loop: asyncio.AbstractEventLoop) -> None:
        """Perform right-click (context click) on element."""
        if not self.driver:
            raise InputError("Browser not initialized")
        actions = ActionChains(self.driver)

        def context_click_perform(act: ActionChains = actions, el: WebElement = element) -> None:
            return act.context_click(el).perform()

        await loop.run_in_executor(None, context_click_perform)

    async def click(self, selector: str, options: ClickOptions | None = None, wait: bool = True, timeout: int = 10) -> None:
        """Click on an element.

        Args:
            selector: CSS selector, XPath, or other selector format
            options: Click options (button, count, delay, etc.)
            wait: Whether to wait for element
            timeout: Maximum wait time in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        options = options or ClickOptions()

        try:
            element = await self._find_element(selector, wait, timeout)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                self._perform_click_sync(element, options)
                if options.wait_after > 0:
                    time.sleep(options.wait_after / 1000)
            else:
                loop = asyncio.get_event_loop()
                await self._perform_click(element, options, loop)
                if options.wait_after > 0:
                    await asyncio.sleep(options.wait_after / 1000)

            self.instance.update_activity()
            logger.debug(f"Clicked element: {selector}")

        except Exception as e:
            logger.error(f"Click failed for {selector}: {e}")
            raise InputError(f"Failed to click {selector}: {e}") from e

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
            script = parameterized_js_execution(
                """
                var element = document.elementFromPoint({x}, {y}) || document.body;

                if ({button} === 'right') {{
                    var event = new MouseEvent('contextmenu', {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: {x},
                        clientY: {y}
                    }});
                    element.dispatchEvent(event);
                }} else if ({click_count} === 2) {{
                    // For double-click, dispatch both click and dblclick events
                    var clickEvent = new MouseEvent('click', {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: {x},
                        clientY: {y},
                        detail: 1
                    }});
                    element.dispatchEvent(clickEvent);

                    var dblClickEvent = new MouseEvent('dblclick', {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: {x},
                        clientY: {y},
                        detail: 2
                    }});
                    element.dispatchEvent(dblClickEvent);
                }} else {{
                    var event = new MouseEvent('click', {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: {x},
                        clientY: {y},
                        detail: {click_count}
                    }});
                    element.dispatchEvent(event);
                }}
                return {{x: {x}, y: {y}}};
                """,
                x=x,
                y=y,
                button=button,
                click_count=click_count,
            )

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Clicked at coordinates: ({x}, {y})")

        except Exception as e:
            logger.error(f"Click at coordinates failed: {e}")
            raise InputError(f"Failed to click at ({x}, {y}): {e}") from e

    async def mouse_move(self, x: int | None = None, y: int | None = None, element: str | None = None, steps: int = 1) -> None:
        """Move mouse to position or element.

        Args:
            x: X coordinate offset
            y: Y coordinate offset
            element: CSS selector of target element
            steps: Number of intermediate steps for smooth movement
        """
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

            self.instance.update_activity()
            logger.debug(f"Moved mouse to x={x}, y={y}, element={element}")

        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            raise InputError(f"Failed to move mouse: {e}") from e

    async def hover(self, selector: str, duration: float = 0, wait: bool = True, timeout: int = 10) -> None:
        """Hover over an element.

        Args:
            selector: CSS selector for the element
            duration: How long to hover in seconds
            wait: Whether to wait for element
            timeout: Maximum wait time
        """
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

            self.instance.update_activity()
            logger.debug(f"Hovered over: {selector}")

        except Exception as e:
            logger.error(f"Hover failed for {selector}: {e}")
            raise InputError(f"Failed to hover over {selector}: {e}") from e

    async def drag_and_drop(self, source: str, target: str, duration: float = 0.5) -> None:
        """Drag from source element to target element.

        Args:
            source: CSS selector for source element
            target: CSS selector for target element
            duration: Duration of the drag operation
        """
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

            self.instance.update_activity()
            logger.debug(f"Dragged from {source} to {target}")

        except Exception as e:
            logger.error(f"Drag and drop failed: {e}")
            raise InputError(f"Failed to drag and drop: {e}") from e

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
            script = parameterized_js_execution(
                """
            var startX = {start_x};
            var startY = {start_y};
            var endX = {end_x};
            var endY = {end_y};
            var steps = 10;

            var startElement = document.elementFromPoint(startX, startY) || document.body;

            // Dispatch mousedown at start position
            var mouseDownEvent = new MouseEvent('mousedown', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: startX,
                clientY: startY,
                button: 0,
                buttons: 1
            }});
            startElement.dispatchEvent(mouseDownEvent);

            // Dispatch multiple mousemove events for smooth dragging
            for (var i = 1; i <= steps; i++) {{
                var progress = i / steps;
                var currentX = startX + (endX - startX) * progress;
                var currentY = startY + (endY - startY) * progress;

                var mouseMoveEvent = new MouseEvent('mousemove', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: currentX,
                    clientY: currentY,
                    button: 0,
                    buttons: 1
                }});
                document.dispatchEvent(mouseMoveEvent);
            }}

            // Dispatch mouseup at end position
            var endElement = document.elementFromPoint(endX, endY) || document.body;
            var mouseUpEvent = new MouseEvent('mouseup', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: endX,
                clientY: endY,
                button: 0,
                buttons: 0
            }});
            endElement.dispatchEvent(mouseUpEvent);

            return true;
            """,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
            )

            if self._is_in_thread_context():
                self.driver.execute_script(script)
                time.sleep(duration)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)
                await asyncio.sleep(duration)

            self.instance.update_activity()
            logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        except Exception as e:
            logger.error(f"Drag from coordinates failed: {e}")
            raise InputError(f"Failed to drag from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}") from e

    async def _find_element(self, selector: str, wait: bool = True, timeout: int = 10) -> WebElement | None:
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
                return await loop.run_in_executor(None, wait_obj.until, EC.presence_of_element_located((by, value)))
            return self.driver.find_element(by, value)

        except Exception as e:
            logger.warning(f"Element not found: {selector}: {e}")
            return None
