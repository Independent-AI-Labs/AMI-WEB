"""Integration tests for anti-detection features."""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


class TestAntiDetection:
    """Test anti-detection features on bot.sannysoft.com."""

    @pytest.mark.asyncio
    async def test_first_tab_antidetection(self, antidetect_browser):
        """Test anti-detection on first tab."""
        instance = antidetect_browser
        driver = instance.driver

        try:
            driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Check critical anti-detection features
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                min_cells = 2
                if len(cells) >= min_cells:
                    test_name = cells[0].text.strip()
                    test_result = cells[1].text.strip()

                    if "WebDriver" in test_name and "Advanced" in test_name:
                        results["webdriver"] = test_result == "passed"
                    elif "Plugins Length" in test_name:
                        results["plugins"] = "0" not in test_result
                        results["plugin_count"] = test_result
                    elif "WebGL Vendor" in test_name:
                        results["webgl_vendor"] = "Google Inc." in test_result or "Intel" in test_result
                        results["webgl_vendor_actual"] = test_result
                    elif "WebGL Renderer" in test_name:
                        results["webgl_renderer"] = "ANGLE" in test_result or "Intel" in test_result
                        results["webgl_renderer_actual"] = test_result

            # Assert critical features
            assert results.get("webdriver", False), "WebDriver detection failed"
            assert results.get("plugins", False), f"No plugins detected: {results.get('plugin_count', 'unknown')}"
            assert results.get("webgl_vendor", False), f"WebGL vendor not properly spoofed. Actual: {results.get('webgl_vendor_actual', 'unknown')}"
            assert results.get("webgl_renderer", False), f"WebGL renderer not properly spoofed. Actual: {results.get('webgl_renderer_actual', 'unknown')}"

        finally:
            pass  # Cleanup handled by fixture

    @pytest.mark.asyncio
    async def test_second_tab_antidetection(self, antidetect_browser):  # noqa: C901
        """Test anti-detection on second tab opened via window.open()."""
        instance = antidetect_browser
        driver = instance.driver

        try:
            # Navigate to initial page
            driver.get("https://example.com")
            wait = WebDriverWait(driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "h1")))

            # Store original window
            original_window = driver.current_window_handle

            # Open second tab via JavaScript (this is what fails with normal anti-detect)
            driver.execute_script("window.open('about:blank', '_blank');")
            time.sleep(1)  # Give time for CDP injection to apply

            # Switch to new tab
            for handle in driver.window_handles:
                if handle != original_window:
                    driver.switch_to.window(handle)
                    break

            # Now navigate to bot detection site in the second tab
            driver.get("https://bot.sannysoft.com")
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Verify we're on the right page
            assert "bot.sannysoft.com" in driver.current_url, f"Not on correct page: {driver.current_url}"

            # Direct check via JavaScript
            print("\n=== DIRECT JS CHECKS ===")
            webdriver_status = driver.execute_script("return navigator.webdriver")
            # Check what bot.sannysoft "WebDriver (New)" actually tests
            webdriver_new_test = driver.execute_script(
                """
                // This is likely what the "WebDriver (New)" test does
                return {
                    'navigator.webdriver': navigator.webdriver,
                    'toString': Object.prototype.toString.call(navigator.webdriver),
                    'type': typeof navigator.webdriver,
                    'truthy': !!navigator.webdriver
                };
            """
            )
            # Skip 'in' check as it may error with proxy
            plugin_count = driver.execute_script("return navigator.plugins ? navigator.plugins.length : -1")
            plugin_proto = driver.execute_script("return Object.getPrototypeOf(navigator.plugins).constructor.name")
            plugin_0_proto = driver.execute_script("return navigator.plugins[0] ? Object.getPrototypeOf(navigator.plugins[0]).constructor.name : 'none'")

            print(f"navigator.webdriver: {webdriver_status}")
            print(f"WebDriver (New) test result: {webdriver_new_test}")
            print(f"navigator.plugins.length: {plugin_count}")
            print(f"navigator.plugins prototype: {plugin_proto}")
            print(f"navigator.plugins[0] prototype: {plugin_0_proto}")

            # Old test for compatibility
            old_plugin_test = driver.execute_script(
                """
                let count = 0;
                for(let i = 0; i < navigator.plugins.length; i++) {
                    count++;
                }
                return count;
            """
            )
            print(f"Old plugin test (for loop): {old_plugin_test}")

            # Try to stringify plugins
            try:
                plugin_str = driver.execute_script("return JSON.stringify(navigator.plugins)")
                print(f"JSON.stringify(navigator.plugins): {plugin_str}")
            except Exception as e:
                print(f"JSON.stringify(navigator.plugins): {e}")

            # Test instanceof
            instanceof_test = driver.execute_script(
                """
                return {
                    'plugins instanceof PluginArray': navigator.plugins instanceof PluginArray,
                    'plugins[0] instanceof Plugin': navigator.plugins[0] ? navigator.plugins[0] instanceof Plugin : false,
                    'toString': Object.prototype.toString.call(navigator.plugins),
                    'valueOf': typeof navigator.plugins.valueOf()
                };
            """
            )
            print(f"instanceof tests: {instanceof_test}")

            # Check how bot.sannysoft.com counts plugins
            bot_test = driver.execute_script(
                """
                let methods = {};
                // Method 1: Direct length
                methods.direct = navigator.plugins.length;
                // Method 2: For loop
                let count = 0;
                for(let i = 0; i < navigator.plugins.length; i++) {
                    count++;
                }
                methods.iterate = count;
                // Method 3: For...of
                count = 0;
                try {
                    for(let plugin of navigator.plugins) {
                        count++;
                    }
                    methods.forof = count;
                } catch(e) {
                    methods.forof = 'error: ' + e;
                }
                // Method 4: Array.from
                try {
                    methods.array_from = Array.from(navigator.plugins).length;
                } catch(e) {
                    methods.array_from = 'error: ' + e;
                }
                return methods;
            """
            )
            print(f"Bot test methods: {bot_test}")
            print("========================\n")

            # Parse the actual results from the page
            print("\n=== PARSING SECOND TAB RESULTS ===")
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                min_cells = 2
                if len(cells) >= min_cells:
                    test_name = cells[0].text.strip()
                    test_result = cells[1].text.strip()
                    print(f"Test: {test_name} -> Result: {test_result}")

                    # Check WebDriver (New) test specifically
                    if "WebDriver" in test_name and "New" in test_name:
                        # This test checks if navigator.webdriver exists
                        results["webdriver_new"] = "missing" in test_result.lower() or "passed" in test_result.lower()

                    if "WebDriver" in test_name and "Advanced" not in test_name and "New" not in test_name:
                        results["webdriver"] = "passed" in test_result
                    elif "WebDriver Advanced" in test_name:
                        results["webdriver"] = test_result == "passed"
                    elif "Plugins Length" in test_name:
                        results["plugins"] = "0" not in test_result
                        results["plugin_count"] = test_result
                    elif "WebGL Vendor" in test_name:
                        results["webgl_vendor"] = "Google Inc." in test_result or "Intel" in test_result
                        results["webgl_vendor_actual"] = test_result
                    elif "WebGL Renderer" in test_name:
                        results["webgl_renderer"] = "ANGLE" in test_result or "Intel" in test_result
                        results["webgl_renderer_actual"] = test_result

            print(f"Parsed results: {results}")
            print("=================================\n")

            # The critical assertion - navigator.webdriver should not be detected
            assert webdriver_status is None or webdriver_status is False, f"navigator.webdriver is {webdriver_status}, should be None or False"

            # Assert WebDriver (New) test passes
            assert results.get("webdriver_new", False), "WebDriver (New) test failed - navigator.webdriver was detected"

            # Other critical features on second tab
            assert results.get("webdriver", False), "WebDriver Advanced detection failed on second tab"
            assert results.get("plugins", False), f"No plugins on second tab! Count: {results.get('plugin_count', 'unknown')}"
            assert plugin_count > 0, f"Direct plugin check failed: {plugin_count}"
            assert results.get("webgl_vendor", False), "WebGL vendor not properly spoofed on second tab"
            assert results.get("webgl_renderer", False), "WebGL renderer not properly spoofed on second tab"

        finally:
            pass  # Cleanup handled by fixture

    @pytest.mark.asyncio
    async def test_mcp_manager_antidetection(self, session_manager):
        """Test that ChromeManager (used by MCP) has anti-detection by default."""
        manager = session_manager
        instance = None

        try:
            # Get instance without explicitly passing anti_detect
            instance = await manager.get_or_create_instance(
                headless=True,
                use_pool=False,  # Don't use pool for direct testing
            )

            instance.driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(instance.driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Check critical anti-detection features
            rows = instance.driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                min_cells = 2
                if len(cells) >= min_cells:
                    test_name = cells[0].text.strip()
                    test_result = cells[1].text.strip()

                    if "WebDriver" in test_name and "Advanced" in test_name:
                        results["webdriver"] = test_result == "passed"
                    elif "Plugins Length" in test_name:
                        results["plugins"] = "0" not in test_result
                        results["plugin_count"] = test_result

            # ChromeManager should have anti-detection enabled by default
            assert results.get("webdriver", False), "ChromeManager doesn't have anti-detection enabled by default"
            assert results.get("plugins", False), f"No plugins with ChromeManager: {results.get('plugin_count', 'unknown')}"

        finally:
            # Ensure cleanup even if instance wasn't fully created
            if instance:
                # For standalone instances, terminate them properly
                await manager.terminate_instance(instance.id, return_to_pool=False)


class TestH264Codec:
    """Test H.264 codec support."""

    @pytest.mark.asyncio
    async def test_h264_codec_response(self, antidetect_browser):
        """Test that H.264 codec is properly supported."""
        instance = antidetect_browser
        driver = instance.driver

        try:
            # Test on a page that checks codec support
            driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(1)

            # Direct check for H.264 support
            h264_support = driver.execute_script(
                """
                const video = document.createElement('video');
                return video.canPlayType('video/mp4; codecs="avc1.42E01E"') !== '';
                """
            )

            assert h264_support, "H.264 codec is not supported"

            # Check if VIDEO_CODECS test passes on bot.sannysoft.com
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                min_cells = 2
                if len(cells) >= min_cells:
                    test_name = cells[0].text.strip()
                    test_result = cells[1].text.strip()
                    if "VIDEO_CODECS" in test_name:
                        assert "ok" in test_result.lower(), f"VIDEO_CODECS test failed: {test_result}"
                        break

        finally:
            pass  # Cleanup handled by fixture
