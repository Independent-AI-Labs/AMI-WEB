"""Simple WebGL test without complex scripts."""

import asyncio
import time

from chrome_manager.core.instance import BrowserInstance


async def main():
    """Test WebGL in anti-detection mode."""
    print("Testing WebGL...")

    instance = BrowserInstance()
    driver = await instance.launch(headless=False, anti_detect=True)

    # Go to bot.sannysoft.com
    driver.get("https://bot.sannysoft.com/")
    time.sleep(3)

    # Just check what the page shows
    print("\nChecking bot.sannysoft.com results...")
    print("Look at the browser window for WebGL Vendor and WebGL Renderer rows")
    print("They should show actual values, not 'Canvas has no webgl context'")

    print("\nPress Enter to continue to Reddit test...")
    input()

    # Test Reddit
    driver.get("https://reddit.com")
    time.sleep(3)

    print("\nCheck if Reddit loads normally without blocking")
    print("Press Enter to close...")
    input()

    await instance.terminate()


if __name__ == "__main__":
    asyncio.run(main())
