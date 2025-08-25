"""Optimized integration tests for real browser interactions only."""

import asyncio

import pytest


class TestRealBrowserInteractions:
    """Test real browser interactions that require actual browser instance."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_website_navigation(self, browser_instance):
        """Test navigating to real websites."""
        # Test actual navigation with network
        result = await browser_instance.navigate("https://example.com")
        assert result["status"] == "success"

        # Verify page loaded
        title = await browser_instance.execute_script("return document.title;")
        assert "Example" in title["result"]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_form_submission(self, browser_instance, test_html_server):
        """Test real form submission with server."""
        # Navigate to test form
        test_url = f"http://localhost:{test_html_server.port}/form.html"
        await browser_instance.navigate(test_url)

        # Fill and submit form
        await browser_instance.type("#username", "testuser")
        await browser_instance.type("#password", "testpass")
        await browser_instance.click("#submit")

        # Wait for submission result
        await asyncio.sleep(1)

        # Verify submission
        result = await browser_instance.execute_script("return document.body.innerText;")
        assert "submitted" in result["result"].lower()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_ajax_content_loading(self, browser_instance, test_html_server):
        """Test AJAX content loading with real server."""
        test_url = f"http://localhost:{test_html_server.port}/ajax.html"
        await browser_instance.navigate(test_url)

        # Trigger AJAX load
        await browser_instance.click("#load-content")

        # Wait for content
        await browser_instance.wait_for_element("#ajax-content", timeout=5)

        # Verify content loaded
        content = await browser_instance.execute_script("return document.getElementById('ajax-content').innerText;")
        assert content["result"] != ""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_screenshot_capture(self, browser_instance):
        """Test real screenshot capture."""
        await browser_instance.navigate("https://example.com")

        # Capture screenshot
        screenshot = await browser_instance.screenshot()

        # Verify screenshot data
        assert screenshot is not None
        min_screenshot_size = 1000
        assert len(screenshot) > min_screenshot_size  # Should have actual image data

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_captcha_solving(self, browser_instance, test_html_server):
        """Test CAPTCHA solving with real browser."""
        test_url = f"http://localhost:{test_html_server.port}/captcha.html"
        await browser_instance.navigate(test_url)

        # Get CAPTCHA challenge
        captcha_text = await browser_instance.execute_script("return document.getElementById('captcha-challenge').innerText;")

        # Solve simple math CAPTCHA
        import re

        match = re.search(r"(\d+)\s*\+\s*(\d+)", captcha_text["result"])
        if match:
            result = int(match.group(1)) + int(match.group(2))
            await browser_instance.type("#captcha-answer", str(result))
            await browser_instance.click("#captcha-submit")

            # Verify solved
            await asyncio.sleep(0.5)
            success = await browser_instance.execute_script("return document.querySelector('.success') !== null;")
            assert success["result"] is True


class TestRealBrowserConcurrency:
    """Test concurrent browser operations with real instances."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_browser_operations(self, session_manager):
        """Test parallel operations on multiple real browsers."""
        manager = session_manager.chrome_manager

        # Create multiple instances
        instances = []
        for _ in range(2):  # Reduced from 3 to 2 for speed
            instance = await manager.get_or_create_instance(headless=True)
            instances.append(instance)

        try:
            # Parallel navigation
            tasks = [instance.navigate("https://example.com") for instance in instances]
            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert all(r["status"] == "success" for r in results)

        finally:
            # Cleanup
            for instance in instances:
                await instance.terminate()
