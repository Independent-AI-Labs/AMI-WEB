"""Browser navigation facade tool."""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

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


async def _handle_goto(
    manager: ChromeManager, url: str | None, instance_id: str | None, wait_for: str | None, timeout: float, **_kwargs: Any
) -> BrowserResponse:
    """Handle goto action."""
    if not url:
        return BrowserResponse(success=False, error="url required for goto action")
    return await browser_navigate_impl(manager, url, instance_id, wait_for, timeout)


async def _handle_back(manager: ChromeManager, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle back action."""
    return await browser_back_tool(manager, instance_id)


async def _handle_forward(manager: ChromeManager, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle forward action."""
    return await browser_forward_tool(manager, instance_id)


async def _handle_refresh(manager: ChromeManager, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle refresh action."""
    return await browser_refresh_tool(manager, instance_id)


async def _handle_get_url(manager: ChromeManager, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle get_url action."""
    return await browser_get_url_tool(manager, instance_id)


async def _handle_open_tab(manager: ChromeManager, url: str | None, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle open_tab action."""
    return await browser_open_tab_tool(manager, url, instance_id)


async def _handle_close_tab(manager: ChromeManager, tab_id: str | None, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle close_tab action."""
    return await browser_close_tab_tool(manager, tab_id, instance_id)


async def _handle_switch_tab(manager: ChromeManager, tab_id: str | None, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle switch_tab action."""
    if not tab_id:
        return BrowserResponse(success=False, error="tab_id required for switch_tab action")
    return await browser_switch_tab_tool(manager, tab_id, instance_id)


async def _handle_list_tabs(manager: ChromeManager, instance_id: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle list_tabs action."""
    return await browser_list_tabs_tool(manager, instance_id)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[BrowserResponse]]] = {
    "goto": _handle_goto,
    "back": _handle_back,
    "forward": _handle_forward,
    "refresh": _handle_refresh,
    "get_url": _handle_get_url,
    "open_tab": _handle_open_tab,
    "close_tab": _handle_close_tab,
    "switch_tab": _handle_switch_tab,
    "list_tabs": _handle_list_tabs,
}


async def browser_navigate_tool(
    manager: ChromeManager,
    action: Literal[
        "goto",
        "back",
        "forward",
        "refresh",
        "get_url",
        "open_tab",
        "close_tab",
        "switch_tab",
        "list_tabs",
    ],
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

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return BrowserResponse(success=False, error=f"Unknown action: {action}")

    return await handler(
        manager=manager,
        url=url,
        wait_for=wait_for,
        timeout=timeout,
        tab_id=tab_id,
        instance_id=instance_id,
    )
