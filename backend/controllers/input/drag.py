"""Drag and drop operations for mouse interactions."""

import asyncio
import time

from loguru import logger
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.controllers.base import BaseController
from browser.backend.controllers.utils import parameterized_js_execution
from browser.backend.utils.exceptions import InputError


class DragController(BaseController):
    """Handles drag and drop operations."""

    async def drag_and_drop(self, source_selector: str, target_selector: str) -> None:
        """Drag an element from source to target.

        Args:
            source_selector: CSS selector for the source element
            target_selector: CSS selector for the target element
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            source_element = await self._find_element(source_selector, wait=True)
            if not source_element:
                raise InputError(f"Source element not found: {source_selector}")

            target_element = await self._find_element(target_selector, wait=True)
            if not target_element:
                raise InputError(f"Target element not found: {target_selector}")

            # Get element locations
            source_x = source_element.location_once_scrolled_into_view["x"] + (source_element.size["width"] // 2)
            source_y = source_element.location_once_scrolled_into_view["y"] + (source_element.size["height"] // 2)
            target_x = target_element.location_once_scrolled_into_view["x"] + (target_element.size["width"] // 2)
            target_y = target_element.location_once_scrolled_into_view["y"] + (target_element.size["height"] // 2)

            await self.drag_coordinates(source_x, source_y, target_x, target_y)

        except Exception as e:
            logger.error(f"Drag and drop failed: {e}")
            raise InputError(f"Failed to drag drop from {source_selector} to {target_selector}: {e}") from e

    async def drag_coordinates(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        """Drag from one coordinate to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Duration of the drag operation in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            # Use JavaScript to simulate mouse events for more reliable dragging
            # This avoids potential issues with ActionChains in different environments
            script = parameterized_js_execution(
                """
            // Dispatch mousedown at start position
            var startElement = document.elementFromPoint({start_x}, {start_y}) || document.body;
            var mouseDownEvent = new MouseEvent('mousedown', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: {start_x},
                clientY: {start_y},
                button: 0,
                buttons: 1
            }});
            startElement.dispatchEvent(mouseDownEvent);

            // Dispatch mousemove events along the path
            var steps = Math.max(Math.abs({end_x} - {start_x}), Math.abs({end_y} - {start_y}));
            var stepDuration = {duration} / steps;
            for (var i = 1; i <= steps; i++) {{
                var currentX = {start_x} + Math.round((({end_x} - {start_x}) * i) / steps);
                var currentY = {start_y} + Math.round((({end_y} - {start_y}) * i) / steps);

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

                // Small delay between steps - approximated in JS since we can't use Python sleep
                // The stepDuration will determine the actual speed
            }}

            // Dispatch mouseup at end position
            var endElement = document.elementFromPoint({end_x}, {end_y}) || document.body;
            var mouseUpEvent = new MouseEvent('mouseup', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: {end_x},
                clientY: {end_y},
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
                duration=duration,
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
                    return wait_obj.until(expected_conditions.presence_of_element_located((by, value)))
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, wait_obj.until, expected_conditions.presence_of_element_located((by, value)))
            return self.driver.find_element(by, value)

        except Exception as e:
            logger.warning(f"Element not found: {selector}: {e}")
            return None
