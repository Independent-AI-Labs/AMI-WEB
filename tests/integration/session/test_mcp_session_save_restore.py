"""Test that reproduces the MCP session save/restore bug where profile is null."""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager

pytestmark = pytest.mark.xdist_group(name="profile")


@pytest.mark.asyncio
async def test_mcp_profile_not_captured_in_session_save() -> None:
    """Reproduce the bug: MCP launches with profile but saves session with profile: null."""
    # Create test directories
    test_profiles_dir = Path("data/test_profiles_mcp_bug")
    test_sessions_dir = Path("data/test_sessions_mcp_bug")
    test_profiles_dir.mkdir(parents=True, exist_ok=True)
    test_sessions_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = {
        "backend.storage.profiles_dir": str(test_profiles_dir),
        "backend.storage.session_dir": str(test_sessions_dir),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    # Create profile
    profile_name = "default"
    profile_dir = test_profiles_dir / profile_name
    if profile_dir.exists():
        manager.profile_manager.delete_profile(profile_name)
    manager.profile_manager.create_profile(profile_name)

    # REPLICATE MCP BEHAVIOR: Launch with profile
    # MCP calls: browser_session(action="launch", profile="default")
    # Which calls: manager.get_or_create_instance(profile="default")
    instance = await manager.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    # Navigate to example.com
    assert instance.driver is not None
    instance.driver.get("https://example.com/")
    await asyncio.sleep(1)

    # Check what the instance's profile name is
    print(f"DEBUG: instance._profile_name = {instance._profile_name}")

    # REPLICATE MCP BEHAVIOR: Save session WITHOUT profile_override
    # MCP calls: manager.session_manager.save_session(instance, session_name)
    session_id = await manager.session_manager.save_session(instance, "mcp-test-session")

    # Read the saved session to check profile
    import json

    session_file = test_sessions_dir / session_id / "session.json"
    with session_file.open() as f:
        saved_data = json.load(f)

    saved_profile = saved_data.get("profile")
    print(f"DEBUG: saved profile = {saved_profile}")

    # Cleanup
    await manager.terminate_instance(instance.id)
    await manager.shutdown()

    # THE BUG: profile should be "default" but it's null
    assert saved_profile == profile_name, f"BUG: Session saved with profile={saved_profile} instead of {profile_name}!"


@pytest.mark.asyncio
async def test_mcp_session_restore_with_profile_null_fails() -> None:
    """Test that restoring a session with profile: null but profile_override specified fails/produces wrong result."""
    # Create test directories
    test_profiles_dir = Path("data/test_profiles_mcp_restore_bug")
    test_sessions_dir = Path("data/test_sessions_mcp_restore_bug")
    test_profiles_dir.mkdir(parents=True, exist_ok=True)
    test_sessions_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = {
        "backend.storage.profiles_dir": str(test_profiles_dir),
        "backend.storage.session_dir": str(test_sessions_dir),
    }

    # STEP 1: Create a session with profile: null (simulating the bug)
    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    profile_name = "default"
    if profile_name in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile(profile_name)
    manager1.profile_manager.create_profile(profile_name)

    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    test_url = "https://example.com/"
    assert instance1.driver is not None
    instance1.driver.get(test_url)
    await asyncio.sleep(1)

    # Save session WITHOUT profile_override (will capture instance._profile_name)
    session_id = await manager1.session_manager.save_session(instance1, "bug-session")

    await manager1.terminate_instance(instance1.id)
    await manager1.shutdown()

    # STEP 2: Try to restore with profile_override="default"
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    instance2 = await manager2.session_manager.restore_session(
        session_id,
        manager2,
        profile_override=profile_name,
        headless=True,
        kill_orphaned=True,
    )

    await asyncio.sleep(2)

    # Check what URL we're on
    assert instance2.driver is not None
    restored_url = instance2.driver.current_url
    print(f"DEBUG: restored URL = {restored_url}")

    await manager2.terminate_instance(instance2.id)
    await manager2.shutdown()

    # VERIFY: Should be on example.com, not chrome://new-tab-page/
    assert "example.com" in restored_url, f"BUG: Restored to {restored_url} instead of {test_url}!"
    assert "chrome://new-tab-page" not in restored_url, f"BUG: Restored to new tab page instead of {test_url}!"
