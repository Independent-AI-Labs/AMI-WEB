"""Simple test for enhanced anti-detection."""

import asyncio

from chrome_manager.core.instance import BrowserInstance


async def test_simple():
    """Test browser with enhanced anti-detection."""
    print("Testing enhanced anti-detection mode...")

    instance = BrowserInstance()

    try:
        # Launch with anti-detection enabled
        driver = await instance.launch(headless=False, anti_detect=True)

        # Go directly to test sites
        print("\nTesting on bot detection sites...")

        # Test bot.sannysoft.com
        print("\n1. Testing bot.sannysoft.com...")
        driver.get("https://bot.sannysoft.com/")
        await asyncio.sleep(5)

        # Test Reddit
        print("\n2. Testing Reddit...")
        driver.get("https://reddit.com")
        await asyncio.sleep(5)

        print("\nCheck the browser windows to see detection results.")
        print("Press Enter to close...")
        input()

    finally:
        await instance.terminate()


if __name__ == "__main__":
    asyncio.run(test_simple())
