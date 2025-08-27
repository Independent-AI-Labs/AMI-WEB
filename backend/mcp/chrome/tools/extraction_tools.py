"""Content extraction tools for Chrome MCP server."""

from typing import Any

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.navigation.extractor import ContentExtractor
from loguru import logger


async def browser_get_text_tool(manager: ChromeManager, selector: str) -> dict[str, Any]:
    """Get text content of an element."""
    logger.debug(f"Getting text from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    extractor = ContentExtractor(instance)

    text = await extractor.get_text(selector)

    return {"success": True, "text": text}


async def browser_get_attribute_tool(manager: ChromeManager, selector: str, attribute: str) -> dict[str, Any]:
    """Get attribute value of an element."""
    logger.debug(f"Getting attribute {attribute} from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    element = instance.driver.find_element_by_css_selector(selector)
    value = element.get_attribute(attribute)

    return {"success": True, "value": value}


async def browser_exists_tool(manager: ChromeManager, selector: str) -> dict[str, Any]:
    """Check if an element exists."""
    logger.debug(f"Checking if element exists: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]

    try:
        instance.driver.find_element_by_css_selector(selector)
        exists = True
    except Exception:
        exists = False

    return {"success": True, "exists": exists}


async def browser_wait_for_tool(manager: ChromeManager, selector: str, state: str = "visible", timeout: float = 30) -> dict[str, Any]:
    """Wait for an element to appear."""
    logger.debug(f"Waiting for element: {selector} to be {state}")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]

    # Simplified wait implementation
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(instance.driver, timeout)

    if state == "visible":
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    elif state == "present":
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        return {"success": False, "error": f"Unknown state: {state}"}

    return {"success": True, "status": "element_found"}


async def browser_get_cookies_tool(manager: ChromeManager) -> dict[str, Any]:
    """Get browser cookies."""
    logger.debug("Getting browser cookies")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    cookies = instance.driver.get_cookies()

    return {"success": True, "cookies": cookies}
