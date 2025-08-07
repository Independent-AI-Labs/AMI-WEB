"""Debug WebGL issue in anti-detection mode."""

import asyncio
import time

from chrome_manager.core.instance import BrowserInstance


async def test_webgl_debug():
    """Debug WebGL context creation."""
    print("Testing WebGL in anti-detection mode...")

    instance = BrowserInstance()

    try:
        # Launch with anti-detection enabled
        driver = await instance.launch(headless=False, anti_detect=True)

        # Navigate to bot.sannysoft.com
        print("\nNavigating to bot.sannysoft.com...")
        driver.get("https://bot.sannysoft.com/")
        time.sleep(3)

        # Test 1: Check if WebGL context can be created
        print("\n=== Test 1: WebGL Context Creation ===")
        webgl_test = driver.execute_script(
            """
            try {
                var canvas = document.createElement('canvas');
                var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    return {
                        success: true,
                        context: gl.constructor.name,
                        vendor: gl.getParameter(gl.VENDOR),
                        renderer: gl.getParameter(gl.RENDERER),
                        version: gl.getParameter(gl.VERSION)
                    };
                } else {
                    return {success: false, error: 'No WebGL context'};
                }
            } catch(e) {
                return {success: false, error: e.toString()};
            }
        """
        )
        print(f"WebGL context test: {webgl_test}")

        # Test 2: Check what the page sees
        print("\n=== Test 2: Page Detection Results ===")
        page_results = driver.execute_script(
            """
            var results = {};
            var rows = document.querySelectorAll('tr');
            for (var i = 0; i < rows.length; i++) {
                var cells = rows[i].querySelectorAll('td');
                if (cells.length >= 2) {
                    var key = cells[0].innerText;
                    var value = cells[1].innerText;
                    if (key.indexOf('WebGL') !== -1 || key.indexOf('Chrome') !== -1 || key.indexOf('webdriver') !== -1) {
                        results[key] = value;
                    }
                }
            }
            return results;
        """
        )
        for key, value in page_results.items():
            print(f"  {key}: {value}")

        # Test 3: Check if WEBGL_debug_renderer_info extension works
        print("\n=== Test 3: WebGL Debug Extension ===")
        debug_test = driver.execute_script(
            """
            try {
                var canvas = document.createElement('canvas');
                var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    if (debugInfo) {
                        return {
                            hasExtension: true,
                            vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                            renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                        };
                    } else {
                        return {hasExtension: false, error: 'No debug extension'};
                    }
                } else {
                    return {hasExtension: false, error: 'No WebGL context'};
                }
            } catch(e) {
                return {hasExtension: false, error: e.toString()};
            }
        """
        )
        print(f"Debug extension test: {debug_test}")

        # Test 4: Check Chrome arguments
        print("\n=== Test 4: Chrome GPU Status ===")
        driver.get("chrome://gpu")
        time.sleep(2)
        gpu_status = driver.execute_script(
            """
            var status = document.querySelector('.feature-status-list');
            if (status) {
                var items = status.querySelectorAll('li');
                var results = [];
                for (var i = 0; i < Math.min(items.length, 5); i++) {
                    results.push(items[i].innerText);
                }
                return results;
            }
            return ['Could not read GPU status'];
        """
        )
        print("GPU Features:")
        for item in gpu_status:
            print(f"  - {item}")

        print("\n=== Press Enter to close browser ===")
        input()

    finally:
        await instance.terminate()


if __name__ == "__main__":
    asyncio.run(test_webgl_debug())
