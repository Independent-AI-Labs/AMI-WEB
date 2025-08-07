"""Integration tests for anti-detection features."""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Check critical anti-detection features
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
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
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Open second tab via window.open
            driver.execute_script("window.open('https://bot.sannysoft.com', '_blank');")
            driver.switch_to.window(driver.window_handles[1])
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(3)  # Give injection time to work

            # Check second tab
            rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
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
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Check critical tests
            rows = instance.driver.find_elements(By.CSS_SELECTOR, "table tr")
            results = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
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
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

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
