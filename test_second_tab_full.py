"""Test EVERYTHING on second tab."""

import asyncio
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.core.tab_manager import TabManager
from chrome_manager.utils.config import Config


async def test():
    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)

    tab_manager = TabManager(driver)

    print("\n========== FIRST TAB ==========")
    driver.get("https://bot.sannysoft.com")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)

    # Get ALL test results
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    first_tab_fails = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            if test_result in ["failed", "FAIL", "WARN"]:
                first_tab_fails.append(f"{test_name}: {test_result}")
                print(f"[FAIL] {test_name}: {test_result}")

    if not first_tab_fails:
        print("ALL TESTS PASSING!")

    print("\n========== SECOND TAB ==========")
    # Open new tab with TabManager
    tab_manager.open_new_tab("https://bot.sannysoft.com")

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)

    # Get ALL test results
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    second_tab_fails = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            if test_result in ["failed", "FAIL", "WARN"]:
                second_tab_fails.append(f"{test_name}: {test_result}")
                print(f"[FAIL] {test_name}: {test_result}")

    if not second_tab_fails:
        print("ALL TESTS PASSING!")

    # Check webdriver directly
    print("\n========== DIRECT CHECKS ==========")
    wd_check = driver.execute_script("return navigator.webdriver")
    print(f"navigator.webdriver on tab 2: {wd_check}")

    await instance.terminate()


asyncio.run(test())
