"""Test TabManager for second tab anti-detection."""

import asyncio
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.core.tab_manager import TabManager
from chrome_manager.utils.config import Config


async def test():
    print("\n========== TAB MANAGER TEST ==========")

    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)

    # Create tab manager
    tab_manager = TabManager(driver)

    print("\n[FIRST TAB]")
    driver.get("https://bot.sannysoft.com")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)

    # Check critical tests
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            if any(k in test_name for k in ["WebDriver Advanced", "Plugins is of type", "WebGL Vendor"]):
                status = "PASS" if test_result in ["passed", "OK"] or "Google" in test_result else f"FAIL ({test_result})"
                print(f"  {test_name}: {status}")

    print("\n[SECOND TAB - Using TabManager]")
    # Use TabManager to open new tab
    tab_manager.open_new_tab("https://bot.sannysoft.com")

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)

    # Check critical tests on second tab
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            if any(k in test_name for k in ["WebDriver Advanced", "Plugins is of type", "WebGL Vendor", "VIDEO_CODECS"]):
                status = "PASS" if test_result in ["passed", "OK", "probably"] or "Google" in test_result else f"FAIL ({test_result})"
                print(f"  {test_name}: {status}")

    await instance.terminate()
    print("\n========== TEST COMPLETE ==========")


asyncio.run(test())
