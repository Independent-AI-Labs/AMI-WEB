"""Navigation tools for Chrome MCP server."""

from loguru import logger

from browser.backend.core.browser.instance import BrowserInstance
from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.navigation.navigator import Navigator
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.utils.exceptions import InstanceError


async def _acquire_healthy_instance(manager: ChromeManager) -> tuple[bool, BrowserInstance | None]:
    """Return a healthy browser instance, optionally provisioning a new one.

    Returns a tuple (from_pool, instance). When from_pool is False we created a
    new session via get_or_create_instance.
    """

    instances = await manager.list_instances()
    for info in instances:
        instance = await manager.get_instance(info.id)
        if instance:
            return True, instance

    default_headless = manager.config.get("backend.browser.default_headless", True)
    try:
        instance = await manager.get_or_create_instance(headless=default_headless, use_pool=True)
        return False, instance
    except InstanceError as exc:
        logger.error(f"Failed to provision replacement browser instance: {exc}")
        return False, None


async def browser_navigate_tool(manager: ChromeManager, url: str, wait_for: str | None = None, timeout: float = 30) -> BrowserResponse:
    """Navigate to a URL."""
    logger.debug(f"Navigating to: {url} with wait_for={wait_for}, timeout={timeout}")

    from_pool, instance = await _acquire_healthy_instance(manager)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.navigate(url, wait_for=None, timeout=int(timeout))
    except Exception as exc:
        if from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error=f"Failed to navigate: {exc}")

    return BrowserResponse(success=True, url=url, data={"status": "navigated"})


async def browser_back_tool(manager: ChromeManager) -> BrowserResponse:
    """Navigate back in browser history."""
    logger.debug("Navigating back")

    from_pool, instance = await _acquire_healthy_instance(manager)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.back()
    except Exception as exc:
        if from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error=f"Failed to navigate back: {exc}")

    return BrowserResponse(success=True, data={"status": "navigated_back"})


async def browser_forward_tool(manager: ChromeManager) -> BrowserResponse:
    """Navigate forward in browser history."""
    logger.debug("Navigating forward")

    from_pool, instance = await _acquire_healthy_instance(manager)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.forward()
    except Exception as exc:
        if from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error=f"Failed to navigate forward: {exc}")

    return BrowserResponse(success=True, data={"status": "navigated_forward"})


async def browser_refresh_tool(manager: ChromeManager) -> BrowserResponse:
    """Refresh the current page."""
    logger.debug("Refreshing page")

    from_pool, instance = await _acquire_healthy_instance(manager)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.refresh()
    except Exception as exc:
        if from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error=f"Failed to refresh: {exc}")

    return BrowserResponse(success=True, data={"status": "refreshed"})


async def browser_get_url_tool(manager: ChromeManager) -> BrowserResponse:
    """Get the current page URL."""
    logger.debug("Getting current URL")

    from_pool, instance = await _acquire_healthy_instance(manager)
    if not instance or not instance.driver:
        if instance and from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error="No healthy browser instance available")

    try:
        url = instance.driver.current_url
    except Exception as exc:
        if from_pool:
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error=f"Failed to resolve current URL: {exc}")

    return BrowserResponse(success=True, url=url)
