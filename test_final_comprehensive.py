"""FINAL COMPREHENSIVE TEST OF ALL ANTI-DETECTION FEATURES"""

import asyncio
from chrome_manager.core.manager import ChromeManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

async def test():
    print("\n" + "="*60)
    print("FINAL COMPREHENSIVE ANTI-DETECTION TEST")
    print("="*60)
    
    # Test 1: ChromeManager (MCP style)
    print("\n[TEST 1] ChromeManager with default anti-detect...")
    manager = ChromeManager()
    await manager.initialize()
    
    instance = await manager.get_or_create_instance(
        headless=False,
        use_pool=False
    )
    
    instance.driver.get("https://bot.sannysoft.com")
    wait = WebDriverWait(instance.driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)
    
    critical_tests = {}
    rows = instance.driver.find_elements(By.CSS_SELECTOR, "table tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 2:
            test_name = cells[0].text.strip()
            test_result = cells[1].text.strip()
            
            # Check critical tests
            if "WebDriver Advanced" in test_name:
                critical_tests["WebDriver"] = "PASS" if test_result == "passed" else f"FAIL ({test_result})"
            elif "WebGL Vendor" in test_name:
                critical_tests["WebGL Vendor"] = "PASS" if "Canvas has no webgl" not in test_result else "FAIL (No context)"
            elif "WebGL Renderer" in test_name:
                critical_tests["WebGL Renderer"] = "PASS" if "Canvas has no webgl" not in test_result else "FAIL (No context)"
            elif "Plugins is of type PluginArray" in test_name:
                critical_tests["Plugin Type"] = "PASS" if test_result == "passed" else f"FAIL ({test_result})"
            elif "Plugins Length" in test_name and "Old" in test_name:
                plugin_count = test_result
                critical_tests["Plugin Count"] = "PASS" if plugin_count != "0" else "FAIL (0 plugins)"
    
    print("\nResults:")
    all_pass = True
    for test, result in critical_tests.items():
        print(f"  {test}: {result}")
        if "FAIL" in result:
            all_pass = False
    
    await manager.shutdown()
    
    # Test 2: Direct BrowserInstance
    print("\n[TEST 2] Direct BrowserInstance with anti_detect=True...")
    from chrome_manager.core.instance import BrowserInstance
    from chrome_manager.utils.config import Config
    
    instance2 = BrowserInstance(config=Config())
    driver = await instance2.launch(headless=False, anti_detect=True)
    
    driver.get("https://bot.sannysoft.com")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    time.sleep(2)
    
    # Quick check WebGL
    webgl_check = driver.execute_script("""
        var canvas = document.createElement('canvas');
        var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return 'NO CONTEXT';
        var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (!debugInfo) return 'NO DEBUG';
        return {
            vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
            renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
        };
    """)
    
    print(f"\nWebGL Check: {webgl_check}")
    
    await instance2.terminate()
    
    print("\n" + "="*60)
    if all_pass and isinstance(webgl_check, dict):
        print("✓ ALL ANTI-DETECTION FEATURES WORKING!")
    else:
        print("✗ SOME FEATURES STILL NEED ATTENTION")
    print("="*60)

asyncio.run(test())