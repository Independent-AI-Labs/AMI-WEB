"""Test anti-detection mode."""

import asyncio

from chrome_manager.core.instance import BrowserInstance


async def test_antidetect():
    """Test browser with anti-detection enabled."""
    print("Testing anti-detection mode...")

    # Create instance with anti-detection
    instance = BrowserInstance()

    try:
        # Launch with anti-detection enabled
        driver = await instance.launch(headless=False, anti_detect=True)

        # Navigate to bot detection test sites
        test_sites = [
            "https://bot.sannysoft.com/",  # General bot detection test
            "https://arh.antoinevastel.com/bots/areyouheadless",  # Headless detection
        ]

        for site in test_sites:
            print(f"\nTesting {site}...")
            driver.get(site)
            await asyncio.sleep(3)

            # Check for common detection markers
            webdriver_check = driver.execute_script("return navigator.webdriver")
            print(f"  navigator.webdriver: {webdriver_check}")

            # Check Chrome object
            chrome_check = driver.execute_script("return typeof window.chrome")
            print(f"  window.chrome: {chrome_check}")

            # Check plugins
            plugins_check = driver.execute_script("return navigator.plugins.length")
            print(f"  navigator.plugins.length: {plugins_check}")

            # Check languages
            languages_check = driver.execute_script("return navigator.languages")
            print(f"  navigator.languages: {languages_check}")

        print("\nAnti-detection test completed!")
        print("Press Enter to close the browser...")
        input()

    finally:
        await instance.terminate()


if __name__ == "__main__":
    asyncio.run(test_antidetect())
