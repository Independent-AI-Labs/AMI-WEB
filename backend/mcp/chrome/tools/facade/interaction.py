"""Browser interaction facade tool."""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.extraction_tools import browser_wait_for_tool
from browser.backend.mcp.chrome.tools.input_tools import (
    browser_click_tool,
    browser_hover_tool,
    browser_press_tool,
    browser_scroll_tool,
    browser_select_tool,
    browser_type_tool,
)


async def _handle_click(manager: ChromeManager, selector: str | None, button: str, click_count: int, **_kwargs: Any) -> BrowserResponse:
    """Handle click action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for click action")
    return await browser_click_tool(manager, selector, button, click_count)


async def _handle_type(manager: ChromeManager, selector: str | None, text: str | None, clear: bool, delay: float, **_kwargs: Any) -> BrowserResponse:
    """Handle type action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for type action")
    if text is None:
        return BrowserResponse(success=False, error="text required for type action")
    return await browser_type_tool(manager, selector, text, clear, delay)


async def _handle_select(
    manager: ChromeManager, selector: str | None, value: str | None, index: int | None, label: str | None, **_kwargs: Any
) -> BrowserResponse:
    """Handle select action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for select action")
    return await browser_select_tool(manager, selector, value, index, label)


async def _handle_hover(manager: ChromeManager, selector: str | None, **_kwargs: Any) -> BrowserResponse:
    """Handle hover action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for hover action")
    return await browser_hover_tool(manager, selector)


async def _handle_scroll(manager: ChromeManager, direction: str, amount: int, **_kwargs: Any) -> BrowserResponse:
    """Handle scroll action."""
    return await browser_scroll_tool(manager, direction, amount)


async def _handle_press(manager: ChromeManager, key: str | None, modifiers: list[str | None] | None, **_kwargs: Any) -> BrowserResponse:
    """Handle press action."""
    if not key:
        return BrowserResponse(success=False, error="key required for press action")
    return await browser_press_tool(manager, key, modifiers)


async def _handle_wait(manager: ChromeManager, selector: str | None, state: str, timeout: float, **_kwargs: Any) -> BrowserResponse:
    """Handle wait action."""
    if not selector:
        return BrowserResponse(success=False, error="selector required for wait action")
    return await browser_wait_for_tool(manager, selector, state, timeout)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[BrowserResponse]]] = {
    "click": _handle_click,
    "type": _handle_type,
    "select": _handle_select,
    "hover": _handle_hover,
    "scroll": _handle_scroll,
    "press": _handle_press,
    "wait": _handle_wait,
}


async def browser_interact_tool(  # noqa: PLR0913
    manager: ChromeManager,
    action: Literal["click", "type", "select", "hover", "scroll", "press", "wait"],
    selector: str | None = None,
    # Type action parameters
    text: str | None = None,
    clear: bool = False,
    delay: float = 0,
    # Click action parameters
    button: str = "left",
    click_count: int = 1,
    # Select action parameters
    value: str | None = None,
    index: int | None = None,
    label: str | None = None,
    # Scroll action parameters
    direction: str = "down",
    amount: int = 100,
    # Press action parameters
    key: str | None = None,
    modifiers: list[str | None] | None = None,
    # Wait action parameters
    state: str = "visible",
    timeout: float = 30,
) -> BrowserResponse:
    """Interact with page elements.

    Args:
        manager: Chrome manager instance
        action: Action to perform
        selector: CSS selector for target element
        text: Text to type (for type action)
        clear: Clear field before typing (for type action)
        delay: Typing delay in seconds (for type action)
        button: Mouse button (for click action)
        click_count: Number of clicks (for click action)
        value: Option value (for select action)
        index: Option index (for select action)
        label: Option label (for select action)
        direction: Scroll direction (for scroll action)
        amount: Scroll amount in pixels (for scroll action)
        key: Key to press (for press action)
        modifiers: Modifier keys (for press action)
        state: Element state to wait for (for wait action)
        timeout: Timeout in seconds (for wait action)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_interact: action={action}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return BrowserResponse(success=False, error=f"Unknown action: {action}")

    return await handler(
        manager=manager,
        selector=selector,
        text=text,
        clear=clear,
        delay=delay,
        button=button,
        click_count=click_count,
        value=value,
        index=index,
        label=label,
        direction=direction,
        amount=amount,
        key=key,
        modifiers=modifiers,
        state=state,
        timeout=timeout,
    )
