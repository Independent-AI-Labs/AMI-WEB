"""Content extraction tools for Chrome MCP server."""

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.navigation.extractor import ContentExtractor
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.utils import ChunkComputationError, compute_chunk, enforce_text_limit


async def browser_get_text_tool(manager: ChromeManager, selector: str) -> BrowserResponse:
    """Get text content of an element."""
    logger.debug(f"Getting text from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance:
        return BrowserResponse(success=False, error="Browser instance not available")

    extractor = ContentExtractor(instance)
    text = await extractor.get_element_text(selector)

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
) -> BrowserResponse:
    """Stream text content of an element in deterministic chunks."""

    logger.debug(f"Chunking text from element: {selector} offset={offset} length={length}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance:
        return BrowserResponse(success=False, error="Browser instance not available")

    extractor = ContentExtractor(instance)
    text = await extractor.get_element_text(selector)

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


async def browser_get_attribute_tool(manager: ChromeManager, selector: str, attribute: str) -> BrowserResponse:
    """Get attribute value of an element."""
    logger.debug(f"Getting attribute {attribute} from element: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    element = instance.driver.find_element(By.CSS_SELECTOR, selector)
    value = element.get_attribute(attribute)

    return BrowserResponse(success=True, data={"value": value})


async def browser_exists_tool(manager: ChromeManager, selector: str) -> BrowserResponse:
    """Check if an element exists."""
    logger.debug(f"Checking if element exists: {selector}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    try:
        instance.driver.find_element(By.CSS_SELECTOR, selector)
        exists = True
    except Exception:
        exists = False

    return BrowserResponse(success=True, data={"exists": exists})


async def browser_wait_for_tool(manager: ChromeManager, selector: str, state: str = "visible", timeout: float = 30) -> BrowserResponse:
    """Wait for an element to appear."""
    logger.debug(f"Waiting for element: {selector} to be {state}")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
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


async def browser_get_cookies_tool(manager: ChromeManager) -> BrowserResponse:
    """Get browser cookies."""
    logger.debug("Getting browser cookies")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    cookies = instance.driver.get_cookies()

    return BrowserResponse(success=True, cookies=cookies)
