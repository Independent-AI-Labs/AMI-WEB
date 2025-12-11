"""Coordinate-based mouse operations."""

import asyncio

from loguru import logger

from browser.backend.controllers.base import BaseController
from browser.backend.controllers.utils import parameterized_js_execution
from browser.backend.utils.exceptions import InputError


class CoordinateController(BaseController):
    """Handles coordinate-based mouse operations."""

    async def click_at_coordinates(self, x: int, y: int) -> None:
        """Click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            # Use JavaScript to simulate click at coordinates
            script = parameterized_js_execution(
                """
            var element = document.elementFromPoint({x}, {y}) || document.body;
            var clickEvent = new MouseEvent('click', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: {x},
                clientY: {y},
                button: 0,
                buttons: 0
            }});
            element.dispatchEvent(clickEvent);
            return true;
            """,
                x=x,
                y=y,
            )

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Clicked at coordinates ({x}, {y})")

        except Exception as e:
            logger.error(f"Click at coordinates failed: {e}")
            raise InputError(f"Failed to click at coordinates ({x}, {y}): {e}") from e

    async def move_to_coordinates(self, x: int, y: int) -> None:
        """Move mouse to specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            # Use JavaScript to simulate mousemove to coordinates
            script = parameterized_js_execution(
                """
            var element = document.elementFromPoint({x}, {y}) || document.body;
            var mouseMoveEvent = new MouseEvent('mousemove', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: {x},
                clientY: {y},
                button: 0,
                buttons: 0
            }});
            element.dispatchEvent(mouseMoveEvent);
            return true;
            """,
                x=x,
                y=y,
            )

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Moved mouse to coordinates ({x}, {y})")

        except Exception as e:
            logger.error(f"Move to coordinates failed: {e}")
            raise InputError(f"Failed to move mouse to coordinates ({x}, {y}): {e}") from e

    async def right_click_at_coordinates(self, x: int, y: int) -> None:
        """Right click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            # Use JavaScript to simulate right click at coordinates
            script = parameterized_js_execution(
                """
            var element = document.elementFromPoint({x}, {y}) || document.body;
            var contextMenuEvent = new MouseEvent('contextmenu', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: {x},
                clientY: {y},
                button: 2,
                buttons: 2
            }});
            element.dispatchEvent(contextMenuEvent);
            return true;
            """,
                x=x,
                y=y,
            )

            if self._is_in_thread_context():
                self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
            logger.debug(f"Right clicked at coordinates ({x}, {y})")

        except Exception as e:
            logger.error(f"Right click at coordinates failed: {e}")
            raise InputError(f"Failed to right click at coordinates ({x}, {y}): {e}") from e
