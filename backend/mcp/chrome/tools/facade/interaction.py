"""Browser interaction facade tool."""

from typing import Literal

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


async def browser_interact_tool(  # noqa: PLR0913, PLR0911, C901
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

    if action == "click":
        if not selector:
            return BrowserResponse(success=False, error="selector required for click action")
        return await browser_click_tool(manager, selector, button, click_count)

    if action == "type":
        if not selector:
            return BrowserResponse(success=False, error="selector required for type action")
        if text is None:
            return BrowserResponse(success=False, error="text required for type action")
        return await browser_type_tool(manager, selector, text, clear, delay)

    if action == "select":
        if not selector:
            return BrowserResponse(success=False, error="selector required for select action")
        return await browser_select_tool(manager, selector, value, index, label)

    if action == "hover":
        if not selector:
            return BrowserResponse(success=False, error="selector required for hover action")
        return await browser_hover_tool(manager, selector)

    if action == "scroll":
        return await browser_scroll_tool(manager, direction, amount)

    if action == "press":
        if not key:
            return BrowserResponse(success=False, error="key required for press action")
        return await browser_press_tool(manager, key, modifiers)

    if not selector:
        return BrowserResponse(success=False, error="selector required for wait action")
    return await browser_wait_for_tool(manager, selector, state, timeout)
