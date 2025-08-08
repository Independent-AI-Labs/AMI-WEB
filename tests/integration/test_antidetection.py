"""Integration tests for anti-detection features."""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.core.manager import ChromeManager
from chrome_manager.utils.config import Config


class TestAntiDetection:
    """Test anti-detection features on bot.sannysoft.com."""

    @pytest.mark.asyncio
    async def test_first_tab_antidetection(self):
        """Test anti-detection on first tab."""
        instance = BrowserInstance(config=Config())
        driver = await instance.launch(headless=False, anti_detect=True)

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
                        plugin_count = test_result
                        results["plugins"] = plugin_count != "0"
                        results["plugin_count"] = plugin_count
                    elif "WebGL Vendor" in test_name:
                        results["webgl_vendor"] = "Canvas has no webgl" not in test_result
                    elif "WebGL Renderer" in test_name:
                        results["webgl_renderer"] = "Canvas has no webgl" not in test_result

            # Assert all critical tests pass
            assert results.get("webdriver", False), "WebDriver detected!"
            assert results.get("plugins", False), f"No plugins detected! Count: {results.get('plugin_count', '0')}"
            assert results.get("webgl_vendor", False), "WebGL vendor not spoofed!"
            assert results.get("webgl_renderer", False), "WebGL renderer not spoofed!"

        finally:
            await instance.terminate()

    @pytest.mark.asyncio
    async def test_second_tab_antidetection(self):
        """Test anti-detection on second tab opened via window.open()."""
        instance = BrowserInstance(config=Config())
        driver = await instance.launch(headless=False, anti_detect=True)

        try:
            # First tab
            driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Open second tab with about:blank first
            original_handles = set(driver.window_handles)
            driver.execute_script("window.open('about:blank', '_blank');")

            # Wait for new window and switch to it
            time.sleep(0.5)
            new_handles = set(driver.window_handles) - original_handles
            assert len(new_handles) == 1, f"Expected 1 new window, got {len(new_handles)}"
            new_window = new_handles.pop()

            # Switch to the NEW tab
            driver.switch_to.window(new_window)

            # Give time for CDP injection to apply to blank tab
            time.sleep(1)

            # Now navigate to the actual URL
            driver.get("https://bot.sannysoft.com")

            # Wait for page to load
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)  # Give page time to fully render

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

            # Check how bot.sannysoft actually tests
            old_test = driver.execute_script(
                """
                // This is how bot.sannysoft.com tests plugins (Old)
                var plugins = navigator.plugins;
                var count = 0;
                for(var i = 0; i < plugins.length; i++) {
                    count++;
                }
                return count;
            """
            )
            print(f"Old plugin test (for loop): {old_test}")

            # Check JSON stringify
            json_test = driver.execute_script(
                """
                try {
                    return JSON.stringify(navigator.plugins);
                } catch(e) {
                    return 'Error: ' + e.message;
                }
            """
            )
            print(f"JSON.stringify(navigator.plugins): {json_test}")

            # Check instanceof
            instanceof_test = driver.execute_script(
                """
                return {
                    'plugins instanceof PluginArray': navigator.plugins instanceof PluginArray,
                    'plugins[0] instanceof Plugin': navigator.plugins[0] ? navigator.plugins[0] instanceof Plugin : 'no plugin[0]',
                    'toString': navigator.plugins.toString(),
                    'valueOf': typeof navigator.plugins.valueOf()
                };
            """
            )
            print(f"instanceof tests: {instanceof_test}")

            # Try bot.sannysoft's actual test - look for their script
            bot_test = driver.execute_script(
                """
                // Simulate bot.sannysoft.com's plugin test
                function testPlugins() {
                    var plugins = navigator.plugins;

                    // Method 1: Direct length check
                    var length1 = plugins.length;

                    // Method 2: Iterate and count
                    var length2 = 0;
                    for(var i = 0; i < 1000; i++) {
                        if(plugins[i]) length2++;
                        else break;
                    }

                    // Method 3: Check if iterable
                    var length3 = 0;
                    try {
                        for(var p of plugins) {
                            length3++;
                        }
                    } catch(e) {
                        length3 = -1;
                    }

                    return {
                        'direct': length1,
                        'iterate': length2,
                        'forof': length3,
                        'array_from': Array.from ? Array.from(plugins).length : -2
                    };
                }
                return testPlugins();
            """
            )
            print(f"Bot test methods: {bot_test}")
            print("========================\n")

            # Check second tab
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            print("\n=== PARSING SECOND TAB RESULTS ===")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                min_cells = 2
                if len(cells) >= min_cells:
                    test_name = cells[0].text.strip()
                    test_result = cells[1].text.strip()
                    print(f"Test: {test_name} -> Result: {test_result}")

                    if "WebDriver" in test_name and "Advanced" in test_name:
                        results["webdriver"] = test_result == "passed"
                    elif "WebDriver" in test_name and "(New)" in test_name:
                        # The new WebDriver test shows "missing (passed)" when not detected
                        # or "present (failed)" when detected
                        results["webdriver_new"] = "missing" in test_result or ("passed" in test_result and "failed" not in test_result)
                    elif "Plugins Length" in test_name:
                        # Get the plugin count regardless of (Old) or (New)
                        plugin_count = test_result
                        results["plugins"] = plugin_count != "0"
                        results["plugin_count"] = plugin_count
                    elif "WebGL Vendor" in test_name:
                        results["webgl_vendor"] = "Canvas has no webgl" not in test_result
                    elif "WebGL Renderer" in test_name:
                        results["webgl_renderer"] = "Canvas has no webgl" not in test_result

            print(f"Parsed results: {results}")
            print("=================================\n")

            # Assert all critical tests pass on second tab
            assert results.get("webdriver", False), "WebDriver detected on second tab!"
            assert results.get("plugins", False), f"No plugins on second tab! Count: {results.get('plugin_count', '0')}"
            assert results.get("webgl_vendor", False), "WebGL vendor not spoofed on second tab!"
            assert results.get("webgl_renderer", False), "WebGL renderer not spoofed on second tab!"

        finally:
            await instance.terminate()

    @pytest.mark.asyncio
    async def test_mcp_manager_antidetection(self):
        """Test that ChromeManager (used by MCP) has anti-detection by default."""
        manager = ChromeManager()

        try:
            await manager.initialize()

            # Get instance without explicitly passing anti_detect
            instance = await manager.get_or_create_instance(
                headless=False,
                use_pool=False,  # Don't use pool for direct testing
            )

            instance.driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(instance.driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Check critical tests
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
                        plugin_count = test_result
                        results["plugins"] = plugin_count != "0"
                        results["plugin_count"] = plugin_count

            # ChromeManager should have anti-detection enabled by default
            assert results.get("webdriver", False), "MCP ChromeManager: WebDriver detected!"
            assert results.get("plugins", False), f"MCP ChromeManager: No plugins! Count: {results.get('plugin_count', '0')}"

        finally:
            await manager.shutdown()


class TestH264Codec:
    """Test H264 codec spoofing."""

    @pytest.mark.asyncio
    async def test_h264_codec_response(self):
        """Test that H264 codec returns 'probably' instead of empty/warn."""
        instance = BrowserInstance(config=Config())
        driver = await instance.launch(headless=False, anti_detect=True)

        try:
            driver.get("https://bot.sannysoft.com")
            wait = WebDriverWait(driver, 10)
            wait.until(expected_conditions.presence_of_element_located((By.TAG_NAME, "table")))

            # Check H264 codec directly via JavaScript
            result = driver.execute_script(
                """
                var video = document.createElement('video');
                return video.canPlayType('video/mp4; codecs="avc1.42E01E"');
            """
            )

            assert result == "probably", f"H264 codec returned '{result}' instead of 'probably'"

        finally:
            await instance.terminate()
