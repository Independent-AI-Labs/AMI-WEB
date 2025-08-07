"""Check for script errors."""

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

    # Try to manually inject and check for errors
    from pathlib import Path

    script_path = Path(__file__).parent / "chrome_manager" / "scripts" / "complete-antidetect.js"
    with script_path.open("r") as f:
        script = f.read()

    # Execute and catch any errors
    try:
        result = driver.execute_script(script + "; return 'SUCCESS';")
        print(f"Script executed: {result}")
    except Exception as e:
        print(f"Script error: {e}")

    # Check if plugins exist now
    check = driver.execute_script(
        """
        return {
            pluginsLength: navigator.plugins.length,
            pluginsType: Object.prototype.toString.call(navigator.plugins),
            hasPlugin0: navigator.plugins[0] ? navigator.plugins[0].name : 'none',
            completeAntiDetectApplied: window.__completeAntiDetectApplied || false,
            error: window.__scriptError || null
        };
    """
    )
    print(f"After manual injection: {check}")

    await instance.terminate()


asyncio.run(test())
