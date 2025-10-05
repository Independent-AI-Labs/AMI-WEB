"""Navigation tools for Chrome MCP server."""

from loguru import logger
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException, WebDriverException

from browser.backend.core.browser.instance import BrowserInstance
from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.navigation.navigator import Navigator
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.utils.exceptions import InstanceError


def _is_fatal_error(exc: Exception) -> bool:
    """Determine if an exception is fatal and requires instance retirement.

    Fatal errors indicate the browser session is dead and cannot be recovered.
    Non-fatal errors (timeouts, network issues, page crashes) should not kill the instance.
    """
    # Session is completely dead - must retire
    if isinstance(exc, InvalidSessionIdException):
        return True

    # Chrome process crashed - must retire
    if isinstance(exc, WebDriverException):
        error_msg = str(exc).lower()
        if any(
            fatal in error_msg
            for fatal in [
                "chrome not reachable",
                "session deleted",
                "session not created",
                "disconnected: not connected to devtools",
                "chrome failed to start",
                "target window already closed",
            ]
        ):
            return True

    # All other errors are potentially recoverable
    return False


async def _acquire_healthy_instance(manager: ChromeManager, instance_id: str | None = None) -> tuple[bool, BrowserInstance | None]:
    """Return a healthy browser instance, optionally provisioning a new one.

    Returns a tuple (from_pool, instance). When from_pool is False we created a
    new session via get_or_create_instance.
    """

    # If specific instance requested, use it
    if instance_id:
        instance = await manager.get_instance(instance_id)
        if instance:
            return True, instance
        logger.warning(f"Requested instance {instance_id} not found")
        return False, None

    # Use current instance context
    instance = await manager.get_current_instance()
    if instance:
        return True, instance

    # Fallback: create new instance
    default_headless = manager.config.get("backend.browser.default_headless", True)
    try:
        instance = await manager.get_or_create_instance(headless=default_headless, use_pool=True)
        manager.set_current_instance(instance.id)
        return False, instance
    except InstanceError as exc:
        logger.error(f"Failed to provision replacement browser instance: {exc}")
        return False, None


async def browser_navigate_tool(
    manager: ChromeManager, url: str, instance_id: str | None = None, wait_for: str | None = None, timeout: float = 30
) -> BrowserResponse:
    """Navigate to a URL."""
    logger.debug(f"Navigating to: {url} with instance_id={instance_id}, wait_for={wait_for}, timeout={timeout}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.navigate(url, wait_for=None, timeout=int(timeout))
    except Exception as exc:
        # Only retire instance on fatal errors (session dead, chrome crashed)
        # Preserve instance and tabs on recoverable errors (timeouts, network issues)
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error during navigation, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Navigation failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to navigate: {exc}")

    return BrowserResponse(success=True, url=url, data={"status": "navigated"})


async def browser_back_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """Navigate back in browser history."""
    logger.debug(f"Navigating back with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.back()
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error navigating back, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Navigate back failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to navigate back: {exc}")

    return BrowserResponse(success=True, data={"status": "navigated_back"})


async def browser_forward_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """Navigate forward in browser history."""
    logger.debug(f"Navigating forward with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.forward()
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error navigating forward, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Navigate forward failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to navigate forward: {exc}")

    return BrowserResponse(success=True, data={"status": "navigated_forward"})


async def browser_refresh_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """Refresh the current page."""
    logger.debug(f"Refreshing page with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    nav = Navigator(instance)
    try:
        await nav.refresh()
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error refreshing page, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Refresh failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to refresh: {exc}")

    return BrowserResponse(success=True, data={"status": "refreshed"})


async def browser_get_url_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """Get the current page URL."""
    logger.debug(f"Getting current URL with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance or not instance.driver:
        if instance and from_pool and _is_fatal_error(Exception("No driver")):
            await manager.retire_instance(instance.id)
        return BrowserResponse(success=False, error="No healthy browser instance available")

    try:
        url = instance.driver.current_url
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error getting URL, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Get URL failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to resolve current URL: {exc}")

    return BrowserResponse(success=True, url=url)


async def browser_open_tab_tool(manager: ChromeManager, url: str | None = None, instance_id: str | None = None) -> BrowserResponse:
    """Open a new tab, optionally navigating to a URL."""
    logger.debug(f"Opening new tab with url={url}, instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance or not instance.driver:
        # No driver is a configuration error, not necessarily fatal
        return BrowserResponse(success=False, error="No healthy browser instance available")

    if not instance._lifecycle.tab_manager:
        # No tab manager is a configuration error, not necessarily fatal
        return BrowserResponse(success=False, error="Tab manager not initialized")

    try:
        tab_handle = instance._lifecycle.tab_manager.open_new_tab(url)
        return BrowserResponse(success=True, data={"tab_id": tab_handle, "url": url})
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error opening tab, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Open tab failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to open new tab: {exc}")


async def browser_list_tabs_tool(manager: ChromeManager, instance_id: str | None = None) -> BrowserResponse:
    """List all open tabs."""
    logger.debug(f"Listing tabs with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    try:
        handles = instance.driver.window_handles
        current = instance.driver.current_window_handle
        tabs = [{"tab_id": h, "is_current": h == current} for h in handles]
        return BrowserResponse(success=True, data={"tabs": tabs, "count": len(tabs)})
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error listing tabs, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"List tabs failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to list tabs: {exc}")


async def browser_switch_tab_tool(manager: ChromeManager, tab_id: str, instance_id: str | None = None) -> BrowserResponse:
    """Switch to a specific tab by handle."""
    logger.debug(f"Switching to tab {tab_id} with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    if not instance._lifecycle.tab_manager:
        return BrowserResponse(success=False, error="Tab manager not initialized")

    try:
        instance._lifecycle.tab_manager.switch_to_tab(tab_id)
        return BrowserResponse(success=True, data={"tab_id": tab_id})
    except NoSuchWindowException as exc:
        # Tab doesn't exist - not a fatal error, just invalid tab_id
        logger.warning(f"Tab {tab_id} not found: {exc}")
        return BrowserResponse(success=False, error=f"Tab not found: {tab_id}")
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error switching tab, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Switch tab failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to switch tab: {exc}")


async def browser_close_tab_tool(manager: ChromeManager, tab_id: str | None = None, instance_id: str | None = None) -> BrowserResponse:
    """Close a tab (current if no tab_id specified)."""
    logger.debug(f"Closing tab {tab_id or 'current'} with instance_id={instance_id}")

    from_pool, instance = await _acquire_healthy_instance(manager, instance_id)
    if not instance or not instance.driver:
        return BrowserResponse(success=False, error="No healthy browser instance available")

    try:
        if tab_id:
            instance.driver.switch_to.window(tab_id)
        instance.driver.close()
        remaining = instance.driver.window_handles
        if remaining:
            instance.driver.switch_to.window(remaining[0])
        return BrowserResponse(success=True, data={"closed_tab": tab_id or "current"})
    except NoSuchWindowException as exc:
        # Tab doesn't exist - not a fatal error
        logger.warning(f"Tab {tab_id} not found when trying to close: {exc}")
        return BrowserResponse(success=False, error=f"Tab not found: {tab_id}")
    except Exception as exc:
        if from_pool and _is_fatal_error(exc):
            logger.error(f"Fatal error closing tab, retiring instance {instance.id}: {exc}")
            await manager.retire_instance(instance.id)
        else:
            logger.warning(f"Close tab failed but instance preserved: {exc}")
        return BrowserResponse(success=False, error=f"Failed to close tab: {exc}")
