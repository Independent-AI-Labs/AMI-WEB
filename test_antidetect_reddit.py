"""Test enhanced anti-detection against Reddit and other strict sites."""

import asyncio
import json

from chrome_manager.core.instance import BrowserInstance


async def test_reddit_antidetect():
    """Test browser with enhanced anti-detection against Reddit."""
    print("Testing enhanced anti-detection mode...")

    # Create instance with anti-detection
    instance = BrowserInstance()

    try:
        # Launch with anti-detection enabled
        driver = await instance.launch(headless=False, anti_detect=True)

        # Navigate to a blank page first to ensure scripts are loaded
        driver.get("about:blank")
        await asyncio.sleep(1)

        print("\n=== Phase 1: Pre-navigation checks ===")
        # Check if CDC properties exist before navigation
        cdc_check = driver.execute_script(
            """
            var cdcProps = [];
            for (var prop in window) {
                if (prop.indexOf('cdc') !== -1 || prop.indexOf('$cdc') !== -1) {
                    cdcProps.push(prop);
                }
            }
            return cdcProps;
        """
        )
        print(f"CDC properties found: {cdc_check if cdc_check else 'None'}")

        # Check navigator.webdriver
        webdriver_check = driver.execute_script("return navigator.webdriver")
        print(f"navigator.webdriver: {webdriver_check}")

        # Check chrome.runtime
        chrome_runtime = driver.execute_script("return typeof (window.chrome && window.chrome.runtime)")
        print(f"chrome.runtime: {chrome_runtime}")

        # Check Function.prototype.toString
        func_check = driver.execute_script(
            """
            try {
                var testFunc = Object.defineProperty;
                return testFunc.toString().indexOf('[native code]') !== -1;
            } catch(e) {
                return 'Error: ' + e.message;
            }
        """
        )
        print(f"Function native check: {func_check}")

        print("\n=== Phase 2: Testing on detection sites ===")

        # Test sites
        test_sites = [
            ("https://bot.sannysoft.com/", "General bot detection"),
            ("https://arh.antoinevastel.com/bots/areyouheadless", "Headless detection"),
            ("https://reddit.com", "Reddit (strict detection)"),
        ]

        for site, description in test_sites:
            print(f"\n--- Testing {description}: {site} ---")
            driver.get(site)
            await asyncio.sleep(3)

            # Check for CDC properties after page load
            cdc_check = driver.execute_script(
                """
                var cdcProps = [];
                for (var prop in window) {
                    if (prop.indexOf('cdc') !== -1 || prop.indexOf('$cdc') !== -1) {
                        cdcProps.push(prop);
                    }
                }
                return cdcProps;
            """
            )
            print(f"  CDC properties: {cdc_check if cdc_check else 'None'}")

            # Check webdriver
            webdriver = driver.execute_script("return navigator.webdriver")
            print(f"  navigator.webdriver: {webdriver}")

            # Check chrome object
            chrome_check = driver.execute_script(
                """
                return {
                    exists: typeof window.chrome !== 'undefined',
                    runtime: typeof (window.chrome && window.chrome.runtime) !== 'undefined',
                    app: typeof (window.chrome && window.chrome.app) !== 'undefined'
                };
            """
            )
            print(f"  chrome object: {json.dumps(chrome_check, indent=4)}")

            # Check plugins
            plugins = driver.execute_script(
                """
                var plugins = [];
                for (var i = 0; i < navigator.plugins.length; i++) {
                    plugins.push(navigator.plugins[i].name);
                }
                return plugins;
            """
            )
            print(f"  plugins: {plugins}")

            # Check if we're detected
            if "reddit.com" in site:
                # Check Reddit-specific detection
                reddit_check = driver.execute_script(
                    """
                    // Check if we can access Reddit normally
                    var bodyText = document.body ? document.body.innerText : '';
                    var blocked = (bodyText.indexOf('blocked') !== -1) ||
                                  (bodyText.indexOf('automated') !== -1) ||
                                  document.querySelector('.blocked-warning') !== null;
                    return {
                        blocked: blocked,
                        title: document.title,
                        canInteract: !blocked
                    };
                """
                )
                print(f"  Reddit detection result: {json.dumps(reddit_check, indent=4)}")

        print("\n=== Phase 3: Advanced detection checks ===")

        # Check for eval patterns in stack traces
        stack_check = driver.execute_script(
            """
            try {
                throw new Error('test');
            } catch(e) {
                return e.stack.includes('eval');
            }
        """
        )
        print(f"Eval in stack traces: {stack_check}")

        # Check Object.getOwnPropertyNames on window
        window_props = driver.execute_script(
            """
            var suspicious = [];
            var props = Object.getOwnPropertyNames(window);
            for (var i = 0; i < props.length; i++) {
                var prop = props[i];
                if (prop.indexOf('cdc') !== -1 || prop.indexOf('$cdc') !== -1 ||
                    prop.indexOf('selenium') !== -1 || prop.indexOf('webdriver') !== -1) {
                    suspicious.push(prop);
                }
            }
            return suspicious;
        """
        )
        print(f"Suspicious window properties: {window_props if window_props else 'None'}")

        print("\n=== Anti-detection test completed! ===")
        print("Press Enter to close the browser...")
        input()

    finally:
        await instance.terminate()


if __name__ == "__main__":
    asyncio.run(test_reddit_antidetect())
