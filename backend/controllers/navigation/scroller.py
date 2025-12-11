"""Scrolling and viewport control functionality."""

import asyncio

from browser.backend.controllers.base import BaseController
from browser.backend.controllers.controller_config import CONTROLLER_CONFIG
from browser.backend.controllers.utils import parameterized_js_execution
from browser.backend.utils.exceptions import NavigationError


class Scroller(BaseController):
    """Handles scrolling and viewport operations."""

    async def scroll_to(
        self,
        x: int | None = None,
        y: int | None = None,
        element: str | None = None,
        smooth: bool = True,
    ) -> None:
        """Scroll to a position or element.

        Args:
            x: X coordinate to scroll to
            y: Y coordinate to scroll to
            element: CSS selector of element to scroll to
            smooth: If True, use smooth scrolling animation
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

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

            await self._execute_in_context(lambda: driver.execute_script(script), lambda: driver.execute_script(script))
            await self._sleep_in_context(CONTROLLER_CONFIG.scroll_wait_smooth if smooth else CONTROLLER_CONFIG.scroll_wait_instant)

        except Exception as e:
            raise NavigationError(f"Failed to scroll: {e}") from e

    async def scroll_to_top(self, smooth: bool = True) -> None:
        """Scroll to the top of the page."""
        await self.scroll_to(0, 0, smooth=smooth)

    async def scroll_to_bottom(self, smooth: bool = True) -> None:
        """Scroll to the bottom of the page."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

        script = "return document.documentElement.scrollHeight"

        if self._is_in_thread_context():
            height = driver.execute_script(script)
            await self.scroll_to(0, height, smooth=smooth)
        else:
            loop = asyncio.get_event_loop()
            height = await loop.run_in_executor(None, driver.execute_script, script)
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

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

        behavior = "smooth" if smooth else "auto"
        script = f"window.scrollBy({{left: {x}, top: {y}, behavior: '{behavior}'}})"

        try:
            await self._execute_in_context(lambda: driver.execute_script(script), lambda: driver.execute_script(script))
            await self._sleep_in_context(CONTROLLER_CONFIG.scroll_wait_smooth if smooth else CONTROLLER_CONFIG.scroll_wait_instant)
        except Exception as e:
            raise NavigationError(f"Failed to scroll by offset: {e}") from e

    async def get_scroll_position(self) -> dict[str, int]:
        """Get the current scroll position.

        Returns:
            Dictionary with 'x' and 'y' scroll positions
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

        script = "return {x: window.pageXOffset, y: window.pageYOffset}"

        try:
            raw_result = await self._execute_in_context(lambda: driver.execute_script(script), lambda: driver.execute_script(script))
            result: dict[str, int] = raw_result
            return result
        except Exception as e:
            raise NavigationError(f"Failed to get scroll position: {e}") from e

    async def get_viewport_size(self) -> dict[str, int]:
        """Get the viewport dimensions.

        Returns:
            Dictionary with 'width' and 'height' of viewport
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

        script = "return {width: window.innerWidth, height: window.innerHeight}"

        try:
            raw_result = await self._execute_in_context(lambda: driver.execute_script(script), lambda: driver.execute_script(script))
            result: dict[str, int] = raw_result
            return result
        except Exception as e:
            raise NavigationError(f"Failed to get viewport size: {e}") from e

    async def get_page_dimensions(self) -> dict[str, int]:
        """Get the full page dimensions.

        Returns:
            Dictionary with 'width' and 'height' of the full page
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Create local reference to help mypy understand that driver is not None
        driver = self.driver

        script = """
        return {
            width: document.documentElement.scrollWidth,
            height: document.documentElement.scrollHeight
        }
        """

        try:
            if self._is_in_thread_context():
                raw_result = driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                raw_result = await loop.run_in_executor(None, driver.execute_script, script)
            result: dict[str, int] = raw_result
            return result
        except Exception as e:
            raise NavigationError(f"Failed to get page dimensions: {e}") from e
