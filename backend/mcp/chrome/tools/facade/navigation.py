"""Browser navigation facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.navigation_tools import (
    browser_back_tool,
    browser_close_tab_tool,
    browser_forward_tool,
    browser_get_url_tool,
    browser_list_tabs_tool,
    browser_open_tab_tool,
    browser_refresh_tool,
    browser_switch_tab_tool,
)
from browser.backend.mcp.chrome.tools.navigation_tools import (
    browser_navigate_tool as browser_navigate_impl,
)


async def browser_navigate_tool(  # noqa: PLR0911, C901
    manager: ChromeManager,
    action: Literal["goto", "back", "forward", "refresh", "get_url", "open_tab", "close_tab", "switch_tab", "list_tabs"],
    url: str | None = None,
    wait_for: str | None = None,
    timeout: float = 30,
    tab_id: str | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Navigate pages and manage browser history and tabs.

    Args:
        manager: Chrome manager instance
        action: Action to perform (goto, back, forward, refresh, get_url, open_tab, close_tab, switch_tab, list_tabs)
        url: URL to navigate to (required for goto, optional for open_tab)
        wait_for: CSS selector to wait for after navigation
        timeout: Navigation timeout in seconds
        tab_id: Tab handle ID (required for switch_tab, optional for close_tab)
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_navigate: action={action}, instance_id={instance_id}")

    if action == "goto":
        if not url:
            return BrowserResponse(success=False, error="url required for goto action")
        return await browser_navigate_impl(manager, url, instance_id, wait_for, timeout)

    if action == "back":
        return await browser_back_tool(manager, instance_id)

    if action == "forward":
        return await browser_forward_tool(manager, instance_id)

    if action == "refresh":
        return await browser_refresh_tool(manager, instance_id)

    if action == "get_url":
        return await browser_get_url_tool(manager, instance_id)

    if action == "open_tab":
        return await browser_open_tab_tool(manager, url, instance_id)

    if action == "close_tab":
        return await browser_close_tab_tool(manager, tab_id, instance_id)

    if action == "switch_tab":
        if not tab_id:
            return BrowserResponse(success=False, error="tab_id required for switch_tab action")
        return await browser_switch_tab_tool(manager, tab_id, instance_id)

    if action == "list_tabs":
        return await browser_list_tabs_tool(manager, instance_id)

    return BrowserResponse(success=False, error=f"Unknown action: {action}")  # type: ignore[unreachable]
