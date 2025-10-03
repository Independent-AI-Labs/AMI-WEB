"""Browser navigation facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.navigation_tools import (
    browser_back_tool,
    browser_forward_tool,
    browser_get_url_tool,
    browser_refresh_tool,
)
from browser.backend.mcp.chrome.tools.navigation_tools import (
    browser_navigate_tool as browser_navigate_impl,
)


async def browser_navigate_tool(  # noqa: PLR0911
    manager: ChromeManager,
    action: Literal["goto", "back", "forward", "refresh", "get_url"],
    url: str | None = None,
    wait_for: str | None = None,
    timeout: float = 30,
) -> BrowserResponse:
    """Navigate pages and manage browser history.

    Args:
        manager: Chrome manager instance
        action: Action to perform (goto, back, forward, refresh, get_url)
        url: URL to navigate to (required for goto)
        wait_for: CSS selector to wait for after navigation
        timeout: Navigation timeout in seconds

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_navigate: action={action}")

    if action == "goto":
        if not url:
            return BrowserResponse(success=False, error="url required for goto action")
        return await browser_navigate_impl(manager, url, wait_for, timeout)

    if action == "back":
        return await browser_back_tool(manager)

    if action == "forward":
        return await browser_forward_tool(manager)

    if action == "refresh":
        return await browser_refresh_tool(manager)

    return await browser_get_url_tool(manager)
