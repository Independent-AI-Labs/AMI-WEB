"""Navigation tools for Chrome MCP server."""

from loguru import logger

from backend.core.management.manager import ChromeManager
from backend.facade.navigation.navigator import Navigator

from ..response import BrowserResponse


async def browser_navigate_tool(manager: ChromeManager, url: str, wait_for: str | None = None, timeout: float = 30) -> BrowserResponse:
    """Navigate to a URL."""
    logger.debug(f"Navigating to: {url} with wait_for={wait_for}, timeout={timeout}")

    # Get current instance
    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]  # Use first available
    nav = Navigator(instance)

    await nav.navigate(url, wait_for=None, timeout=timeout)

    return BrowserResponse(success=True, url=url, data={"status": "navigated"})


async def browser_back_tool(manager: ChromeManager) -> BrowserResponse:
    """Navigate back in browser history."""
    logger.debug("Navigating back")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    nav = Navigator(instance)
    await nav.back()

    return BrowserResponse(success=True, data={"status": "navigated_back"})


async def browser_forward_tool(manager: ChromeManager) -> BrowserResponse:
    """Navigate forward in browser history."""
    logger.debug("Navigating forward")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    nav = Navigator(instance)
    await nav.forward()

    return BrowserResponse(success=True, data={"status": "navigated_forward"})


async def browser_refresh_tool(manager: ChromeManager) -> BrowserResponse:
    """Refresh the current page."""
    logger.debug("Refreshing page")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    nav = Navigator(instance)
    await nav.refresh()

    return BrowserResponse(success=True, data={"status": "refreshed"})


async def browser_get_url_tool(manager: ChromeManager) -> BrowserResponse:
    """Get the current page URL."""
    logger.debug("Getting current URL")

    instances = await manager.list_instances()
    if not instances:
        return BrowserResponse(success=False, error="No browser instance available")

    instance = instances[0]
    url = instance.driver.current_url

    return BrowserResponse(success=True, url=url)
