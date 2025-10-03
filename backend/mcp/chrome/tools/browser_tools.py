"""Browser lifecycle tools for Chrome MCP server."""

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse


async def browser_launch_tool(
    manager: ChromeManager, headless: bool = False, profile: str | None = None, anti_detect: bool = False, use_pool: bool = True
) -> BrowserResponse:
    """Launch a new browser instance."""
    logger.debug(f"Launching browser: headless={headless}, profile={profile}, anti_detect={anti_detect}, use_pool={use_pool}")
    logger.debug("Browser launch initiated")

    try:
        # Ensure manager is initialized
        if not manager._initialized:
            logger.debug("Initializing manager...")
            await manager.initialize()
            logger.debug("Manager initialized")

        logger.debug("Getting or creating instance...")
        instance = await manager.get_or_create_instance(
            headless=headless,
            profile=profile,
            anti_detect=anti_detect,
            use_pool=use_pool,  # Allow flexibility for testing
        )
        logger.debug(f"Got instance: {instance.id}")

        logger.debug("Creating response...")
        response = BrowserResponse(success=True, instance_id=instance.id, data={"status": "launched"})
        logger.debug(f"Response created: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}", exc_info=True)
        return BrowserResponse(success=False, error=str(e), data={"status": "failed"})


async def browser_terminate_tool(manager: ChromeManager, instance_id: str) -> BrowserResponse:
    """Terminate a browser instance."""
    logger.debug(f"Terminating browser instance: {instance_id}")

    await manager.terminate_instance(instance_id)

    return BrowserResponse(success=True, data={"status": "terminated"})


async def browser_list_tool(manager: ChromeManager) -> BrowserResponse:
    """List all browser instances."""
    logger.debug("Listing browser instances")

    instances = await manager.list_instances()

    return BrowserResponse(success=True, data={"instances": [inst.model_dump(mode="json") for inst in instances]})


async def browser_get_active_tool(manager: ChromeManager) -> BrowserResponse:
    """Get the currently active browser instance."""
    logger.debug("Getting active browser instance")

    # For now, return the first instance if available
    instances = await manager.list_instances()
    active_id = instances[0].id if instances else None

    return BrowserResponse(success=True, instance_id=active_id)
