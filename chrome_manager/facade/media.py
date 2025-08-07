import asyncio
import base64
import contextlib
import io
import threading
import time
import uuid
from datetime import datetime

import cv2
import numpy as np
from loguru import logger
from PIL import Image
from selenium.webdriver.common.by import By

from ..core.instance import BrowserInstance
from ..models.media import ImageFormat, RecordingSession
from ..utils.exceptions import MediaError


class ScreenshotController:
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

    async def capture_viewport(self, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            if self._is_in_thread_context():
                # Synchronous operation in thread context
                screenshot_base64 = self.driver.get_screenshot_as_base64()
                screenshot_bytes = base64.b64decode(screenshot_base64)

                if image_format != ImageFormat.PNG:
                    # Convert synchronously
                    screenshot_bytes = self._convert_image_sync(screenshot_bytes, image_format, quality)
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                screenshot_base64 = await loop.run_in_executor(None, self.driver.get_screenshot_as_base64)

                screenshot_bytes = base64.b64decode(screenshot_base64)

                if image_format != ImageFormat.PNG:
                    screenshot_bytes = await self._convert_image(screenshot_bytes, image_format, quality)

            logger.debug("Captured viewport screenshot")
            return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to capture viewport: {e}")
            raise MediaError(f"Failed to capture viewport: {e}") from e

    async def capture_element(self, selector: str, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
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
                screenshot_bytes = base64.b64decode(screenshot_base64)

                if image_format != ImageFormat.PNG:
                    screenshot_bytes = self._convert_image_sync(screenshot_bytes, image_format, quality)
            else:
                # Normal async operation
                loop = asyncio.get_event_loop()
                screenshot_base64: str = await loop.run_in_executor(None, lambda: element.screenshot_as_base64)

                screenshot_bytes = base64.b64decode(screenshot_base64)

                if image_format != ImageFormat.PNG:
                    screenshot_bytes = await self._convert_image(screenshot_bytes, image_format, quality)

            logger.debug(f"Captured element screenshot: {selector}")
            return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to capture element {selector}: {e}")
            raise MediaError(f"Failed to capture element: {e}") from e

    async def capture_full_page(self, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100, stitch: bool = True) -> bytes:  # noqa: ARG002
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            if stitch:
                return await self._capture_full_page_stitched(image_format, quality)
            return await self._capture_full_page_cdp(image_format, quality)

        except Exception as e:
            logger.error(f"Failed to capture full page: {e}")
            raise MediaError(f"Failed to capture full page: {e}") from e

    async def _capture_full_page_stitched(self, image_format: ImageFormat, quality: int) -> bytes:  # noqa: ARG002
        if self._is_in_thread_context():
            # Synchronous version for thread context
            import time

            original_position = self.driver.execute_script("return [window.pageXOffset, window.pageYOffset];")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            viewport_width = self.driver.execute_script("return window.innerWidth")
            total_height = self.driver.execute_script("return document.documentElement.scrollHeight")

            screenshots = []
            current_position = 0

            while current_position < total_height:
                self.driver.execute_script(f"window.scrollTo(0, {current_position})")
                time.sleep(0.2)
                screenshot_base64 = self.driver.get_screenshot_as_base64()
                screenshots.append(base64.b64decode(screenshot_base64))
                current_position += viewport_height

            self.driver.execute_script(f"window.scrollTo({original_position[0]}, {original_position[1]})")
        else:
            # Normal async version
            loop = asyncio.get_event_loop()

            original_position = await loop.run_in_executor(None, self.driver.execute_script, "return [window.pageXOffset, window.pageYOffset];")

            viewport_height = await loop.run_in_executor(None, self.driver.execute_script, "return window.innerHeight")

            viewport_width = await loop.run_in_executor(None, self.driver.execute_script, "return window.innerWidth")

            total_height = await loop.run_in_executor(None, self.driver.execute_script, "return document.documentElement.scrollHeight")

            screenshots = []
            current_position = 0

            while current_position < total_height:
                await loop.run_in_executor(None, self.driver.execute_script, f"window.scrollTo(0, {current_position})")

                await asyncio.sleep(0.2)

                screenshot_base64 = await loop.run_in_executor(None, self.driver.get_screenshot_as_base64)
                screenshots.append(base64.b64decode(screenshot_base64))

                current_position += viewport_height

            await loop.run_in_executor(None, self.driver.execute_script, f"window.scrollTo({original_position[0]}, {original_position[1]})")

        stitched_image = Image.new("RGB", (viewport_width, total_height))
        y_offset = 0

        for screenshot_bytes in screenshots:
            img = Image.open(io.BytesIO(screenshot_bytes))
            stitched_image.paste(img, (0, y_offset))
            y_offset += img.height

        output = io.BytesIO()
        if image_format == ImageFormat.JPEG:
            stitched_image.save(output, format="JPEG", quality=quality)
        elif image_format == ImageFormat.WEBP:
            stitched_image.save(output, format="WEBP", quality=quality)
        else:
            stitched_image.save(output, format="PNG")

        return output.getvalue()

    async def _capture_full_page_cdp(self, image_format: ImageFormat, quality: int) -> bytes:  # noqa: ARG002
        try:
            if self._is_in_thread_context():
                # Synchronous version for thread context
                metrics = self.driver.execute_cdp_cmd("Page.getLayoutMetrics", {})  # type: ignore[attr-defined]
                width = metrics["contentSize"]["width"]
                height = metrics["contentSize"]["height"]

                self.driver.execute_cdp_cmd(  # type: ignore[attr-defined]
                    "Emulation.setDeviceMetricsOverride",
                    {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
                )

                screenshot = self.driver.execute_cdp_cmd(  # type: ignore[attr-defined]
                    "Page.captureScreenshot",
                    {
                        "format": "png" if image_format == ImageFormat.PNG else "jpeg",
                        "quality": quality if image_format != ImageFormat.PNG else None,
                        "captureBeyondViewport": True,
                    },
                )

                self.driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})  # type: ignore[attr-defined]
                return base64.b64decode(screenshot["data"])
            # Normal async version
            loop = asyncio.get_event_loop()

            metrics = await loop.run_in_executor(None, self.driver.execute_cdp_cmd, "Page.getLayoutMetrics", {})  # type: ignore[attr-defined]

            width = metrics["contentSize"]["width"]
            height = metrics["contentSize"]["height"]

            await loop.run_in_executor(
                None,
                self.driver.execute_cdp_cmd,  # type: ignore[attr-defined]
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
            )

            screenshot = await loop.run_in_executor(
                None,
                self.driver.execute_cdp_cmd,  # type: ignore[attr-defined]
                "Page.captureScreenshot",
                {
                    "format": "png" if image_format == ImageFormat.PNG else "jpeg",
                    "quality": quality if image_format != ImageFormat.PNG else None,
                    "captureBeyondViewport": True,
                },
            )

            await loop.run_in_executor(None, self.driver.execute_cdp_cmd, "Emulation.clearDeviceMetricsOverride", {})  # type: ignore[attr-defined]

            return base64.b64decode(screenshot["data"])

        except Exception as e:
            logger.warning(f"CDP screenshot failed, falling back to stitching: {e}")
            return await self._capture_full_page_stitched(image_format, quality)

    async def capture_region(self, x: int, y: int, width: int, height: int, image_format: ImageFormat = ImageFormat.PNG, quality: int = 100) -> bytes:  # noqa: ARG002
        if not self.driver:
            raise MediaError("Browser not initialized")

        try:
            full_screenshot = await self.capture_viewport()

            img = Image.open(io.BytesIO(full_screenshot))
            cropped = img.crop((x, y, x + width, y + height))

            output = io.BytesIO()
            if image_format == ImageFormat.JPEG:
                cropped.save(output, format="JPEG", quality=quality)
            elif image_format == ImageFormat.WEBP:
                cropped.save(output, format="WEBP", quality=quality)
            else:
                cropped.save(output, format="PNG")

            logger.debug(f"Captured region: x={x}, y={y}, w={width}, h={height}")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to capture region: {e}")
            raise MediaError(f"Failed to capture region: {e}") from e

    def _convert_image_sync(self, image_bytes: bytes, image_format: ImageFormat, quality: int) -> bytes:  # noqa: ARG002
        """Synchronous version of image conversion for thread context."""
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode == "RGBA" and image_format == ImageFormat.JPEG:
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background  # type: ignore[assignment]

        output = io.BytesIO()
        if image_format == ImageFormat.JPEG:
            img.save(output, format="JPEG", quality=quality)
        elif image_format == ImageFormat.WEBP:
            img.save(output, format="WEBP", quality=quality)
        else:
            img.save(output, format="PNG")

        return output.getvalue()

    async def _convert_image(self, image_bytes: bytes, image_format: ImageFormat, quality: int) -> bytes:  # noqa: ARG002
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode == "RGBA" and image_format == ImageFormat.JPEG:
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background  # type: ignore[assignment]

        output = io.BytesIO()
        if image_format == ImageFormat.JPEG:
            img.save(output, format="JPEG", quality=quality)
        elif image_format == ImageFormat.WEBP:
            img.save(output, format="WEBP", quality=quality)
        else:
            img.save(output, format="PNG")

        return output.getvalue()

    def _parse_selector(self, selector: str) -> tuple:
        if selector.startswith("//"):
            return (By.XPATH, selector)
        if selector.startswith("#"):
            return (By.ID, selector[1:])
        if selector.startswith("."):
            return (By.CLASS_NAME, selector[1:])
        return (By.CSS_SELECTOR, selector)


class VideoRecorder:
    def __init__(self, instance: BrowserInstance):
        self.instance = instance
        self.driver = instance.driver
        self.recording_sessions: dict[str, dict] = {}

    async def start_recording(self, output_path: str, fps: int = 30, codec: str = "h264") -> RecordingSession:
        session_id = str(uuid.uuid4())

        session = RecordingSession(
            session_id=session_id, output_path=output_path, started_at=datetime.now().isoformat(), status="recording", duration=0.0, frame_count=0
        )

        self.recording_sessions[session_id] = {
            "session": session,
            "writer": None,
            "task": asyncio.create_task(self._record_loop(session_id, output_path, fps, codec)),
        }

        logger.info(f"Started recording session {session_id}")
        return session

    async def stop_recording(self, session_id: str) -> RecordingSession:
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        recording = self.recording_sessions[session_id]
        recording["session"].status = "stopped"

        if recording["task"]:
            recording["task"].cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recording["task"]

        if recording["writer"]:
            recording["writer"].release()

        session = recording["session"]
        del self.recording_sessions[session_id]

        logger.info(f"Stopped recording session {session_id}")
        return session

    async def pause_recording(self, session_id: str) -> None:
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        self.recording_sessions[session_id]["session"].status = "paused"
        logger.info(f"Paused recording session {session_id}")

    async def resume_recording(self, session_id: str) -> None:
        if session_id not in self.recording_sessions:
            raise MediaError(f"Recording session {session_id} not found")

        self.recording_sessions[session_id]["session"].status = "recording"
        logger.info(f"Resumed recording session {session_id}")

    async def _record_loop(self, session_id: str, output_path: str, fps: int, codec: str) -> None:  # noqa: ARG002
        recording = self.recording_sessions[session_id]
        frame_interval = 1.0 / fps

        viewport_size = self.driver.get_window_size()
        width = viewport_size["width"]
        height = viewport_size["height"]

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        recording["writer"] = writer

        start_time = time.time()

        try:
            while recording["session"].status != "stopped":
                if recording["session"].status == "recording":
                    screenshot_base64 = self.driver.get_screenshot_as_base64()
                    screenshot_bytes = base64.b64decode(screenshot_base64)

                    img = Image.open(io.BytesIO(screenshot_bytes))
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                    writer.write(frame)
                    recording["session"].frame_count += 1
                    recording["session"].duration = time.time() - start_time

                await asyncio.sleep(frame_interval)

        except asyncio.CancelledError:
            pass
        finally:
            writer.release()
