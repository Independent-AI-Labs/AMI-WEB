"""JavaScript execution tools for Chrome MCP server."""

from typing import Any

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.utils.limits import (
    ChunkComputationError,
    compute_chunk,
    enforce_text_limit,
)


async def browser_execute_tool(manager: ChromeManager, script: str, args: list[Any | None] | None = None) -> BrowserResponse:
    """Execute JavaScript code."""
    logger.debug(f"Executing JavaScript: {script[:100]}...")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    # Execute script
    result = instance.driver.execute_script(script, *(args or []))

    if isinstance(result, str):
        limited = enforce_text_limit(manager.config, "browser_execute", result)
        return BrowserResponse(
            success=True,
            result=limited.text,
            truncated=limited.truncated,
            returned_bytes=limited.returned_bytes,
            total_bytes_estimate=limited.total_bytes,
        )

    return BrowserResponse(success=True, result=result)


async def browser_evaluate_tool(manager: ChromeManager, expression: str) -> BrowserResponse:
    """Evaluate JavaScript expression."""
    logger.debug(f"Evaluating JavaScript: {expression[:100]}...")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    # Evaluate expression (wrap in return to get value)
    script = f"return {expression}"
    result = instance.driver.execute_script(script)

    if isinstance(result, str):
        limited = enforce_text_limit(manager.config, "browser_evaluate", result)
        return BrowserResponse(
            success=True,
            result=limited.text,
            truncated=limited.truncated,
            returned_bytes=limited.returned_bytes,
            total_bytes_estimate=limited.total_bytes,
        )

    return BrowserResponse(success=True, result=result)


async def browser_execute_chunk_tool(
    manager: ChromeManager,
    script: str,
    offset: int = 0,
    length: int | None = None,
    snapshot_checksum: str | None = None,
    args: list[Any | None] | None = None,
) -> BrowserResponse:
    """Execute JavaScript and stream the string result in deterministic chunks."""

    logger.debug("Executing chunked JavaScript result")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    result = instance.driver.execute_script(script, *(args or []))

    if not isinstance(result, str):
        return BrowserResponse(success=False, error="Chunked execution requires a string result")

    try:
        chunk = compute_chunk(
            manager.config,
            "browser_execute",
            result,
            offset=offset,
            length=length,
            snapshot_checksum=snapshot_checksum,
        )
    except ChunkComputationError as exc:
        return BrowserResponse(success=False, error=str(exc))

    return BrowserResponse(
        success=True,
        result=chunk.text,
        truncated=chunk.next_offset is not None,
        returned_bytes=chunk.returned_bytes,
        total_bytes_estimate=chunk.total_bytes,
        chunk_start=chunk.chunk_start,
        chunk_end=chunk.chunk_end,
        next_offset=chunk.next_offset,
        remaining_bytes=chunk.remaining_bytes,
        snapshot_checksum=chunk.snapshot_checksum,
    )


async def browser_evaluate_chunk_tool(
    manager: ChromeManager,
    expression: str,
    offset: int = 0,
    length: int | None = None,
    snapshot_checksum: str | None = None,
) -> BrowserResponse:
    """Evaluate JavaScript and stream the string result in deterministic chunks."""

    logger.debug("Evaluating chunked JavaScript expression")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance_info = instances[0]
    instance = await manager.get_instance(instance_info.id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="Browser instance not available")

    script = f"return {expression}"
    result = instance.driver.execute_script(script)

    if not isinstance(result, str):
        return BrowserResponse(success=False, error="Chunked evaluation requires a string result")

    try:
        chunk = compute_chunk(
            manager.config,
            "browser_evaluate",
            result,
            offset=offset,
            length=length,
            snapshot_checksum=snapshot_checksum,
        )
    except ChunkComputationError as exc:
        return BrowserResponse(success=False, error=str(exc))

    return BrowserResponse(
        success=True,
        result=chunk.text,
        truncated=chunk.next_offset is not None,
        returned_bytes=chunk.returned_bytes,
        total_bytes_estimate=chunk.total_bytes,
        chunk_start=chunk.chunk_start,
        chunk_end=chunk.chunk_end,
        next_offset=chunk.next_offset,
        remaining_bytes=chunk.remaining_bytes,
        snapshot_checksum=chunk.snapshot_checksum,
    )
