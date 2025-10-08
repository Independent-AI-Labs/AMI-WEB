"""Browser React interaction facade tool."""

from collections.abc import Awaitable, Callable
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


async def _handle_trigger_handler(
    manager: ChromeManager, selector: str | None, handler_name: str | None, event_data: dict[str, Any] | None, **_kwargs: Any
) -> BrowserResponse:
    """Handle trigger_handler action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for trigger_handler action")
    if not handler_name:
        return BrowserResponse(success=False, error="handler_name required for trigger_handler action")
    return await browser_react_trigger_handler_tool(manager, selector, handler_name, event_data)


async def _handle_get_props(manager: ChromeManager, selector: str | None, max_depth: int, **_kwargs: Any) -> BrowserResponse:
    """Handle get_props action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for get_props action")
    return await browser_react_get_props_tool(manager, selector, max_depth)


async def _handle_get_state(manager: ChromeManager, selector: str | None, max_depth: int, **_kwargs: Any) -> BrowserResponse:
    """Handle get_state action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for get_state action")
    return await browser_react_get_fiber_tree_tool(manager, selector, max_depth)


async def _handle_find_component(manager: ChromeManager, component_name: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle find_component action."""
    if not component_name:
        return BrowserResponse(success=False, error="component_name required for find_component action")
    return await browser_react_find_component_tool(manager, component_name)


async def _handle_get_fiber_tree(manager: ChromeManager, selector: str | None, max_depth: int, **_kwargs: Any) -> BrowserResponse:
    """Handle get_fiber_tree action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for get_fiber_tree action")
    return await browser_react_get_fiber_tree_tool(manager, selector, max_depth)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[BrowserResponse]]] = {
    "trigger_handler": _handle_trigger_handler,
    "get_props": _handle_get_props,
    "get_state": _handle_get_state,
    "find_component": _handle_find_component,
    "get_fiber_tree": _handle_get_fiber_tree,
}


async def browser_react_tool(  # noqa: PLR0913
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

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return BrowserResponse(success=False, error=f"Unknown action: {action}")

    return await handler(
        manager=manager,
        selector=selector,
        handler_name=handler_name,
        event_data=event_data,
        component_name=component_name,
        max_depth=max_depth,
    )
