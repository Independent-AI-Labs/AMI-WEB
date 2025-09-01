"""Screenshot tools for Chrome MCP server."""

import base64

from loguru import logger

from backend.core.management.manager import ChromeManager

from ..response import BrowserResponse


async def browser_screenshot_tool(manager: ChromeManager, full_page: bool = False) -> BrowserResponse:
    """Take a screenshot of the page."""
    logger.debug(f"Taking screenshot: full_page={full_page}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    # Get screenshot as base64
    # Note: full_page support would require additional implementation
    screenshot_bytes = instance.driver.get_screenshot_as_png()

    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    return BrowserResponse(success=True, screenshot=screenshot_base64, data={"format": "base64"})


async def browser_element_screenshot_tool(manager: ChromeManager, selector: str) -> BrowserResponse:
    """Take a screenshot of an element."""
    logger.debug(f"Taking element screenshot: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    # Find element and take screenshot
    element = instance.driver.find_element_by_css_selector(selector)
    screenshot_bytes = element.screenshot_as_png
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    return BrowserResponse(success=True, screenshot=screenshot_base64, data={"format": "base64"})
