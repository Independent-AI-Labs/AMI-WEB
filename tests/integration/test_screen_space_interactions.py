"""Integration tests for screen-space interactions."""

import asyncio
import os

import pytest
import pytest_asyncio

# Test configuration
HEADLESS = os.environ.get('TEST_HEADLESS', 'false').lower() == 'true'

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.facade.input import InputController
from chrome_manager.facade.navigation import NavigationController
from tests.fixtures.threaded_server import ThreadedHTMLServer


@pytest_asyncio.fixture
def test_server():
    """Start test HTTP server for the test."""
    import random
    # Use random port to avoid conflicts
    port = random.randint(9000, 9999)
    server = ThreadedHTMLServer(port=port)
    base_url = server.start()  # Synchronous start for threaded server
    yield base_url
    server.stop()  # Synchronous stop


@pytest_asyncio.fixture
async def browser_instance():
    """Create a browser instance for testing."""
    instance = BrowserInstance()
    try:
        await instance.launch(headless=HEADLESS)
        yield instance
    finally:
        await instance.terminate(force=True)


class TestScreenSpaceClicks:
    """Test screen-space click functionality."""

    @pytest.mark.asyncio
    async def test_click_at_coordinates(self, browser_instance, test_server):
        """Test clicking at specific coordinates."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Get button position using JavaScript
        button_pos = await nav.execute_script(
            """
            const btn = document.querySelector('[data-testid="verify-text-btn"]');
            const rect = btn.getBoundingClientRect();
            return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
        """
        )

        # Click at the button's coordinates
        await input_ctrl.click_at_coordinates(int(button_pos["x"]), int(button_pos["y"]))

        # Check if click was registered
        await asyncio.sleep(0.5)
        status = await nav.execute_script(
            """
            const status = document.querySelector('#status');
            return status ? status.textContent : null;
        """
        )
        assert status == 'Incorrect text. Please try again.'  # Should show error because no text entered

    @pytest.mark.asyncio
    async def test_double_click_at_coordinates(self, browser_instance, test_server):
        """Test double-clicking at coordinates."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Add double-click handler
        await nav.execute_script(
            """
            window.doubleClickCount = 0;
            document.getElementById('content-area').addEventListener('dblclick', (e) => {
                window.doubleClickCount++;
                console.log('Double click at', e.clientX, e.clientY);
            });
        """
        )

        # Get element position
        element_pos = await nav.execute_script(
            """
            const el = document.getElementById('content-area');
            const rect = el.getBoundingClientRect();
            return {x: rect.left + 50, y: rect.top + 50};
        """
        )

        # Double-click at coordinates
        await input_ctrl.click_at_coordinates(int(element_pos["x"]), int(element_pos["y"]), click_count=2)

        await asyncio.sleep(0.5)

        # Check double-click was registered
        count = await nav.execute_script("return window.doubleClickCount")
        assert count == 1

    @pytest.mark.asyncio
    async def test_right_click_at_coordinates(self, browser_instance, test_server):
        """Test right-clicking at coordinates."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Add context menu handler
        await nav.execute_script(
            """
            window.rightClickDetected = false;
            document.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                window.rightClickDetected = true;
                window.rightClickX = e.clientX;
                window.rightClickY = e.clientY;
            });
        """
        )

        # Right-click at specific coordinates
        await input_ctrl.click_at_coordinates(200, 300, button="right")

        await asyncio.sleep(0.5)

        # Verify right-click was detected
        detected = await nav.execute_script("return window.rightClickDetected")
        assert detected is True

        x = await nav.execute_script("return window.rightClickX")
        y = await nav.execute_script("return window.rightClickY")
        margin = 5
        assert abs(x - 200) < margin  # Allow small margin for accuracy
        assert abs(y - 300) < margin


class TestScreenSpaceDrag:
    """Test screen-space drag functionality."""

    @pytest.mark.asyncio
    async def test_drag_from_to_coordinates(self, browser_instance, test_server):
        """Test dragging from one coordinate to another."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Setup drag detection
        await nav.execute_script(
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
        """
        )

        # Drag from (125, 125) to (300, 300) - center of draggable to new position
        await input_ctrl.drag_from_to(125, 125, 300, 300, duration=1.0)

        await asyncio.sleep(0.5)

        # Check drag events were recorded
        events = await nav.execute_script("return window.dragEvents")
        assert len(events) > 0
        assert events[0]["type"] == "start"
        assert events[-1]["type"] == "end"

        # Check final position of draggable
        final_pos = await nav.execute_script(
            """
            const el = document.getElementById('test-draggable');
            return {left: parseInt(el.style.left), top: parseInt(el.style.top)};
        """
        )

        # Should have moved approximately to the target position
        drag_margin = 50
        assert abs(final_pos["left"] - 275) < drag_margin  # Allow margin for drag accuracy
        assert abs(final_pos["top"] - 275) < drag_margin

    @pytest.mark.asyncio
    async def test_puzzle_captcha_drag(self, browser_instance, test_server):
        """Test solving a puzzle CAPTCHA using drag."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Get puzzle piece and slot positions
        positions = await nav.execute_script(
            """
            const piece = document.querySelector('.puzzle-piece');
            const slot = document.querySelector('.puzzle-slot');
            const pieceRect = piece.getBoundingClientRect();
            const slotRect = slot.getBoundingClientRect();
            return {
                piece: {x: pieceRect.left + pieceRect.width/2, y: pieceRect.top + pieceRect.height/2},
                slot: {x: slotRect.left + slotRect.width/2, y: slotRect.top + slotRect.height/2}
            };
        """
        )

        # Drag puzzle piece to slot
        await input_ctrl.drag_from_to(
            int(positions["piece"]["x"]), int(positions["piece"]["y"]), int(positions["slot"]["x"]), int(positions["slot"]["y"]), duration=1.5
        )

        await asyncio.sleep(1.0)

        # Check if puzzle was solved
        solved = await nav.execute_script("return window.captchaState.solved.puzzle")
        assert solved is True


class TestZoomInteractions:
    """Test zoom functionality."""

    @pytest.mark.asyncio
    async def test_zoom_scale(self, browser_instance, test_server):
        """Test zooming the page."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Zoom in to 150%
        zoom_in = 1.5
        await input_ctrl.zoom(zoom_in)

        # Check zoom was applied
        scale = await nav.execute_script(
            """
            const transform = document.body.style.transform;
            const match = transform.match(/scale\\(([^)]+)\\)/);
            return match ? parseFloat(match[1]) : 1.0;
        """
        )
        assert scale == zoom_in

        # Zoom out to 75%
        zoom_out = 0.75
        await input_ctrl.zoom(zoom_out)

        scale = await nav.execute_script(
            """
            const transform = document.body.style.transform;
            const match = transform.match(/scale\\(([^)]+)\\)/);
            return match ? parseFloat(match[1]) : 1.0;
        """
        )
        assert scale == zoom_out

        # Reset zoom
        await input_ctrl.zoom(1.0)

    @pytest.mark.asyncio
    async def test_zoom_at_center(self, browser_instance, test_server):
        """Test zooming at specific center point."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Zoom in at specific point (e.g., the submit button)
        button_pos = await nav.execute_script(
            """
            const btn = document.getElementById('submit-btn');
            const rect = btn.getBoundingClientRect();
            return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
        """
        )

        await input_ctrl.zoom(2.0, int(button_pos["x"]), int(button_pos["y"]))

        # Check zoom and origin were set
        transform_data = await nav.execute_script(
            """
            return {
                transform: document.body.style.transform,
                origin: document.body.style.transformOrigin
            };
        """
        )

        assert "scale(2)" in transform_data["transform"]
        assert f"{int(button_pos['x'])}px" in transform_data["origin"]
        assert f"{int(button_pos['y'])}px" in transform_data["origin"]


class TestSwipeGestures:
    """Test swipe gestures."""

    @pytest.mark.asyncio
    async def test_swipe_horizontal(self, browser_instance, test_server):
        """Test horizontal swipe gesture."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Setup swipe detection
        await nav.execute_script(
            """
            window.swipeDetected = null;

            let touchStartX = 0;
            let touchStartY = 0;

            document.addEventListener('touchstart', (e) => {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            });

            document.addEventListener('touchend', (e) => {
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;

                const deltaX = touchEndX - touchStartX;
                const deltaY = touchEndY - touchStartY;

                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    window.swipeDetected = deltaX > 0 ? 'right' : 'left';
                } else {
                    window.swipeDetected = deltaY > 0 ? 'down' : 'up';
                }
            });
        """
        )

        # Perform horizontal swipe (left to right)
        await input_ctrl.swipe(100, 300, 400, 300, duration=0.5)

        await asyncio.sleep(0.5)

        # Check swipe was detected
        swipe_direction = await nav.execute_script("return window.swipeDetected")
        assert swipe_direction == "right"

        # Reset
        await nav.execute_script("window.swipeDetected = null")

        # Perform horizontal swipe (right to left)
        await input_ctrl.swipe(400, 300, 100, 300, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await nav.execute_script("return window.swipeDetected")
        assert swipe_direction == "left"

    @pytest.mark.asyncio
    async def test_swipe_vertical(self, browser_instance, test_server):
        """Test vertical swipe gesture."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Setup swipe detection (reuse from horizontal test)
        await nav.execute_script(
            """
            window.swipeDetected = null;

            let touchStartX = 0;
            let touchStartY = 0;

            document.addEventListener('touchstart', (e) => {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            }, {passive: true});

            document.addEventListener('touchend', (e) => {
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;

                const deltaX = touchEndX - touchStartX;
                const deltaY = touchEndY - touchStartY;

                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    window.swipeDetected = deltaX > 0 ? 'right' : 'left';
                } else {
                    window.swipeDetected = deltaY > 0 ? 'down' : 'up';
                }
            }, {passive: true});
        """
        )

        # Perform vertical swipe (top to bottom)
        await input_ctrl.swipe(300, 100, 300, 400, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await nav.execute_script("return window.swipeDetected")
        assert swipe_direction == "down"

        # Reset
        await nav.execute_script("window.swipeDetected = null")

        # Perform vertical swipe (bottom to top)
        await input_ctrl.swipe(300, 400, 300, 100, duration=0.5)

        await asyncio.sleep(0.5)

        swipe_direction = await nav.execute_script("return window.swipeDetected")
        assert swipe_direction == "up"


class TestTextExtraction:
    """Test text extraction functionality."""

    @pytest.mark.asyncio
    async def test_extract_text_from_page(self, browser_instance, test_server):
        """Test extracting human-readable text from a page."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Extract text with structure
        text = await nav.extract_text(preserve_structure=True)

        # Check key text is present
        assert "Login Form" in text
        assert "Username" in text
        assert "Password" in text
        assert "Remember me" in text

        # Extract text without structure
        flat_text = await nav.extract_text(preserve_structure=False)
        assert len(flat_text) > 0
        assert "Login Form" in flat_text

    @pytest.mark.asyncio
    async def test_extract_links(self, browser_instance, test_server):
        """Test extracting links from a page."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Add some test links
        await nav.execute_script(
            """
            const container = document.getElementById('login-container');
            container.innerHTML += '<a href="/forgot">Forgot Password?</a>';
            container.innerHTML += '<a href="/register">Sign Up</a>';
            container.innerHTML += '<a href="https://example.com">External Link</a>';
        """
        )

        # Extract links
        links = await nav.extract_links(absolute=True)

        # Check links were extracted
        min_links = 3
        assert len(links) >= min_links

        # Check link structure
        for link in links:
            assert "href" in link
            assert "text" in link
            assert "title" in link

    @pytest.mark.asyncio
    async def test_extract_forms(self, browser_instance, test_server):
        """Test extracting form information."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Extract forms
        forms = await nav.extract_forms()

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
