"""Browser visual capture facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.screenshot_tools import (
    browser_element_screenshot_tool,
    browser_screenshot_tool,
)


async def browser_capture_tool(
    manager: ChromeManager,
    action: Literal["screenshot", "element_screenshot"],
    selector: str | None = None,
    full_page: bool = False,
    save_to_disk: bool = True,
) -> BrowserResponse:
    """Capture screenshots of page or elements.

    Args:
        manager: Chrome manager instance
        action: Action to perform (screenshot, element_screenshot)
        selector: CSS selector (required for element_screenshot)
        full_page: Capture full page (for screenshot)
        save_to_disk: Save screenshot to disk instead of returning base64

    Returns:
        BrowserResponse with base64 encoded screenshot or file path
    """
    logger.debug(f"browser_capture: action={action}, save_to_disk={save_to_disk}")

    if action == "screenshot":
        return await browser_screenshot_tool(manager, full_page, save_to_disk)

    if not selector:
        return BrowserResponse(
            success=False, error="selector required for element_screenshot action"
        )
    return await browser_element_screenshot_tool(manager, selector, save_to_disk)
