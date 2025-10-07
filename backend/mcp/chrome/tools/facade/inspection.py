"""Browser DOM inspection facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.extraction_tools import (
    browser_exists_tool,
    browser_get_attribute_tool,
    browser_get_html_tool,
)


async def browser_inspect_tool(
    manager: ChromeManager,
    action: Literal["get_html", "exists", "get_attribute"],
    selector: str | None = None,
    # get_html action parameters
    max_depth: int | None = None,
    collapse_depth: int | None = None,
    ellipsize_text_after: int | None = None,
    # get_attribute action parameters
    attribute: str | None = None,
) -> BrowserResponse:
    """Inspect DOM structure and element properties.

    Args:
        manager: Chrome manager instance
        action: Action to perform (get_html, exists, get_attribute)
        selector: CSS selector (null = full page for get_html)
        max_depth: Maximum DOM depth to traverse (for get_html)
        collapse_depth: Depth at which to collapse elements (for get_html)
        ellipsize_text_after: Truncate text after N chars (for get_html)
        attribute: Attribute name (required for get_attribute)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_inspect: action={action}")

    match action:
        case "get_html":
            return await browser_get_html_tool(
                manager, selector, max_depth, collapse_depth, ellipsize_text_after
            )
        case "exists":
            if not selector:
                return BrowserResponse(
                    success=False, error="selector required for exists action"
                )
            return await browser_exists_tool(manager, selector)
        case "get_attribute":
            if not selector:
                return BrowserResponse(
                    success=False, error="selector required for get_attribute action"
                )
            if not attribute:
                return BrowserResponse(
                    success=False, error="attribute required for get_attribute action"
                )
            return await browser_get_attribute_tool(manager, selector, attribute)
