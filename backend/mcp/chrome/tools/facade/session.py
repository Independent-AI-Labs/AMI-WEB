"""Browser session management facade tool."""

from typing import Literal

from loguru import logger

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.response import BrowserResponse
from browser.backend.mcp.chrome.tools.browser_tools import (
    browser_get_active_tool,
    browser_launch_tool,
    browser_list_tool,
    browser_terminate_tool,
)


async def _terminate_with_autosave(manager: ChromeManager, instance_id: str | None, session_name: str | None) -> BrowserResponse:
    """Terminate instance with automatic session save."""
    if not instance_id:
        return BrowserResponse(success=False, error="instance_id required for terminate action")

    instance = await manager.get_instance(instance_id)
    if not instance:
        return BrowserResponse(success=False, error=f"Instance {instance_id} not found")

    try:
        auto_name = session_name or f"autosave_{instance_id[:8]}"
        saved_id = await manager.session_manager.save_session(instance, auto_name)
        await browser_terminate_tool(manager, instance_id)
        return BrowserResponse(
            success=True,
            data={
                "status": "terminated",
                "session_id": saved_id,
                "message": f"Instance terminated and session saved as {saved_id}",
            },
        )
    except Exception as e:
        logger.error(f"Failed to save session during terminate: {e}")
        await browser_terminate_tool(manager, instance_id)
        return BrowserResponse(
            success=True,
            data={
                "status": "terminated",
                "session_id": None,
                "message": f"Instance terminated but session save failed: {e}",
            },
        )


async def _save_session(manager: ChromeManager, instance_id: str | None, session_name: str | None, profile: str | None) -> BrowserResponse:
    """Save browser session."""
    if not instance_id:
        return BrowserResponse(success=False, error="instance_id required for save action")

    instance = await manager.get_instance(instance_id)
    if not instance:
        return BrowserResponse(success=False, error=f"Instance {instance_id} not found")

    try:
        saved_id = await manager.session_manager.save_session(instance, session_name, profile_override=profile)
        return BrowserResponse(
            success=True,
            data={"session_id": saved_id, "message": f"Session saved as {saved_id}"},
        )
    except Exception as e:
        logger.error(f"Failed to save session: {e}")
        return BrowserResponse(success=False, error=f"Failed to save session: {e}")


async def _restore_session(
    manager: ChromeManager,
    session_id: str | None,
    profile: str | None,
    headless: bool | None,
    kill_orphaned: bool,
) -> BrowserResponse:
    """Restore browser session."""
    if not session_id:
        return BrowserResponse(success=False, error="session_id required for restore action")

    try:
        # Ensure manager is initialized so session metadata is loaded
        if not manager._initialized:
            await manager.initialize()

        instance = await manager.session_manager.restore_session(
            session_id,
            manager,
            profile_override=profile,
            headless=headless,
            kill_orphaned=kill_orphaned,
        )

        # Set as current instance so subsequent tool calls use this instance
        manager.set_current_instance(instance.id)

        return BrowserResponse(
            success=True,
            data={
                "instance_id": instance.id,
                "session_id": session_id,
                "message": f"Session {session_id} restored",
            },
        )
    except Exception as e:
        logger.error(f"Failed to restore session: {e}")
        return BrowserResponse(success=False, error=f"Failed to restore session: {e}")


async def _list_sessions(manager: ChromeManager) -> BrowserResponse:
    """List all saved sessions."""
    try:
        # Ensure manager is initialized so session metadata is loaded
        if not manager._initialized:
            await manager.initialize()

        sessions = await manager.session_manager.list_sessions()
        return BrowserResponse(
            success=True,
            data={"sessions": sessions, "count": len(sessions)},
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return BrowserResponse(success=False, error=f"Failed to list sessions: {e}")


async def _delete_session(manager: ChromeManager, session_id: str | None) -> BrowserResponse:
    """Delete a saved session."""
    if not session_id:
        return BrowserResponse(success=False, error="session_id required for delete_session action")

    try:
        # Ensure manager is initialized so session metadata is loaded
        if not manager._initialized:
            await manager.initialize()

        deleted = manager.session_manager.delete_session(session_id)
        if deleted:
            return BrowserResponse(
                success=True,
                data={"session_id": session_id, "message": f"Session {session_id} deleted"},
            )
        return BrowserResponse(success=False, error=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        return BrowserResponse(success=False, error=f"Failed to delete session: {e}")


async def _rename_session(manager: ChromeManager, session_id: str | None, session_name: str | None) -> BrowserResponse:
    """Rename a saved session."""
    if not session_id:
        return BrowserResponse(success=False, error="session_id required for rename_session action")
    if not session_name:
        return BrowserResponse(success=False, error="session_name required for rename_session action")

    try:
        # Ensure manager is initialized so session metadata is loaded
        if not manager._initialized:
            await manager.initialize()

        renamed = manager.rename_session(session_id, session_name)
        if renamed:
            return BrowserResponse(
                success=True,
                data={"session_id": session_id, "name": session_name, "message": f"Session {session_id} renamed to '{session_name}'"},
            )
        return BrowserResponse(success=False, error=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Failed to rename session: {e}")
        return BrowserResponse(success=False, error=f"Failed to rename session: {e}")


async def browser_session_tool(
    manager: ChromeManager,
    action: Literal["launch", "terminate", "list", "get_active", "save", "restore", "list_sessions", "delete_session", "rename_session"],
    instance_id: str | None = None,
    headless: bool = True,
    profile: str | None = None,
    anti_detect: bool | None = None,
    use_pool: bool = True,
    session_id: str | None = None,
    session_name: str | None = None,
    kill_orphaned: bool = False,
) -> BrowserResponse:
    """Manage browser instance lifecycle and session persistence.

    Args:
        manager: Chrome manager instance
        action: Action to perform
        instance_id: Browser instance ID (required for terminate, save)
        headless: Run in headless mode (for launch)
        profile: Profile name (for launch and restore - overrides saved profile)
        anti_detect: Enable anti-detection (for launch)
        use_pool: Use instance pool (for launch)
        session_id: Session ID (required for restore, delete_session)
        session_name: Session name (optional for save)

    Returns:
        BrowserResponse with action-specific data
    """
    logger.debug(f"browser_session: action={action}")

    # Instance lifecycle actions (no params needed)
    if action in ("launch", "list", "get_active"):
        if action == "launch":
            return await browser_launch_tool(manager, headless, profile, anti_detect, use_pool)
        return await browser_list_tool(manager) if action == "list" else await browser_get_active_tool(manager)

    # Instance-based actions (require instance_id)
    if action in ("terminate", "save"):
        if action == "terminate":
            return await _terminate_with_autosave(manager, instance_id, session_name)
        return await _save_session(manager, instance_id, session_name, profile)

    # Session-based actions (require session_id)
    action_handlers = {
        "list_sessions": lambda: _list_sessions(manager),
        "restore": lambda: _restore_session(manager, session_id, profile, headless, kill_orphaned),
        "delete_session": lambda: _delete_session(manager, session_id),
        "rename_session": lambda: _rename_session(manager, session_id, session_name),
    }

    handler = action_handlers.get(action)
    if handler:
        return await handler()

    return BrowserResponse(success=False, error=f"Unknown action: {action}")
