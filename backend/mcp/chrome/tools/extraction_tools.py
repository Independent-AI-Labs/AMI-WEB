"""Content extraction tools for Chrome MCP server."""

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from backend.core.management.manager import ChromeManager
from backend.facade.navigation.extractor import ContentExtractor

from ..response import BrowserResponse


async def browser_get_text_tool(manager: ChromeManager, selector: str) -> BrowserResponse:
    """Get text content of an element."""
    logger.debug(f"Getting text from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    extractor = ContentExtractor(instance)

    text = await extractor.get_text(selector)

    return BrowserResponse(success=True, text=text)


async def browser_get_attribute_tool(manager: ChromeManager, selector: str, attribute: str) -> BrowserResponse:
    """Get attribute value of an element."""
    logger.debug(f"Getting attribute {attribute} from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    element = instance.driver.find_element_by_css_selector(selector)
    value = element.get_attribute(attribute)

    return BrowserResponse(success=True, data={"value": value})


async def browser_exists_tool(manager: ChromeManager, selector: str) -> BrowserResponse:
    """Check if an element exists."""
    logger.debug(f"Checking if element exists: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    try:
        instance.driver.find_element_by_css_selector(selector)
        exists = True
    except Exception:
        exists = False

    return BrowserResponse(success=True, data={"exists": exists})


async def browser_wait_for_tool(manager: ChromeManager, selector: str, state: str = "visible", timeout: float = 30) -> BrowserResponse:
    """Wait for an element to appear."""
    logger.debug(f"Waiting for element: {selector} to be {state}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    # Simplified wait implementation

    wait = WebDriverWait(instance.driver, timeout)

    if state == "visible":
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    elif state == "present":
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        return BrowserResponse(success=False, error=f"Unknown state: {state}")

    return BrowserResponse(success=True, data={"status": "element_found"})


async def browser_get_cookies_tool(manager: ChromeManager) -> BrowserResponse:
    """Get browser cookies."""
    logger.debug("Getting browser cookies")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    cookies = instance.driver.get_cookies()

    return BrowserResponse(success=True, cookies=cookies)
