"""Test that MCP server uses anti-detection by default."""

import asyncio
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from chrome_manager.core.manager import ChromeManager


async def test():
    print("Testing MCP ChromeManager with anti-detect...")

    # Create ChromeManager like MCP does
    manager = ChromeManager()
    await manager.initialize()

    # Get instance WITHOUT explicitly passing anti_detect (should be True by default now)
    instance = await manager.get_or_create_instance(
        headless=False,
        use_pool=False,  # Don't use pool for direct testing
    )

    print("Browser launched via ChromeManager")

    # Navigate to bot.sannysoft.com
    instance.driver.get("https://bot.sannysoft.com")

    wait = WebDriverWait(instance.driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(3)

    # Check WebGL and other critical tests
    rows = instance.driver.find_elements(By.CSS_SELECTOR, "table tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            if any(keyword in test_name for keyword in ["WebGL", "WebDriver", "Plugins"]):
                status = "[PASS]" if test_result not in ["failed", "FAIL", "WARN", "missing"] else "[FAIL]"
                if "Canvas has no webgl context" not in test_result:
                    print(f"{status} {test_name}: {test_result}")
                else:
                    print(f"[FAIL] {test_name}: NO WEBGL CONTEXT!")

    await manager.shutdown()
    print("\nMCP ChromeManager test complete")


asyncio.run(test())
