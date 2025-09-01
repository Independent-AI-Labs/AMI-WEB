"""JavaScript execution tools for Chrome MCP server."""

from typing import Any

from loguru import logger

from backend.core.management.manager import ChromeManager

from ..response import BrowserResponse


async def browser_execute_tool(manager: ChromeManager, script: str, args: list[Any | None] = None) -> BrowserResponse:
    """Execute JavaScript code."""
    logger.debug(f"Executing JavaScript: {script[:100]}...")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    # Execute script
    result = instance.driver.execute_script(script, *(args or []))

    return BrowserResponse(success=True, result=result)


async def browser_evaluate_tool(manager: ChromeManager, expression: str) -> BrowserResponse:
    """Evaluate JavaScript expression."""
    logger.debug(f"Evaluating JavaScript: {expression[:100]}...")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]

    # Evaluate expression (wrap in return to get value)
    script = f"return {expression}"
    result = instance.driver.execute_script(script)

    return BrowserResponse(success=True, result=result)
