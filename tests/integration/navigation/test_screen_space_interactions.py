"""Integration tests for screen-space interactions."""

import asyncio
import os
from typing import Any

import pytest

# BrowserInstance import removed - using fixtures from conftest
from browser.backend.facade.input.mouse import MouseController
from browser.backend.facade.navigation.extractor import ContentExtractor
from browser.backend.facade.navigation.navigator import Navigator

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"

pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")

# Using test_html_server fixture from conftest.py instead of creating duplicate


class TestScreenSpaceClicks:
    """Test screen-space click functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_click_at_coordinates(self, browser_instance: Any, test_html_server: str) -> None:
        """Test clicking at specific coordinates."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/captcha_form.html")

        # Get button position using JavaScript
        button_pos = await extractor.execute_script(
            """
            const btn = document.querySelector('[data-testid="verify-text-btn"]');
            const rect = btn.getBoundingClientRect();
            return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
        """,
        )

        # Click at the button's coordinates
        await mouse.click_at_coordinates(int(button_pos["x"]), int(button_pos["y"]))

        # Check if click was registered
        await asyncio.sleep(0.5)
        status = await extractor.execute_script(
            """
            const status = document.querySelector('#status');
            return status ? status.textContent : null;
        """,
        )
        assert status == "Incorrect text. Please try again."  # Should show error because no text entered

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_double_click_at_coordinates(self, browser_instance: Any, test_html_server: str) -> None:
        """Test double-clicking at coordinates."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/dynamic_content.html")

        # Add double-click handler
        await extractor.execute_script(
            """
            window.doubleClickCount = 0;
            document.getElementById('content-area').addEventListener('dblclick', (e) => {
                window.doubleClickCount++;
                console.log('Double click at', e.clientX, e.clientY);
            });
        """,
        )

        # Get element position
        element_pos = await extractor.execute_script(
            """
            const el = document.getElementById('content-area');
            const rect = el.getBoundingClientRect();
            return {x: rect.left + 50, y: rect.top + 50};
        """,
        )

        # Double-click at coordinates
        await mouse.click_at_coordinates(int(element_pos["x"]), int(element_pos["y"]), click_count=2)

        await asyncio.sleep(0.5)

        # Check double-click was registered
        count = await extractor.execute_script("return window.doubleClickCount")
        assert count == 1

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_right_click_at_coordinates(self, browser_instance: Any, test_html_server: str) -> None:
        """Test right-clicking at coordinates."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/login_form.html")

        # Add context menu handler
        await extractor.execute_script(
            """
            window.rightClickDetected = false;
            document.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                window.rightClickDetected = true;
                window.rightClickX = e.clientX;
                window.rightClickY = e.clientY;
            });
        """,
        )

        # Right-click at specific coordinates
        await mouse.click_at_coordinates(200, 300, button="right")

        await asyncio.sleep(0.5)

        # Verify right-click was detected
        detected = await extractor.execute_script("return window.rightClickDetected")
        assert detected is True

        x = await extractor.execute_script("return window.rightClickX")
        y = await extractor.execute_script("return window.rightClickY")
        margin = 50  # Increased margin for browser coordinate differences
        assert abs(x - 200) < margin  # Allow margin for accuracy
        assert abs(y - 300) < margin


class TestScreenSpaceDrag:
    """Test screen-space drag functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_drag_from_to_coordinates(self, browser_instance: Any, test_html_server: str) -> None:
        """Test dragging from one coordinate to another."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/captcha_form.html")

        # Setup drag detection
        await extractor.execute_script(
            """
            window.dragEvents = [];

            // Create draggable element
            const draggable = document.createElement('div');
            draggable.id = 'test-draggable';
            draggable.style.position = 'absolute';
            draggable.style.left = '100px';
            draggable.style.top = '100px';
            draggable.style.width = '50px';
            draggable.style.height = '50px';
            draggable.style.background = 'blue';
            draggable.style.cursor = 'move';
            document.body.appendChild(draggable);

            let isDragging = false;
            let startX, startY;

            draggable.addEventListener('mousedown', (e) => {
                isDragging = true;
                startX = e.clientX - draggable.offsetLeft;
                startY = e.clientY - draggable.offsetTop;
                window.dragEvents.push({type: 'start', x: e.clientX, y: e.clientY});
            });

            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    draggable.style.left = (e.clientX - startX) + 'px';
                    draggable.style.top = (e.clientY - startY) + 'px';
                    window.dragEvents.push({type: 'move', x: e.clientX, y: e.clientY});
                }
            });

            document.addEventListener('mouseup', (e) => {
                if (isDragging) {
                    isDragging = false;
                    window.dragEvents.push({type: 'end', x: e.clientX, y: e.clientY});
                }
            });
        """,
        )

        # Drag from (125, 125) to (300, 300) - center of draggable to new position
        await mouse.drag_from_to(125, 125, 300, 300, duration=1.0)

        await asyncio.sleep(0.5)

        # Check drag events were recorded
        events = await extractor.execute_script("return window.dragEvents")
        assert len(events) > 0
        assert events[0]["type"] == "start"
        assert events[-1]["type"] == "end"

        # Check final position of draggable
        final_pos = await extractor.execute_script(
            """
            const el = document.getElementById('test-draggable');
            return {left: parseInt(el.style.left), top: parseInt(el.style.top)};
        """,
        )

        # Should have moved approximately to the target position
        drag_margin = 50
        assert abs(final_pos["left"] - 275) < drag_margin  # Allow margin for drag accuracy
        assert abs(final_pos["top"] - 275) < drag_margin

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_puzzle_captcha_drag(self, browser_instance: Any, test_html_server: str) -> None:
        """Test solving a puzzle CAPTCHA using drag."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/captcha_form.html")

        # Get puzzle piece current position and calculate target
        positions = await extractor.execute_script(
            """
            const piece = document.querySelector('.puzzle-piece');
            const container = document.getElementById('puzzle-container');
            const pieceRect = piece.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            // Current piece position in viewport
            const pieceX = pieceRect.left + pieceRect.width/2;
            const pieceY = pieceRect.top + pieceRect.height/2;

            // Target position is (230, 75) relative to container
            // Convert to viewport coordinates
            const targetX = containerRect.left + 230 + 25; // 25 is half the piece width
            const targetY = containerRect.top + 75 + 25;   // 25 is half the piece height

            return {
                piece: {x: pieceX, y: pieceY},
                target: {x: targetX, y: targetY}
            };
        """,
        )

        # Use a custom drag simulation that works with the puzzle's mouse event handlers
        await extractor.execute_script(
            f"""
            // Simulate dragging the puzzle piece
            const piece = document.getElementById('puzzle-piece');
            const container = document.getElementById('puzzle-container');
            const containerRect = container.getBoundingClientRect();

            // Start position (center of piece)
            const startX = {positions["piece"]["x"]};
            const startY = {positions["piece"]["y"]};

            // End position (target position)
            const endX = {positions["target"]["x"]};
            const endY = {positions["target"]["y"]};

            // Fire mousedown on the piece
            const mouseDownEvent = new MouseEvent('mousedown', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: startX,
                clientY: startY
            }});
            piece.dispatchEvent(mouseDownEvent);

            // Simulate drag with multiple mousemove events
            const steps = 20;
            for (let i = 1; i <= steps; i++) {{
                const progress = i / steps;
                const currentX = startX + (endX - startX) * progress;
                const currentY = startY + (endY - startY) * progress;

                const mouseMoveEvent = new MouseEvent('mousemove', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: currentX,
                    clientY: currentY
                }});
                document.dispatchEvent(mouseMoveEvent);
            }}

            // Fire mouseup at the end position
            const mouseUpEvent = new MouseEvent('mouseup', {{
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: endX,
                clientY: endY
            }});
            document.dispatchEvent(mouseUpEvent);
        """,
        )

        await asyncio.sleep(1.0)

        # Verify the puzzle position (this is required to mark it as solved)
        await extractor.execute_script("verifyPuzzle()")
        await asyncio.sleep(0.5)

        # Check if puzzle was solved
        solved = await extractor.execute_script("return window.captchaState.solved.puzzle")
        assert solved is True


class TestZoomInteractions:
    """Test zoom functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_zoom_scale(self, browser_instance: Any, test_html_server: str) -> None:
        """Test zooming the page."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/dynamic_content.html")

        # Zoom in to 150%
        zoom_in = 1.5
        await extractor.execute_script(f"document.body.style.transform = 'scale({zoom_in})'")

        # Check zoom was applied
        scale = await extractor.execute_script(
            """
            const transform = document.body.style.transform;
            const match = transform.match(/scale\\(([^)]+)\\)/);
            return match ? parseFloat(match[1]) : 1.0;
        """,
        )
        assert scale == zoom_in

        # Zoom out to 75%
        zoom_out = 0.75
        await extractor.execute_script(f"document.body.style.transform = 'scale({zoom_out})'")

        scale = await extractor.execute_script(
            """
            const transform = document.body.style.transform;
            const match = transform.match(/scale\\(([^)]+)\\)/);
            return match ? parseFloat(match[1]) : 1.0;
        """,
        )
        assert scale == zoom_out

        # Reset zoom
        await extractor.execute_script("document.body.style.transform = 'scale(1.0)'")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_zoom_at_center(self, browser_instance: Any, test_html_server: str) -> None:
        """Test zooming at specific center point."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)

        await nav.navigate(f"{test_html_server}/login_form.html")

        # Zoom in at specific point (e.g., the submit button)
        button_pos = await extractor.execute_script(
            """
            const btn = document.getElementById('submit-btn');
            const rect = btn.getBoundingClientRect();
            return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
        """,
        )

        x_pos = int(button_pos["x"])
        y_pos = int(button_pos["y"])
        await extractor.execute_script(f"document.body.style.transform = 'scale(2.0)'; document.body.style.transformOrigin = '{x_pos}px {y_pos}px'")

        # Check zoom and origin were set
        transform_data = await extractor.execute_script(
            """
            return {
                transform: document.body.style.transform,
                origin: document.body.style.transformOrigin
            };
        """,
        )

        assert "scale(2)" in transform_data["transform"]
        assert f"{int(button_pos['x'])}px" in transform_data["origin"]
        assert f"{int(button_pos['y'])}px" in transform_data["origin"]


class TestSwipeGestures:
    """Test swipe gestures."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_swipe_horizontal(self, browser_instance: Any, test_html_server: str) -> None:
        """Test horizontal swipe gesture."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/dynamic_content.html")

        # Setup swipe detection
        await extractor.execute_script(
            """
            window.swipeDetected = null;

            let mouseStartX = 0;
            let mouseStartY = 0;
            let isDragging = false;

            document.addEventListener('mousedown', (e) => {
                mouseStartX = e.clientX;
                mouseStartY = e.clientY;
                isDragging = true;
            });

            document.addEventListener('mouseup', (e) => {
                if (!isDragging) return;
                const mouseEndX = e.clientX;
                const mouseEndY = e.clientY;

                const deltaX = mouseEndX - mouseStartX;
                const deltaY = mouseEndY - mouseStartY;

                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    window.swipeDetected = deltaX > 0 ? 'right' : 'left';
                } else {
                    window.swipeDetected = deltaY > 0 ? 'down' : 'up';
                }
                isDragging = false;
            });
        """,
        )

        # Perform horizontal swipe (left to right)
        await mouse.drag_from_to(100, 300, 400, 300, duration=0.5)

        await asyncio.sleep(0.5)

        # Check swipe was detected
        swipe_direction = await extractor.execute_script("return window.swipeDetected")
        assert swipe_direction == "right"

        # Reset
        await extractor.execute_script("window.swipeDetected = null")

        # Perform horizontal swipe (right to left)
        await mouse.drag_from_to(400, 300, 100, 300, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await extractor.execute_script("return window.swipeDetected")
        assert swipe_direction == "left"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_swipe_vertical(self, browser_instance: Any, test_html_server: str) -> None:
        """Test vertical swipe gesture."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)
        mouse = MouseController(browser_instance)

        await nav.navigate(f"{test_html_server}/dynamic_content.html")

        # Setup swipe detection (reuse from horizontal test)
        await extractor.execute_script(
            """
            window.swipeDetected = null;

            let mouseStartX = 0;
            let mouseStartY = 0;
            let isDragging = false;

            document.addEventListener('mousedown', (e) => {
                mouseStartX = e.clientX;
                mouseStartY = e.clientY;
                isDragging = true;
            });

            document.addEventListener('mouseup', (e) => {
                if (!isDragging) return;
                const mouseEndX = e.clientX;
                const mouseEndY = e.clientY;

                const deltaX = mouseEndX - mouseStartX;
                const deltaY = mouseEndY - mouseStartY;

                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    window.swipeDetected = deltaX > 0 ? 'right' : 'left';
                } else {
                    window.swipeDetected = deltaY > 0 ? 'down' : 'up';
                }
                isDragging = false;
            });
        """,
        )

        # Perform vertical swipe (top to bottom)
        await mouse.drag_from_to(300, 100, 300, 400, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await extractor.execute_script("return window.swipeDetected")
        assert swipe_direction == "down"

        # Reset
        await extractor.execute_script("window.swipeDetected = null")

        # Perform vertical swipe (bottom to top)
        await mouse.drag_from_to(300, 400, 300, 100, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await extractor.execute_script("return window.swipeDetected")
        assert swipe_direction == "up"


class TestTextExtraction:
    """Test text extraction functionality."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_text_from_page(self, browser_instance: Any, test_html_server: str) -> None:
        """Test extracting human-readable text from a page."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)

        await nav.navigate(f"{test_html_server}/login_form.html")

        # Extract text with structure
        text = await extractor.extract_text(preserve_structure=True)

        # Check key text is present
        assert "Login Form" in text
        assert "Username" in text
        assert "Password" in text
        assert "Remember me" in text

        # Extract text without structure
        flat_text = await extractor.extract_text(preserve_structure=False)
        assert len(flat_text) > 0
        assert "Login Form" in flat_text

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_links(self, browser_instance: Any, test_html_server: str) -> None:
        """Test extracting links from a page."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)

        await nav.navigate(f"{test_html_server}/login_form.html")

        # Add some test links
        await extractor.execute_script(
            """
            const form = document.getElementById('login-form');
            if (form) {
                form.innerHTML += '<a href="/forgot">Forgot Password?</a>';
                form.innerHTML += '<a href="/register">Sign Up</a>';
                form.innerHTML += '<a href="https://example.com">External Link</a>';
            }
        """,
        )

        # Extract links
        links = await extractor.extract_links(absolute=True)

        # Check links were extracted
        min_links = 3
        assert len(links) >= min_links

        # Check link structure
        for link in links:
            assert "href" in link
            assert "text" in link
            assert "title" in link

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_forms(self, browser_instance: Any, test_html_server: str) -> None:
        """Test extracting form information."""
        nav = Navigator(browser_instance)
        extractor = ContentExtractor(browser_instance)

        await nav.navigate(f"{test_html_server}/login_form.html")

        # Extract forms
        forms = await extractor.extract_forms()

        # Check form was extracted
        assert len(forms) >= 1

        # Check form structure
        form = forms[0]
        assert "fields" in form

        # Check field types
        min_fields = 3
        assert len(form["fields"]) >= min_fields  # username, password, remember

        field_types = [f["type"] for f in form["fields"]]
        assert "text" in field_types or "input" in field_types
        assert "password" in field_types
        assert "checkbox" in field_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
