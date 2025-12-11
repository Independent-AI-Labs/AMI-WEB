"""Content extraction tools for Chrome MCP server."""

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.controllers.navigation.extractor import ContentExtractor
from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.utils.limits import (
    ChunkComputationError,
    compute_chunk,
    enforce_text_limit,
)


async def browser_get_text_tool(
    manager: ChromeManager,
    selector: str,
    ellipsize_text_after: int = 128,
    include_tag_names: bool = True,
    skip_hidden: bool = True,
    max_depth: int | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get text content of an element with tags and auto-ellipsization."""
    logger.debug(
        f"Getting text from element: {selector}, ellipsize_after={ellipsize_text_after}, "
        f"include_tags={include_tag_names}, skip_hidden={skip_hidden}, instance_id={instance_id}"
    )

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    extractor = ContentExtractor(instance)
    text = await extractor.get_text_with_tags(
        selector=selector,
        ellipsize_text_after=ellipsize_text_after,
        include_tag_names=include_tag_names,
        skip_hidden=skip_hidden,
        max_depth=max_depth,
    )

    limited = enforce_text_limit(manager.config, "browser_get_text", text)

    return BrowserResponse(
        success=True,
        text=limited.text,
        truncated=limited.truncated,
        returned_bytes=limited.returned_bytes,
        total_bytes_estimate=limited.total_bytes,
    )


async def browser_get_text_chunk_tool(
    manager: ChromeManager,
    selector: str,
    offset: int = 0,
    length: int | None = None,
    snapshot_checksum: str | None = None,
    ellipsize_text_after: int = 128,
    include_tag_names: bool = True,
    skip_hidden: bool = True,
    max_depth: int | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Stream text content of an element in deterministic chunks."""

    logger.debug(f"Chunking text from element: {selector} offset={offset} length={length}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    extractor = ContentExtractor(instance)
    text = await extractor.get_text_with_tags(
        selector=selector,
        ellipsize_text_after=ellipsize_text_after,
        include_tag_names=include_tag_names,
        skip_hidden=skip_hidden,
        max_depth=max_depth,
    )

    try:
        chunk = compute_chunk(
            manager.config,
            "browser_get_text",
            text,
            offset=offset,
            length=length,
            snapshot_checksum=snapshot_checksum,
        )
    except ChunkComputationError as exc:
        return BrowserResponse(success=False, error=str(exc))

    return BrowserResponse(
        success=True,
        text=chunk.text,
        truncated=chunk.next_offset is not None,
        returned_bytes=chunk.returned_bytes,
        total_bytes_estimate=chunk.total_bytes,
        chunk_start=chunk.chunk_start,
        chunk_end=chunk.chunk_end,
        next_offset=chunk.next_offset,
        remaining_bytes=chunk.remaining_bytes,
        snapshot_checksum=chunk.snapshot_checksum,
    )


async def browser_get_attribute_tool(
    manager: ChromeManager,
    selector: str,
    attribute: str,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get attribute value of an element."""
    logger.debug(f"Getting attribute {attribute} from element: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    element = instance.driver.find_element(By.CSS_SELECTOR, selector)
    value = element.get_attribute(attribute)

    return BrowserResponse(success=True, data={"value": value})


async def browser_exists_tool(manager: ChromeManager, selector: str, instance_id: str | None = None) -> BrowserResponse:
    """Check if an element exists."""
    logger.debug(f"Checking if element exists: {selector}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    try:
        instance.driver.find_element(By.CSS_SELECTOR, selector)
        exists = True
    except Exception:
        exists = False

    return BrowserResponse(success=True, data={"exists": exists})


async def browser_wait_for_tool(
    manager: ChromeManager,
    selector: str,
    state: str = "visible",
    timeout: float = 30,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Wait for an element to appear."""
    logger.debug(f"Waiting for element: {selector} to be {state}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    # Simplified wait implementation
    wait = WebDriverWait(instance.driver, int(timeout))

    if state == "visible":
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    elif state == "present":
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        return BrowserResponse(success=False, error=f"Unknown state: {state}")

    return BrowserResponse(success=True, data={"status": "element_found"})


async def browser_get_cookies_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """Get browser cookies."""
    logger.debug(f"Getting browser cookies, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    cookies = instance.driver.get_cookies()

    return BrowserResponse(success=True, cookies=cookies)


async def browser_get_html_tool(
    manager: ChromeManager,
    selector: str | None = None,
    max_depth: int | None = None,
    collapse_depth: int | None = None,
    ellipsize_text_after: int | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    """Get HTML with depth limiting and text ellipsization.

    Args:
        manager: Chrome manager instance
        selector: CSS selector for specific element (recommended for large pages)
        max_depth: Maximum DOM depth to traverse
        collapse_depth: Depth at which to collapse elements to summaries
        ellipsize_text_after: Truncate text content after this many chars (from config if not provided)
        instance_id: Optional instance ID to target

    Returns:
        BrowserResponse with HTML content
    """
    logger.debug(f"Getting HTML: selector={selector}, max_depth={max_depth}, collapse_depth={collapse_depth}, instance_id={instance_id}")

    instance = await manager.get_instance_or_current(instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No browser instance available")

    extractor = ContentExtractor(instance)

    # Get ellipsize_text_after from config if not provided
    if ellipsize_text_after is None:
        ellipsize_text_after = manager.config.get("mcp.tool_limits.browser_get_html.ellipsize_text_after", 128)

    # Get HTML based on selector or full page
    if selector:
        # Specific element requested
        html = await extractor.get_element_html(selector)
        # Apply ellipsization to element HTML
        if ellipsize_text_after:
            html = await extractor.get_html_with_depth_limit(
                max_depth=max_depth,
                collapse_depth=collapse_depth,
                ellipsize_text_after=ellipsize_text_after,
            )
    else:
        # Full page with depth/collapse/ellipsize options
        html = await extractor.get_html_with_depth_limit(
            max_depth=max_depth,
            collapse_depth=collapse_depth,
            ellipsize_text_after=ellipsize_text_after,
        )

    # Enforce response limits
    limited = enforce_text_limit(manager.config, "browser_get_html", html)

    return BrowserResponse(
        success=True,
        text=limited.text,
        truncated=limited.truncated,
        returned_bytes=limited.returned_bytes,
        total_bytes_estimate=limited.total_bytes,
    )
