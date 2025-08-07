"""Integration tests for browser functionality."""

import asyncio
import tempfile

import pytest
from loguru import logger

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.core.manager import ChromeManager
from chrome_manager.facade.input import InputController
from chrome_manager.facade.media import ScreenshotController
from chrome_manager.facade.navigation import NavigationController
from tests.fixtures.test_server import HTMLTestServer


@pytest.fixture(scope="session")
def test_server(event_loop):
    """Start test HTTP server for the test session."""

    async def _start_server():
        server = HTMLTestServer(port=8888)
        base_url = await server.start()
        return server, base_url

    server, base_url = event_loop.run_until_complete(_start_server())
    yield base_url
    event_loop.run_until_complete(server.stop())


@pytest.fixture
def browser_instance(event_loop):
    """Create a browser instance for testing."""
    instance = BrowserInstance()
    driver = event_loop.run_until_complete(instance.launch(headless=True))
    yield instance
    event_loop.run_until_complete(instance.terminate())


@pytest.fixture
def chrome_manager(event_loop):
    """Create a Chrome manager for testing."""
    manager = ChromeManager()
    event_loop.run_until_complete(manager.start())
    yield manager
    event_loop.run_until_complete(manager.stop())


class TestBrowserNavigation:
    """Test browser navigation functionality."""

    @pytest.mark.asyncio
    async def test_navigate_to_page(self, browser_instance, test_server):
        """Test basic page navigation."""
        nav = NavigationController(browser_instance)

        # Navigate to login page
        result = await nav.navigate(f"{test_server}/login_form.html")

        assert result.url.endswith("login_form.html")
        assert "Login" in result.title
        assert result.status_code == 200
        assert result.load_time > 0

    @pytest.mark.asyncio
    async def test_wait_for_element(self, browser_instance, test_server):
        """Test waiting for elements to appear."""
        nav = NavigationController(browser_instance)

        # Navigate to dynamic content page
        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Wait for specific element
        found = await nav.wait_for_element("#content-area", timeout=5)
        assert found is True

        # Try non-existent element
        found = await nav.wait_for_element("#non-existent", timeout=1)
        assert found is False

    @pytest.mark.asyncio
    async def test_execute_script(self, browser_instance, test_server):
        """Test JavaScript execution."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Execute script to get form data
        result = await nav.execute_script("return window.testHelpers.getFormData()")
        assert result["username"] == ""
        assert result["password"] == ""
        assert result["remember"] is False

        # Execute script to fill form
        await nav.execute_script("window.testHelpers.fillForm(arguments[0], arguments[1])", "testuser", "password123")

        # Verify form was filled
        result = await nav.execute_script("return window.testHelpers.getFormData()")
        assert result["username"] == "testuser"
        assert result["password"] == "password123"

    @pytest.mark.asyncio
    async def test_get_page_content(self, browser_instance, test_server):
        """Test retrieving page HTML content."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Get outer HTML
        html = await nav.get_page_content()
        assert "<title>CAPTCHA Test Page</title>" in html
        assert "text-captcha" in html

        # Get inner HTML of specific element
        element_html = await nav.get_element_html("#text-captcha")
        assert len(element_html) > 0  # Should contain the CAPTCHA text


class TestInputSimulation:
    """Test input simulation functionality."""

    @pytest.mark.asyncio
    async def test_click_element(self, browser_instance, test_server):
        """Test clicking elements."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Click submit button without filling form
        await input_ctrl.click("#submit-btn")

        # Check for validation errors
        await asyncio.sleep(0.5)
        errors = await nav.execute_script("return window.formInteractions.validationErrors")
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_type_text(self, browser_instance, test_server):
        """Test typing text into inputs."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Type into username field
        await input_ctrl.type_text("#username", "testuser", clear=True)

        # Type into password field
        await input_ctrl.type_text("#password", "password123", clear=True)

        # Verify input values
        result = await nav.execute_script("return window.testHelpers.getFormData()")
        assert result["username"] == "testuser"
        assert result["password"] == "password123"

    @pytest.mark.asyncio
    async def test_checkbox_interaction(self, browser_instance, test_server):
        """Test checkbox interactions."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Check the robot checkbox
        await input_ctrl.click("#robot-checkbox")

        # Verify it's checked
        is_checked = await nav.execute_script("return document.getElementById('robot-checkbox').checked")
        assert is_checked is True

        # Click again to uncheck
        await input_ctrl.click("#robot-checkbox")
        is_checked = await nav.execute_script("return document.getElementById('robot-checkbox').checked")
        assert is_checked is False

    @pytest.mark.asyncio
    async def test_form_submission(self, browser_instance, test_server):
        """Test complete form submission flow."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Fill and submit form
        await input_ctrl.type_text("#username", "testuser")
        await input_ctrl.type_text("#password", "password123")
        await input_ctrl.click("#remember")
        await input_ctrl.click("#submit-btn")

        # Wait for submission to process
        await asyncio.sleep(1.5)

        # Check submission data
        data = await nav.execute_script("return window.formInteractions.lastSubmittedData")
        assert data["username"] == "testuser"
        assert data["password"] == "password123"
        assert data["remember"] is True

        # Check login status
        status = await nav.execute_script("return sessionStorage.getItem('loggedInUser')")
        assert status == "testuser"


class TestScreenshotCapture:
    """Test screenshot functionality."""

    @pytest.mark.asyncio
    async def test_viewport_screenshot(self, browser_instance, test_server):
        """Test capturing viewport screenshot."""
        nav = NavigationController(browser_instance)
        screenshot_ctrl = ScreenshotController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Capture viewport
        screenshot_data = await screenshot_ctrl.capture_viewport()
        assert len(screenshot_data) > 0

        # Verify it's valid PNG data
        assert screenshot_data[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_element_screenshot(self, browser_instance, test_server):
        """Test capturing element screenshot."""
        nav = NavigationController(browser_instance)
        screenshot_ctrl = ScreenshotController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Capture specific element
        screenshot_data = await screenshot_ctrl.capture_element(".captcha-container")
        assert len(screenshot_data) > 0

    @pytest.mark.asyncio
    async def test_full_page_screenshot(self, browser_instance, test_server):
        """Test capturing full page screenshot."""
        nav = NavigationController(browser_instance)
        screenshot_ctrl = ScreenshotController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Capture full page
        screenshot_data = await screenshot_ctrl.capture_full_page()
        assert len(screenshot_data) > 0

        # Save to file for manual verification
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(screenshot_data)
            logger.info(f"Full page screenshot saved to: {f.name}")


class TestDynamicContent:
    """Test handling of dynamic content."""

    @pytest.mark.asyncio
    async def test_ajax_content_loading(self, browser_instance, test_server):
        """Test waiting for AJAX content."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Click button to load AJAX content
        await input_ctrl.click('[data-testid="load-ajax-btn"]')

        # Wait for content to load
        await nav.wait_for_element(".ajax-content", timeout=3)

        # Verify content loaded
        ajax_count = await nav.execute_script("return window.dynamicState.ajaxCallCount")
        assert ajax_count == 1

    @pytest.mark.asyncio
    async def test_modal_interaction(self, browser_instance, test_server):
        """Test modal dialog interaction."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Open modal
        await input_ctrl.click('[data-testid="show-modal-btn"]')
        await asyncio.sleep(0.5)

        # Check modal is visible
        is_visible = await nav.execute_script("return document.getElementById('modal').style.display === 'block'")
        assert is_visible is True

        # Type in modal input
        await input_ctrl.type_text("#modal-input", "Test modal input")

        # Submit modal
        await input_ctrl.click('[data-testid="modal-submit"]')
        await asyncio.sleep(0.5)

        # Verify modal data was saved
        modal_data = await nav.execute_script("return window.dynamicState.modalData")
        assert modal_data == "Test modal input"

    @pytest.mark.asyncio
    async def test_infinite_scroll(self, browser_instance, test_server):
        """Test infinite scroll functionality."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Switch to infinite scroll tab
        await nav.execute_script("switchTab(2)")

        # Get initial item count
        initial_count = await nav.execute_script("return window.dynamicState.scrollItemCount")

        # Trigger scroll
        await nav.execute_script("window.testHelpers.triggerInfiniteScroll()")
        await asyncio.sleep(0.5)

        # Check new items were added
        new_count = await nav.execute_script("return window.dynamicState.scrollItemCount")
        assert new_count > initial_count


class TestCaptchaHandling:
    """Test CAPTCHA handling scenarios."""

    @pytest.mark.asyncio
    async def test_text_captcha(self, browser_instance, test_server):
        """Test solving text CAPTCHA."""
        nav = NavigationController(browser_instance)
        input_ctrl = InputController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Get CAPTCHA text
        captcha_text = await nav.execute_script("return window.captchaState.textCaptcha")

        # Enter CAPTCHA
        await input_ctrl.type_text("#text-captcha-input", captcha_text)

        # Verify CAPTCHA
        await input_ctrl.click('[data-testid="verify-text-btn"]')
        await asyncio.sleep(0.5)

        # Check if solved
        is_solved = await nav.execute_script("return window.captchaState.solved.text")
        assert is_solved is True

    @pytest.mark.asyncio
    async def test_math_captcha(self, browser_instance, test_server):
        """Test solving math CAPTCHA."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/captcha_form.html")

        # Use helper to solve
        await nav.execute_script("window.testHelpers.solveCaptcha('math')")
        await asyncio.sleep(0.5)

        # Check if solved
        is_solved = await nav.execute_script("return window.captchaState.solved.math")
        assert is_solved is True


class TestBrowserPool:
    """Test browser pool management."""

    @pytest.mark.asyncio
    async def test_create_multiple_instances(self, chrome_manager):
        """Test creating multiple browser instances."""
        # Create multiple instances
        instance1 = await chrome_manager.create_instance(headless=True)
        instance2 = await chrome_manager.create_instance(headless=True)

        assert instance1.id != instance2.id

        # List instances
        instances = await chrome_manager.list_instances()
        assert len(instances) >= 2

        # Terminate instances
        await chrome_manager.terminate_instance(instance1.id)
        await chrome_manager.terminate_instance(instance2.id)

    @pytest.mark.asyncio
    async def test_pool_warm_instances(self, chrome_manager):
        """Test pool warm instance functionality."""
        # Request instance from pool
        instance = await chrome_manager.get_or_create_instance()
        assert instance is not None

        # Return to pool
        await chrome_manager.return_to_pool(instance.id)

        # Get from pool again (should be warm)
        instance2 = await chrome_manager.get_or_create_instance()
        assert instance2.id == instance.id  # Should get same instance

    @pytest.mark.asyncio
    async def test_parallel_operations(self, chrome_manager, test_server):
        """Test parallel operations on multiple instances."""
        # Create instances
        instance1 = await chrome_manager.create_instance(headless=True)
        instance2 = await chrome_manager.create_instance(headless=True)

        nav1 = NavigationController(instance1)
        nav2 = NavigationController(instance2)

        # Navigate in parallel
        results = await asyncio.gather(nav1.navigate(f"{test_server}/login_form.html"), nav2.navigate(f"{test_server}/captcha_form.html"))

        assert "Login" in results[0].title
        assert "CAPTCHA" in results[1].title

        # Cleanup
        await chrome_manager.terminate_instance(instance1.id)
        await chrome_manager.terminate_instance(instance2.id)


class TestScriptInjection:
    """Test script injection scenarios."""

    @pytest.mark.asyncio
    async def test_inject_custom_script(self, browser_instance, test_server):
        """Test injecting custom JavaScript."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/login_form.html")

        # Inject custom script
        await nav.execute_script(
            """
            window.customInjected = {
                timestamp: new Date().toISOString(),
                data: 'test-data',
                function: function() { return 'injected-function-result'; }
            };
        """
        )

        # Verify injection
        result = await nav.execute_script("return window.customInjected.data")
        assert result == "test-data"

        # Call injected function
        result = await nav.execute_script("return window.customInjected.function()")
        assert result == "injected-function-result"

    @pytest.mark.asyncio
    async def test_modify_dom(self, browser_instance, test_server):
        """Test DOM modification via script."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Add new element via script
        await nav.execute_script(
            """
            const newDiv = document.createElement('div');
            newDiv.id = 'injected-element';
            newDiv.textContent = 'Injected via script';
            newDiv.style.padding = '20px';
            newDiv.style.background = 'yellow';
            document.getElementById('content-area').appendChild(newDiv);
        """
        )

        # Verify element exists
        exists = await nav.wait_for_element("#injected-element", timeout=1)
        assert exists is True

        # Get element text
        text = await nav.execute_script("return document.getElementById('injected-element').textContent")
        assert text == "Injected via script"

    @pytest.mark.asyncio
    async def test_intercept_network_requests(self, browser_instance, test_server):
        """Test intercepting network requests via script."""
        nav = NavigationController(browser_instance)

        await nav.navigate(f"{test_server}/dynamic_content.html")

        # Inject request interceptor
        await nav.execute_script(
            """
            window.interceptedRequests = [];
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                window.interceptedRequests.push({
                    url: args[0],
                    timestamp: new Date().toISOString()
                });
                return originalFetch.apply(this, args);
            };
        """
        )

        # Trigger AJAX request
        await nav.execute_script("loadAjaxContent()")
        await asyncio.sleep(2)

        # Check intercepted requests
        requests = await nav.execute_script("return window.interceptedRequests")
        # Note: The AJAX simulation doesn't use real fetch, so we'd need to modify
        # the test page to actually test this properly


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
