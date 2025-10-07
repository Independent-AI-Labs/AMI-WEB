"""Browser JavaScript execution facade tool."""

from typing import Any, Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.javascript_tools import (
    browser_evaluate_chunk_tool,
    browser_evaluate_tool,
    browser_execute_chunk_tool,
)
from browser.backend.mcp.chrome.tools.javascript_tools import (
    browser_execute_tool as browser_execute_impl,
)


async def browser_execute_tool(
    manager: ChromeManager,
    action: Literal["execute", "evaluate"],
    code: str,
    args: list[Any | None] | None = None,
    # Chunking support
    use_chunking: bool = False,
    offset: int = 0,
    length: int | None = None,
    snapshot_checksum: str | None = None,
) -> BrowserResponse:
    """Execute JavaScript code or evaluate expressions.

    Args:
        manager: Chrome manager instance
        action: Action to perform (execute, evaluate)
        code: JavaScript code or expression
        args: Arguments for execute action
        use_chunking: Enable chunked response for large string results
        offset: Byte offset for chunked response
        length: Chunk length in bytes
        snapshot_checksum: Checksum for consistency validation

    Returns:
        BrowserResponse with execution result
    """
    logger.debug(f"browser_execute: action={action}, use_chunking={use_chunking}")

    if action == "execute":
        if use_chunking:
            return await browser_execute_chunk_tool(
                manager, code, offset, length, snapshot_checksum, args
            )
        return await browser_execute_impl(manager, code, args)

    if use_chunking:
        return await browser_evaluate_chunk_tool(
            manager, code, offset, length, snapshot_checksum
        )
    return await browser_evaluate_tool(manager, code)
