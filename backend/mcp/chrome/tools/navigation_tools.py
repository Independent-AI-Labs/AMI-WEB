"""Navigation tools for Chrome MCP server."""

from typing import Any

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.navigation.navigator import Navigator
from loguru import logger


async def browser_navigate_tool(manager: ChromeManager, url: str, wait_for: str | None = None, timeout: float = 30) -> dict[str, Any]:
    """Navigate to a URL."""
    logger.debug(f"Navigating to: {url} with wait_for={wait_for}, timeout={timeout}")

    # Get current instance
    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]  # Use first available
    nav = Navigator(instance)

    await nav.navigate(url, wait_for=None, timeout=timeout)

    return {"success": True, "status": "navigated", "url": url}


async def browser_back_tool(manager: ChromeManager) -> dict[str, Any]:
    """Navigate back in browser history."""
    logger.debug("Navigating back")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    nav = Navigator(instance)
    await nav.back()

    return {"success": True, "status": "navigated_back"}


async def browser_forward_tool(manager: ChromeManager) -> dict[str, Any]:
    """Navigate forward in browser history."""
    logger.debug("Navigating forward")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    nav = Navigator(instance)
    await nav.forward()

    return {"success": True, "status": "navigated_forward"}


async def browser_refresh_tool(manager: ChromeManager) -> dict[str, Any]:
    """Refresh the current page."""
    logger.debug("Refreshing page")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    nav = Navigator(instance)
    await nav.refresh()

    return {"success": True, "status": "refreshed"}


async def browser_get_url_tool(manager: ChromeManager) -> dict[str, Any]:
    """Get the current page URL."""
    logger.debug("Getting current URL")

    instances = await manager.list_instances()
    if not instances:
        return {"success": False, "error": "No browser instance available"}

    instance = instances[0]
    url = instance.driver.current_url

    return {"success": True, "url": url}
