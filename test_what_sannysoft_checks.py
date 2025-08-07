import asyncio
from chrome_manager.core.instance import BrowserInstance
from chrome_manager.utils.config import Config
from selenium.webdriver.common.by import By

async def test():
    instance = BrowserInstance(config=Config())
    driver = await instance.launch(headless=False, anti_detect=True)
    
    # Navigate to bot.sannysoft.com
    driver.get("https://bot.sannysoft.com")
    await asyncio.sleep(3)
    
    # Find the WebDriver test row and get the actual test result
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            if "WebDriver" in test_name and "(New)" in test_name:
                test_result = cells[1].text.strip()
                cell_class = cells[1].get_attribute("class")
                print(f"WebDriver (New) test result text: '{test_result}'")
                print(f"WebDriver (New) test result class: '{cell_class}'")
                
                # Get the actual JavaScript being tested
                script_result = driver.execute_script("""
                    return {
                        webdriver: navigator.webdriver,
                        webdriverType: typeof navigator.webdriver,
                        hasWebdriver: 'webdriver' in navigator,
                        descriptor: Object.getOwnPropertyDescriptor(navigator, 'webdriver')
                    }
                """)
                print(f"Actual navigator.webdriver state: {script_result}")
                break
    
    await instance.terminate()

asyncio.run(test())