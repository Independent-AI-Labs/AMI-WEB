"""JavaScript execution tools for Chrome MCP server."""

from typing import Any

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from loguru import logger


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

    return BrowserResponse(success=True, result=result)
