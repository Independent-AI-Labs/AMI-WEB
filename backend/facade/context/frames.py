"""Frame and iframe management."""

import asyncio
from typing import Any

from browser.backend.facade.base import BaseController
from browser.backend.utils.exceptions import NavigationError
from loguru import logger
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class FrameController(BaseController):
    """Controller for frame and iframe management."""

    async def switch_frame(self, frame: int | str | WebElement) -> None:
        """Switch to a frame or iframe.

        Args:
            frame: Frame identifier - can be:
                - int: Frame index (0-based)
                - str: Frame name, ID, or CSS selector
                - WebElement: Frame element
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()

            # Validate and process frame identifier
            if isinstance(frame, str):
                frame = self._validate_frame_identifier(frame)
            elif isinstance(frame, int):
                if frame < 0:
                    raise ValueError(f"Frame index cannot be negative: {frame}")
                # Validate index is within range
                frames = await self.count_frames()
                if frame >= frames:
                    raise NavigationError(f"Frame index {frame} out of range (0-{frames - 1})")

            await loop.run_in_executor(None, self.driver.switch_to.frame, frame)

            self.instance.update_activity()
            logger.debug(f"Switched to frame: {frame}")

        except Exception as e:
            logger.error(f"Failed to switch frame: {e}")
            raise NavigationError(f"Failed to switch to frame: {e}") from e

    def _validate_frame_identifier(self, frame: str) -> int | WebElement:
        """Validate and process frame identifier string.

        Args:
            frame: Frame identifier string

        Returns:
            Processed frame identifier
        """
        if not frame:
            raise ValueError("Frame identifier cannot be empty")

        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Check if it's a numeric string (frame index)
        if frame.isdigit():
            return self._validate_frame_index(int(frame))

        # Try to find frame by name or ID, then CSS selector
        element = self._find_frame_element(frame)
        if element:
            return element

        raise NavigationError(f"Frame not found: {frame}")

    def _validate_frame_index(self, index: int) -> int:
        """Validate frame index value.

        Args:
            index: Frame index to validate

        Returns:
            Validated index

        Raises:
            ValueError: If index is negative
        """
        if index < 0:
            raise ValueError(f"Frame index cannot be negative: {index}")
        return index

    def _find_frame_element(self, frame: str) -> WebElement | None:
        """Find frame element by ID, name, or CSS selector.

        Args:
            frame: Frame identifier string

        Returns:
            WebElement if found, None otherwise
        """
        # Try by ID first
        element = self._find_frame_by_locator(By.ID, frame)
        if element:
            return element

        # Try by name
        element = self._find_frame_by_locator(By.NAME, frame)
        if element:
            return element

        # Finally try as CSS selector
        return self._find_frame_by_css_selector(frame)

    def _find_frame_by_locator(self, by: str, value: str) -> WebElement | None:
        """Find frame element using specific locator strategy.

        Args:
            by: Locator strategy (By.ID, By.NAME, etc.)
            value: Locator value

        Returns:
            WebElement if found and is frame, None otherwise
        """
        if not self.driver:
            return None
        try:
            element = self.driver.find_element(by, value)
            if element.tag_name.lower() in ["iframe", "frame"]:
                return element
            return None
        except NoSuchElementException:
            logger.debug(f"Frame not found by {by}: {value}")
            return None

    def _find_frame_by_css_selector(self, selector: str) -> WebElement | None:
        """Find frame element using CSS selector.

        Args:
            selector: CSS selector

        Returns:
            WebElement if found and is frame

        Raises:
            NavigationError: If element found but not a frame
        """
        if not self.driver:
            return None
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            if element.tag_name.lower() not in ["iframe", "frame"]:
                raise NavigationError(f"Element '{selector}' is not a frame or iframe")
            return element
        except NoSuchElementException:
            return None

    async def switch_to_default_content(self) -> None:
        """Switch back to the main document from any frame."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.default_content)

            self.instance.update_activity()
            logger.debug("Switched to default content")

        except Exception as e:
            logger.error(f"Failed to switch to default content: {e}")
            raise NavigationError(f"Failed to switch to default content: {e}") from e

    async def switch_to_parent_frame(self) -> None:
        """Switch to the parent frame of the current frame."""
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.driver.switch_to.parent_frame)

            self.instance.update_activity()
            logger.debug("Switched to parent frame")

        except Exception as e:
            logger.error(f"Failed to switch to parent frame: {e}")
            raise NavigationError(f"Failed to switch to parent frame: {e}") from e

    async def count_frames(self) -> int:
        """Count the number of frames in the current context.

        Returns:
            Number of frames
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = "return window.frames.length;"

            if self._is_in_thread_context():
                count = self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                count = await loop.run_in_executor(None, self.driver.execute_script, script)

            return int(count)

        except Exception as e:
            logger.error(f"Failed to count frames: {e}")
            return 0

    async def list_frames(self) -> list[dict[str, Any]]:
        """Get list of all frames in current context.

        Returns:
            List of frame information dictionaries
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = """
            const frames = [];
            for (let i = 0; i < window.frames.length; i++) {
                try {
                    const frame = window.frames[i];
                    frames.push({
                        index: i,
                        name: frame.name | , '',
                        src: frame.location.href | , 'about:blank',
                        id: frame.frameElement ? frame.frameElement.id : ''
                    });
                } catch (e) {
                    // Cross-origin frame, limited info
                    frames.push({
                        index: i,
                        name: '',
                        src: 'cross-origin',
                        id: ''
                    });
                }
            }
            return frames;
            """

            if self._is_in_thread_context():
                frames = self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                frames = await loop.run_in_executor(None, self.driver.execute_script, script)

            return frames or []

        except Exception as e:
            logger.error(f"Failed to list frames: {e}")
            return []

    async def is_in_frame(self) -> bool:
        """Check if currently in a frame context.

        Returns:
            True if in frame, False if in main document
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        try:
            script = "return window !== window.top;"

            if self._is_in_thread_context():
                result = self.driver.execute_script(script)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.driver.execute_script, script)

            return bool(result)

        except Exception as e:
            logger.error(f"Failed to check frame context: {e}")
            return False

    async def execute_in_frame(self, frame: int | str | WebElement, script: str, *args: Any) -> Any:
        """Execute script in a specific frame and return to current context.

        Args:
            frame: Frame identifier
            script: JavaScript to execute
            *args: Script arguments

        Returns:
            Script execution result
        """
        if not self.driver:
            raise NavigationError("Browser not initialized")

        # Remember if we're in a frame
        was_in_frame = await self.is_in_frame()

        try:
            # Switch to target frame
            await self.switch_frame(frame)

            # Execute script
            if self._is_in_thread_context():
                result = self.driver.execute_script(script, *args)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.driver.execute_script, script, *args)

            return result

        finally:
            # Return to original context
            if not was_in_frame:
                await self.switch_to_default_content()
            # If we were in a frame, we can't easily return to it
            # This is a limitation of the WebDriver API
