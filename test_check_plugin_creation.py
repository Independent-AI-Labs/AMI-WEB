"""Check if plugins are being created."""

import asyncio
import time

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.utils.config import Config


async def test():
    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)

    # Navigate to a blank page first
    driver.get("about:blank")
    time.sleep(1)

    # Check if plugins exist BEFORE navigating
    check = driver.execute_script(
        """
        return {
            pluginsLength: navigator.plugins.length,
            pluginsType: Object.prototype.toString.call(navigator.plugins),
            hasPlugin0: navigator.plugins[0] ? navigator.plugins[0].name : 'none',
            completeAntiDetectApplied: window.__completeAntiDetectApplied || false
        };
    """
    )
    print(f"Before navigation: {check}")

    # Now navigate
    driver.get("https://bot.sannysoft.com")
    time.sleep(2)

    # Check again
    check = driver.execute_script(
        """
        return {
            pluginsLength: navigator.plugins.length,
            pluginsType: Object.prototype.toString.call(navigator.plugins),
            hasPlugin0: navigator.plugins[0] ? navigator.plugins[0].name : 'none',
            completeAntiDetectApplied: window.__completeAntiDetectApplied || false
        };
    """
    )
    print(f"After navigation: {check}")

    await instance.terminate()


asyncio.run(test())
