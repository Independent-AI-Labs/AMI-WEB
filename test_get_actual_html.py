"""GET THE ACTUAL FUCKING HTML FROM BOT.SANNYSOFT.COM"""

import asyncio
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.utils.config import Config


async def test():
    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)

    print("\n========== FIRST TAB ==========")
    driver.get("https://bot.sannysoft.com")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(3)

    # Get the ACTUAL HTML of the results table
    table_html = driver.find_element(By.TAG_NAME, "table").get_attribute("innerHTML")
    print("FIRST TAB TABLE HTML:")
    print(table_html[:2000])  # First 2000 chars

    print("\n========== SECOND TAB (window.open) ==========")
    # Open new tab the problematic way
    driver.execute_script("window.open('https://bot.sannysoft.com', '_blank');")
    driver.switch_to.window(driver.window_handles[1])

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(3)

    # Get the ACTUAL HTML of the results table
    table_html = driver.find_element(By.TAG_NAME, "table").get_attribute("innerHTML")
    print("SECOND TAB TABLE HTML:")
    print(table_html[:2000])  # First 2000 chars

    await instance.terminate()


asyncio.run(test())
