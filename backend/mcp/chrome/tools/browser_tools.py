"""Browser lifecycle tools for Chrome MCP server."""

from typing import Any

from browser.backend.core.management.manager import ChromeManager
from loguru import logger


async def browser_launch_tool(
    manager: ChromeManager, headless: bool = False, profile: str | None = None, anti_detect: bool = False, use_pool: bool = True
) -> dict[str, Any]:
    """Launch a new browser instance."""
    logger.debug(f"Launching browser: headless={headless}, profile={profile}, anti_detect={anti_detect}, use_pool={use_pool}")

    try:
        instance = await manager.get_or_create_instance(
            headless=headless,
            profile=profile,
            anti_detect=anti_detect,
            use_pool=use_pool,  # Allow flexibility for testing
        )

        return {"success": True, "instance_id": instance.id, "status": "launched"}
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        return {"success": False, "error": str(e), "status": "failed"}


async def browser_terminate_tool(manager: ChromeManager, instance_id: str) -> dict[str, Any]:
    """Terminate a browser instance."""
    logger.debug(f"Terminating browser instance: {instance_id}")

    await manager.terminate_instance(instance_id)

    return {"success": True, "status": "terminated"}


async def browser_list_tool(manager: ChromeManager) -> dict[str, Any]:
    """List all browser instances."""
    logger.debug("Listing browser instances")

    instances = await manager.list_instances()

    return {"success": True, "instances": [inst.model_dump(mode="json") for inst in instances]}


async def browser_get_active_tool(manager: ChromeManager) -> dict[str, Any]:
    """Get the currently active browser instance."""
    logger.debug("Getting active browser instance")

    # For now, return the first instance if available
    instances = await manager.list_instances()
    active_id = instances[0].id if instances else None

    return {"success": True, "instance_id": active_id}
