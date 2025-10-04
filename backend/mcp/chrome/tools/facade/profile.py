"""Browser profile management facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse


async def _create_profile(manager: ChromeManager, profile_name: str | None, description: str | None) -> BrowserResponse:
    """Create a new browser profile."""
    if not profile_name:
        return BrowserResponse(success=False, error="profile_name required for create action")

    try:
        # Ensure manager is initialized
        if not manager._initialized:
            await manager.initialize()

        profile_dir = manager.profile_manager.create_profile(profile_name, description or "")
        return BrowserResponse(
            success=True,
            data={
                "name": profile_name,
                "path": str(profile_dir),
                "description": description or "",
                "message": f"Profile '{profile_name}' created successfully",
            },
        )
    except Exception as e:
        logger.error(f"Failed to create profile: {e}")
        return BrowserResponse(success=False, error=f"Failed to create profile: {e}")


async def _delete_profile(manager: ChromeManager, profile_name: str | None) -> BrowserResponse:
    """Delete a browser profile."""
    if not profile_name:
        return BrowserResponse(success=False, error="profile_name required for delete action")

    try:
        # Ensure manager is initialized
        if not manager._initialized:
            await manager.initialize()

        deleted = manager.profile_manager.delete_profile(profile_name)
        if deleted:
            return BrowserResponse(
                success=True,
                data={"name": profile_name, "message": f"Profile '{profile_name}' deleted successfully"},
            )
        return BrowserResponse(success=False, error=f"Profile '{profile_name}' not found")
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        return BrowserResponse(success=False, error=f"Failed to delete profile: {e}")


async def _list_profiles(manager: ChromeManager) -> BrowserResponse:
    """List all browser profiles."""
    try:
        # Ensure manager is initialized
        if not manager._initialized:
            await manager.initialize()

        profiles = manager.profile_manager.list_profiles()
        return BrowserResponse(
            success=True,
            data={"profiles": profiles, "count": len(profiles)},
        )
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        return BrowserResponse(success=False, error=f"Failed to list profiles: {e}")


async def _copy_profile(manager: ChromeManager, source_profile: str | None, dest_profile: str | None) -> BrowserResponse:
    """Copy a browser profile."""
    if not source_profile:
        return BrowserResponse(success=False, error="source_profile required for copy action")
    if not dest_profile:
        return BrowserResponse(success=False, error="dest_profile required for copy action")

    try:
        # Ensure manager is initialized
        if not manager._initialized:
            await manager.initialize()

        dest_dir = manager.profile_manager.copy_profile(source_profile, dest_profile)
        return BrowserResponse(
            success=True,
            data={
                "source": source_profile,
                "dest": dest_profile,
                "path": str(dest_dir),
                "message": f"Profile '{source_profile}' copied to '{dest_profile}' successfully",
            },
        )
    except Exception as e:
        logger.error(f"Failed to copy profile: {e}")
        return BrowserResponse(success=False, error=f"Failed to copy profile: {e}")


async def browser_profile_tool(
    manager: ChromeManager,
    action: Literal["create", "delete", "list", "copy"],
    profile_name: str | None = None,
    description: str | None = None,
    source_profile: str | None = None,
    dest_profile: str | None = None,
) -> BrowserResponse:
    """Manage browser profiles.

    Args:
        manager: Chrome manager instance
        action: Action to perform (create, delete, list, copy)
        profile_name: Profile name (required for create, delete)
        description: Profile description (optional for create)
        source_profile: Source profile name (required for copy)
        dest_profile: Destination profile name (required for copy)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_profile: action={action}, profile_name={profile_name}")

    action_handlers = {
        "create": lambda: _create_profile(manager, profile_name, description),
        "delete": lambda: _delete_profile(manager, profile_name),
        "list": lambda: _list_profiles(manager),
        "copy": lambda: _copy_profile(manager, source_profile, dest_profile),
    }

    handler = action_handlers.get(action)
    if handler:
        return await handler()

    return BrowserResponse(success=False, error=f"Unknown action: {action}")
