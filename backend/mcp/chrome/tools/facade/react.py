"""Browser React interaction facade tool."""

from typing import Any, Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.react_tools import (
    browser_react_find_component_tool,
    browser_react_get_fiber_tree_tool,
    browser_react_get_props_tool,
    browser_react_trigger_handler_tool,
)


async def browser_react_tool(  # noqa: PLR0913, PLR0911
    manager: ChromeManager,
    action: Literal["trigger_handler", "get_props", "get_state", "find_component", "get_fiber_tree"],
    selector: str | None = None,
    handler_name: str | None = None,
    event_data: dict[str, Any] | None = None,
    component_name: str | None = None,
    max_depth: int = 10,
) -> BrowserResponse:
    """React-specific helpers for triggering handlers and inspecting components.

    Args:
        manager: Chrome manager instance
        action: Action to perform
        selector: CSS selector for target element
        handler_name: React handler name (e.g., "onClick", "onDoubleClick")
        event_data: Optional event data for handler
        component_name: Component name to search for
        max_depth: Maximum fiber tree depth to traverse

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_react: action={action}")

    match action:
        case "trigger_handler":
            if not selector:
                return BrowserResponse(success=False, error="selector required for trigger_handler action")
            if not handler_name:
                return BrowserResponse(
                    success=False,
                    error="handler_name required for trigger_handler action",
                )
            return await browser_react_trigger_handler_tool(manager, selector, handler_name, event_data)
        case "get_props":
            if not selector:
                return BrowserResponse(success=False, error="selector required for get_props action")
            return await browser_react_get_props_tool(manager, selector, max_depth)
        case "get_state":
            if not selector:
                return BrowserResponse(success=False, error="selector required for get_state action")
            return await browser_react_get_fiber_tree_tool(manager, selector, max_depth)
        case "find_component":
            if not component_name:
                return BrowserResponse(
                    success=False,
                    error="component_name required for find_component action",
                )
            return await browser_react_find_component_tool(manager, component_name)
        case "get_fiber_tree":
            if not selector:
                return BrowserResponse(success=False, error="selector required for get_fiber_tree action")
            return await browser_react_get_fiber_tree_tool(manager, selector, max_depth)
