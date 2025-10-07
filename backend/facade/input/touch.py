"""Touch gesture controls for mobile emulation."""

import asyncio
import time

from loguru import logger

from browser.backend.facade.base import BaseController
from browser.backend.facade.utils import parameterized_js_execution
from browser.backend.utils.exceptions import InputError


class TouchController(BaseController):
    """Handles touch gestures and mobile interactions."""

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
                viewport = await loop.run_in_executor(
                    None,
                    self.driver.execute_script,
                    "return {width: window.innerWidth, height: window.innerHeight}",
                )
                center_x = center_x or viewport["width"] // 2
                center_y = center_y or viewport["height"] // 2

            # Use CSS transform for zooming
            script = parameterized_js_execution(
                """
                document.body.style.transformOrigin = '{center_x}px {center_y}px';
                document.body.style.transform = 'scale({scale})';
                """,
                center_x=center_x,
                center_y=center_y,
                scale=scale,
            )
            await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
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
                viewport = await loop.run_in_executor(
                    None,
                    self.driver.execute_script,
                    "return {width: window.innerWidth, height: window.innerHeight}",
                )
                center_x = center_x or viewport["width"] // 2
                center_y = center_y or viewport["height"] // 2

            # Simulate pinch zoom using touch events
            script = parameterized_js_execution(
                """
                const centerX = {center_x};
                const centerY = {center_y};
                const scale = {scale};

                // Create touch event
                const createTouch = (x, y, id) => {{
                    return new Touch({{
                        identifier: id,
                        target: document.elementFromPoint(x | y), , document.body,
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
                """,
                center_x=center_x,
                center_y=center_y,
                scale=scale,
            )

            await loop.run_in_executor(None, self.driver.execute_script, script)

            self.instance.update_activity()
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
            script = parameterized_js_execution(
                """
                const startX = {start_x};
                const startY = {start_y};
                const endX = {end_x};
                const endY = {end_y};
                const duration = {duration} * 1000;  // Convert to milliseconds

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
                """,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                duration=duration,
            )

            await loop.run_in_executor(None, self.driver.execute_script, script)
            await asyncio.sleep(duration)  # Wait for swipe to complete

            self.instance.update_activity()
            logger.debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        except Exception as e:
            logger.error(f"Swipe failed: {e}")
            raise InputError(f"Failed to swipe: {e}") from e

    async def tap(self, x: int, y: int) -> None:
        """Perform a tap gesture at coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            script = parameterized_js_execution(
                """
                const x = {x};
                const y = {y};
                const element = document.elementFromPoint(x, y) || document.body;

                const touchStart = new TouchEvent('touchstart', {{
                    touches: [new Touch({{
                        identifier: 1,
                        target: element,
                        clientX: x,
                        clientY: y,
                        pageX: x,
                        pageY: y
                    }})],
                    bubbles: true,
                    cancelable: true
                }});

                const touchEnd = new TouchEvent('touchend', {{
                    touches: [],
                    changedTouches: [new Touch({{
                        identifier: 1,
                        target: element,
                        clientX: x,
                        clientY: y,
                        pageX: x,
                        pageY: y
                    }})],
                    bubbles: true,
                    cancelable: true
                }});

                element.dispatchEvent(touchStart);
                element.dispatchEvent(touchEnd);

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
            logger.debug(f"Tapped at ({x}, {y})")

        except Exception as e:
            logger.error(f"Tap failed: {e}")
            raise InputError(f"Failed to tap at ({x}, {y}): {e}") from e

    async def long_press(self, x: int, y: int, duration: float = 1.0) -> None:
        """Perform a long press gesture.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: How long to hold the press in seconds
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            script = parameterized_js_execution(
                """
                const x = {x};
                const y = {y};
                const duration = {duration} * 1000;
                const element = document.elementFromPoint(x, y) || document.body;

                const touchStart = new TouchEvent('touchstart', {{
                    touches: [new Touch({{
                        identifier: 1,
                        target: element,
                        clientX: x,
                        clientY: y,
                        pageX: x,
                        pageY: y
                    }})],
                    bubbles: true,
                    cancelable: true
                }});

                element.dispatchEvent(touchStart);

                setTimeout(() => {{
                    const touchEnd = new TouchEvent('touchend', {{
                        touches: [],
                        changedTouches: [new Touch({{
                            identifier: 1,
                            target: element,
                            clientX: x,
                            clientY: y,
                            pageX: x,
                            pageY: y
                        }})],
                        bubbles: true,
                        cancelable: true
                    }});
                    element.dispatchEvent(touchEnd);
                }}, duration);

                return true;
                """,
                x=x,
                y=y,
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
            logger.debug(f"Long pressed at ({x}, {y}) for {duration}s")

        except Exception as e:
            logger.error(f"Long press failed: {e}")
            raise InputError(f"Failed to long press at ({x}, {y}): {e}") from e
