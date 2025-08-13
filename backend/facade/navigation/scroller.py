"""Scrolling and viewport control functionality."""

import asyncio
import time

from ...utils.exceptions import NavigationError
from ..base import BaseController
from ..config import FACADE_CONFIG
from ..utils import parameterized_js_execution


class Scroller(BaseController):
    """Handles scrolling and viewport operations."""

    async def scroll_to(self, x: int | None = None, y: int | None = None, element: str | None = None, smooth: bool = True) -> None:
        """Scroll to a position or element.

        Args:
            x: X coordinate to scroll to
            y: Y coordinate to scroll to
            element: CSS selector of element to scroll to
            smooth: If True, use smooth scrolling animation
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            if element:
                script = parameterized_js_execution(
                    """
                const element = document.querySelector({element});
                if (element) {{
                    element.scrollIntoView({{
                        behavior: {behavior},
                        block: 'center'
                    }});
                }}
                """,
                    element=element,
                    behavior="smooth" if smooth else "auto",
                )
            else:
                behavior = "smooth" if smooth else "auto"
                script = f"window.scrollTo({{left: {x or 0}, top: {y or 0}, behavior: '{behavior}'}})"

            if self._is_in_thread_context():
                self.driver.execute_script(script)
                time.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)
                await asyncio.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)

        except Exception as e:
            raise NavigationError(f"Failed to scroll: {e}") from e

    async def scroll_to_top(self, smooth: bool = True) -> None:
        """Scroll to the top of the page."""
        await self.scroll_to(0, 0, smooth=smooth)

    async def scroll_to_bottom(self, smooth: bool = True) -> None:
        """Scroll to the bottom of the page."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = "return document.documentElement.scrollHeight"

        if self._is_in_thread_context():
            height = self.driver.execute_script(script)
            await self.scroll_to(0, height, smooth=smooth)
        else:
            loop = asyncio.get_event_loop()
            height = await loop.run_in_executor(None, self.driver.execute_script, script)
            await self.scroll_to(0, height, smooth=smooth)

    async def scroll_by(self, x: int = 0, y: int = 0, smooth: bool = True) -> None:
        """Scroll by a relative amount.

        Args:
            x: Pixels to scroll horizontally
            y: Pixels to scroll vertically
            smooth: If True, use smooth scrolling
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        behavior = "smooth" if smooth else "auto"
        script = f"window.scrollBy({{left: {x}, top: {y}, behavior: '{behavior}'}})"

        try:
            if self._is_in_thread_context():
                self.driver.execute_script(script)
                time.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.driver.execute_script, script)
                await asyncio.sleep(FACADE_CONFIG.scroll_wait_smooth if smooth else FACADE_CONFIG.scroll_wait_instant)
        except Exception as e:
            raise NavigationError(f"Failed to scroll by offset: {e}") from e

    async def get_scroll_position(self) -> dict[str, int]:
        """Get the current scroll position.

        Returns:
            Dictionary with 'x' and 'y' scroll positions
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = "return {x: window.pageXOffset, y: window.pageYOffset}"

        try:
            if self._is_in_thread_context():
                return self.driver.execute_script(script)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_script, script)
        except Exception as e:
            raise NavigationError(f"Failed to get scroll position: {e}") from e

    async def get_viewport_size(self) -> dict[str, int]:
        """Get the viewport dimensions.

        Returns:
            Dictionary with 'width' and 'height' of viewport
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = "return {width: window.innerWidth, height: window.innerHeight}"

        try:
            if self._is_in_thread_context():
                return self.driver.execute_script(script)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_script, script)
        except Exception as e:
            raise NavigationError(f"Failed to get viewport size: {e}") from e

    async def get_page_dimensions(self) -> dict[str, int]:
        """Get the full page dimensions.

        Returns:
            Dictionary with 'width' and 'height' of the full page
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        script = """
        return {
            width: document.documentElement.scrollWidth,
            height: document.documentElement.scrollHeight
        }
        """

        try:
            if self._is_in_thread_context():
                return self.driver.execute_script(script)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_script, script)
        except Exception as e:
            raise NavigationError(f"Failed to get page dimensions: {e}") from e
