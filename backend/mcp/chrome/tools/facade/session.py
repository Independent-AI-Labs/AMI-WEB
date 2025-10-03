"""Browser session management facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.browser_tools import (
    browser_get_active_tool,
    browser_launch_tool,
    browser_list_tool,
    browser_terminate_tool,
)


async def browser_session_tool(
    manager: ChromeManager,
    action: Literal["launch", "terminate", "list", "get_active"],
    instance_id: str | None = None,
    headless: bool = True,
    profile: str | None = None,
    anti_detect: bool = False,
    use_pool: bool = True,
) -> BrowserResponse:
    """Manage browser instance lifecycle.

    Args:
        manager: Chrome manager instance
        action: Action to perform (launch, terminate, list, get_active)
        instance_id: Browser instance ID (required for terminate)
        headless: Run in headless mode (for launch)
        profile: Profile name (for launch)
        anti_detect: Enable anti-detection (for launch)
        use_pool: Use instance pool (for launch)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_session: action={action}")

    if action == "launch":
        return await browser_launch_tool(manager, headless, profile, anti_detect, use_pool)

    if action == "terminate":
        if not instance_id:
            return BrowserResponse(success=False, error="instance_id required for terminate action")
        return await browser_terminate_tool(manager, instance_id)

    if action == "list":
        return await browser_list_tool(manager)

    return await browser_get_active_tool(manager)
