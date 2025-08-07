"""Check if extension runs on second tab."""

import asyncio
import time

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.utils.config import Config


async def test():
    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)

    print("\n========== FIRST TAB ==========")
    driver.get("https://bot.sannysoft.com")
    time.sleep(2)

    # Check if our scripts ran
    check = driver.execute_script(
        """
        return {
            antiDetectApplied: window.__antiDetectApplied || false,
            completeAntiDetectApplied: window.__completeAntiDetectApplied || false,
            pluginsLength: navigator.plugins.length,
            webdriver: navigator.webdriver
        };
    """
    )
    print(f"First tab: {check}")

    print("\n========== SECOND TAB (window.open) ==========")
    driver.execute_script("window.open('https://bot.sannysoft.com', '_blank');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(3)

    # Check if our scripts ran
    check = driver.execute_script(
        """
        return {
            antiDetectApplied: window.__antiDetectApplied || false,
            completeAntiDetectApplied: window.__completeAntiDetectApplied || false,
            pluginsLength: navigator.plugins.length,
            webdriver: navigator.webdriver
        };
    """
    )
    print(f"Second tab: {check}")

    # Try to manually inject and see what happens
    print("\n========== MANUAL INJECTION ON SECOND TAB ==========")
    try:
        # Get the script
        from pathlib import Path

        script_path = Path(__file__).parent / "chrome_manager" / "scripts" / "complete-antidetect.js"
        with script_path.open("r") as f:
            script = f.read()

        # Execute it
        driver.execute_script(script)

        # Check again
        check = driver.execute_script(
            """
            return {
                antiDetectApplied: window.__antiDetectApplied || false,
                completeAntiDetectApplied: window.__completeAntiDetectApplied || false,
                pluginsLength: navigator.plugins.length,
                webdriver: navigator.webdriver
            };
        """
        )
        print(f"After manual injection: {check}")
    except Exception as e:
        print(f"Manual injection failed: {e}")

    await instance.terminate()


asyncio.run(test())
