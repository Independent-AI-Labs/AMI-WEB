"""Browser content extraction facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.extraction_tools import (
    browser_get_cookies_tool,
    browser_get_text_chunk_tool,
    browser_get_text_tool,
)


async def browser_extract_tool(  # noqa: PLR0913
    manager: ChromeManager,
    action: Literal["get_text", "get_cookies"],
    selector: str | None = None,
    # Chunking support
    use_chunking: bool = False,
    offset: int = 0,
    length: int | None = None,
    snapshot_checksum: str | None = None,
    # Text extraction parameters
    ellipsize_text_after: int = 128,
    include_tag_names: bool = True,
    skip_hidden: bool = True,
    max_depth: int | None = None,
) -> BrowserResponse:
    """Extract text content and cookies from pages.

    Args:
        manager: Chrome manager instance
        action: Action to perform (get_text, get_cookies)
        selector: CSS selector (null = full page for get_text)
        use_chunking: Enable chunked response for large text
        offset: Byte offset for chunked response
        length: Chunk length in bytes
        snapshot_checksum: Checksum for consistency validation
        ellipsize_text_after: Truncate each element's text after N chars (get_text)
        include_tag_names: Prefix text with element tag names (get_text)
        skip_hidden: Skip hidden/invisible elements (get_text)
        max_depth: Maximum DOM depth to traverse (get_text)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_extract: action={action}, use_chunking={use_chunking}")

    if action == "get_text":
        if not selector:
            return BrowserResponse(success=False, error="selector required for get_text action")

        if use_chunking:
            return await browser_get_text_chunk_tool(
                manager, selector, offset, length, snapshot_checksum, ellipsize_text_after, include_tag_names, skip_hidden, max_depth
            )
        return await browser_get_text_tool(manager, selector, ellipsize_text_after, include_tag_names, skip_hidden, max_depth)

    return await browser_get_cookies_tool(manager)
