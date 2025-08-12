"""Screenshot capture and image manipulation."""

import asyncio
import base64
import io
import time
from pathlib import Path

from loguru import logger
from PIL import Image

from ...models.media import ImageFormat
from ...utils.exceptions import MediaError
from ..base import BaseController
from ..config import FACADE_CONFIG


class ScreenshotController(BaseController):
    """Controller for screenshot and image capture operations."""

    async def capture_viewport(self, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
        """Capture a screenshot of the current viewport.

        Args:
            image_format: Image format (PNG, JPEG, WEBP)
            quality: Image quality (1-100, for JPEG/WEBP)

        Returns:
            Screenshot as bytes
        """
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                screenshot_base64 = self.driver.get_screenshot_as_base64()
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                screenshot_base64 = await loop.run_in_executor(None, self.driver.get_screenshot_as_base64)

            screenshot_bytes = base64.b64decode(screenshot_base64)

            # Convert format if needed
            if image_format != ImageFormat.PNG:
                screenshot_bytes = self._convert_image_format(screenshot_bytes, image_format, quality)

            self.instance.update_activity()
            return screenshot_bytes

        except Exception as e:
            raise MediaError(f"Failed to capture viewport: {e}") from e

    async def capture_element(self, selector: str, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
        """Capture a screenshot of a specific element.

        Args:
            selector: CSS selector for the element
            image_format: Image format (PNG, JPEG, WEBP)
            quality: Image quality (1-100, for JPEG/WEBP)

        Returns:
            Screenshot as bytes
        """
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            by, value = self._parse_selector(selector)
            element = self.driver.find_element(by, value)

            if not element:
                raise MediaError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                # Synchronous operation in thread context
                screenshot_base64 = element.screenshot_as_base64
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                screenshot_base64 = await loop.run_in_executor(None, lambda: element.screenshot_as_base64)

            screenshot_bytes = base64.b64decode(screenshot_base64)

            # Convert format if needed
            if image_format != ImageFormat.PNG:
                screenshot_bytes = self._convert_image_format(screenshot_bytes, image_format, quality)

            self.instance.update_activity()
            return screenshot_bytes

        except Exception as e:
            raise MediaError(f"Failed to capture element {selector}: {e}") from e

    async def capture_full_page(self, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
        """Capture a screenshot of the entire page by scrolling and stitching.

        Args:
            image_format: Image format (PNG, JPEG, WEBP)
            quality: Image quality (1-100, for JPEG/WEBP)

        Returns:
            Full page screenshot as bytes
        """
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                return self._capture_full_page_sync(image_format, quality)
            return await self._capture_full_page_async(image_format, quality)

        except Exception as e:
            raise MediaError(f"Failed to capture full page: {e}") from e

    def _capture_full_page_sync(self, image_format: ImageFormat, quality: int) -> bytes:
        """Synchronous version of full page capture."""
        # Get page dimensions
        total_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        total_width = self.driver.execute_script("return document.documentElement.scrollWidth")

        # Scroll to top
        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(FACADE_CONFIG.screenshot_stitch_delay)

        # Take screenshots while scrolling
        screenshots = []
        current_position = 0

        while current_position < total_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position})")
            time.sleep(FACADE_CONFIG.screenshot_stitch_delay)
            screenshot_base64 = self.driver.get_screenshot_as_base64()
            screenshots.append(base64.b64decode(screenshot_base64))
            current_position += viewport_height

        # Restore original position
        self.driver.execute_script("window.scrollTo(0, 0)")

        # Stitch screenshots together
        stitched_image = self._stitch_screenshots(screenshots, total_width, total_height, viewport_height)

        # Convert to bytes
        output = io.BytesIO()
        if image_format == ImageFormat.JPEG:
            stitched_image.save(output, format="JPEG", quality=quality)
        elif image_format == ImageFormat.WEBP:
            stitched_image.save(output, format="WEBP", quality=quality)
        else:
            stitched_image.save(output, format="PNG")

        self.instance.update_activity()
        return output.getvalue()

    async def _capture_full_page_async(self, image_format: ImageFormat, quality: int) -> bytes:
        """Asynchronous version of full page capture."""
        loop = asyncio.get_event_loop()

        # Get page dimensions
        total_height = await loop.run_in_executor(None, self.driver.execute_script, "return document.documentElement.scrollHeight")
        viewport_height = await loop.run_in_executor(None, self.driver.execute_script, "return window.innerHeight")
        total_width = await loop.run_in_executor(None, self.driver.execute_script, "return document.documentElement.scrollWidth")

        # Scroll to top
        await loop.run_in_executor(None, self.driver.execute_script, "window.scrollTo(0, 0)")
        await asyncio.sleep(FACADE_CONFIG.screenshot_stitch_delay)

        # Take screenshots while scrolling
        screenshots = []
        current_position = 0

        while current_position < total_height:
            await loop.run_in_executor(None, self.driver.execute_script, f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(FACADE_CONFIG.screenshot_stitch_delay)
            screenshot_base64 = await loop.run_in_executor(None, self.driver.get_screenshot_as_base64)
            screenshots.append(base64.b64decode(screenshot_base64))
            current_position += viewport_height

        # Restore original position
        await loop.run_in_executor(None, self.driver.execute_script, "window.scrollTo(0, 0)")

        # Stitch screenshots together
        stitched_image = self._stitch_screenshots(screenshots, total_width, total_height, viewport_height)

        # Convert to bytes
        output = io.BytesIO()
        if image_format == ImageFormat.JPEG:
            stitched_image.save(output, format="JPEG", quality=quality)
        elif image_format == ImageFormat.WEBP:
            stitched_image.save(output, format="WEBP", quality=quality)
        else:
            stitched_image.save(output, format="PNG")

        self.instance.update_activity()
        return output.getvalue()

    def _stitch_screenshots(self, screenshots: list[bytes], width: int, height: int, viewport_height: int) -> Image.Image:
        """Stitch multiple screenshots into one image.

        Args:
            screenshots: List of screenshot bytes
            width: Total width of the page
            height: Total height of the page
            viewport_height: Height of the viewport

        Returns:
            Stitched PIL Image
        """
        # Create blank image
        stitched = Image.new("RGB", (width, height))

        # Paste screenshots
        y_offset = 0
        for _i, screenshot_bytes in enumerate(screenshots):
            img = Image.open(io.BytesIO(screenshot_bytes))

            # Calculate paste height (last screenshot might be partial)
            paste_height = min(viewport_height, height - y_offset)

            # Crop if needed
            if img.height > paste_height:
                img = img.crop((0, 0, img.width, paste_height))  # type: ignore[assignment]

            stitched.paste(img, (0, y_offset))
            y_offset += paste_height

        return stitched

    def _convert_image_format(self, image_bytes: bytes, format_type: ImageFormat, quality: int) -> bytes:
        """Convert image to different format.

        Args:
            image_bytes: Original image bytes
            format_type: Target format
            quality: Image quality (1-100)

        Returns:
            Converted image bytes
        """
        img = Image.open(io.BytesIO(image_bytes))
        output = io.BytesIO()

        if format_type == ImageFormat.JPEG:
            # Convert RGBA to RGB for JPEG
            if img.mode == "RGBA":
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img  # type: ignore[assignment]
            img.save(output, format="JPEG", quality=quality)
        elif format_type == ImageFormat.WEBP:
            img.save(output, format="WEBP", quality=quality)
        else:
            img.save(output, format="PNG")

        return output.getvalue()

    async def save_screenshot(self, filepath: str, selector: str | None = None, full_page: bool = False) -> str:
        """Save a screenshot to file.

        Args:
            filepath: Path to save the screenshot
            selector: Optional CSS selector for element screenshot
            full_page: If True, capture full page

        Returns:
            Path to saved file
        """
        # Determine format from extension
        ext = filepath.lower().split(".")[-1]
        if ext in {"jpg", "jpeg"}:
            format_type = ImageFormat.JPEG
        elif ext == "webp":
            format_type = ImageFormat.WEBP
        else:
            format_type = ImageFormat.PNG

        # Capture screenshot
        if selector:
            screenshot = await self.capture_element(selector, format_type)
        elif full_page:
            screenshot = await self.capture_full_page(format_type)
        else:
            screenshot = await self.capture_viewport(format_type)

        # Save to file
        path = Path(filepath)
        with path.open("wb") as f:
            f.write(screenshot)

        logger.info(f"Screenshot saved to {filepath}")
        return filepath
