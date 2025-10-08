"""Test that replicates the ACTUAL issue: saving a session with a real website loaded.

This test navigates to actual websites (like the user does with docs),
saves the session, and verifies the ACTUAL URL is captured - not New Tab.
"""

import asyncio
import json
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager

pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")


@pytest.mark.asyncio
async def test_save_session_captures_actual_loaded_url(worker_data_dirs: dict[str, Path]) -> None:
    """Test that when we navigate to a real URL and save, it captures that URL - not New Tab."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    # Create profile
    profile_name = "real-url-profile"
    profile_dir = worker_data_dirs["profiles_dir"] / profile_name
    if profile_dir.exists():
        manager.profile_manager.delete_profile(profile_name)
    manager.profile_manager.create_profile(profile_name)

    # Create instance
    instance = await manager.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    # REPRODUCE THE BUG: Browser starts with new tab page, then we navigate
    # This simulates what happens when user launches browser and clicks through UI

    # First, let the browser settle with its initial tab
    await asyncio.sleep(0.5)
    assert instance.driver is not None
    initial_handles = instance.driver.window_handles
    print(f"DEBUG: Browser started with {len(initial_handles)} tabs")
    for i, handle in enumerate(initial_handles):
        instance.driver.switch_to.window(handle)
        print(f"DEBUG: Initial tab {i}: {instance.driver.current_url}")

    # Now open a NEW TAB and navigate to our test URL (simulates clicking "open" in UI)
    instance.driver.execute_script("window.open('');")
    await asyncio.sleep(0.5)

    # Switch to the new tab and navigate to example.com
    all_handles = instance.driver.window_handles
    instance.driver.switch_to.window(all_handles[-1])  # Switch to newly opened tab
    test_url = "https://example.com/"
    instance.driver.get(test_url)
    await asyncio.sleep(1)  # Wait for page to load

    # Now we have TWO tabs: one with chrome://new-tab-page and one with example.com
    print(f"DEBUG: After navigation, found {len(all_handles)} tabs:")
    for i, handle in enumerate(all_handles):
        instance.driver.switch_to.window(handle)
        print(f"DEBUG: Tab {i}: {instance.driver.current_url} - '{instance.driver.title}'")

    # Make sure we're on the example.com tab
    instance.driver.switch_to.window(all_handles[-1])
    current_url_before_save = instance.driver.current_url
    current_handle_before_save = instance.driver.current_window_handle

    print(f"DEBUG: Active tab before save: {current_url_before_save}")
    print(f"DEBUG: Active handle before save: {current_handle_before_save}")

    assert test_url in current_url_before_save, f"Browser should be on {test_url} before save, got {current_url_before_save}"

    # Save the session
    session_id = await manager.session_manager.save_session(instance, "real-url-test")

    # Read the saved session file to check what was captured
    session_file = worker_data_dirs["sessions_dir"] / session_id / "session.json"
    with session_file.open() as f:
        saved_data = json.load(f)

    saved_url = saved_data.get("url")
    saved_tabs = saved_data.get("tabs", [])
    active_tab_handle = saved_data.get("active_tab_handle")

    print(f"DEBUG: Saved URL: {saved_url}")
    print(f"DEBUG: Active handle before save: {current_handle_before_save}")
    print(f"DEBUG: Saved active handle: {active_tab_handle}")
    print(f"DEBUG: Saved tabs: {json.dumps(saved_tabs, indent=2)}")

    # Clean up
    await manager.terminate_instance(instance.id)
    await manager.shutdown()

    # THIS IS THE ACTUAL BUG - the saved URL is chrome://new-tab-page/ instead of the real URL
    assert saved_url is not None, "Saved URL should not be None"
    assert "chrome://new-tab-page" not in saved_url, (
        f"BUG: Session saved chrome://new-tab-page instead of actual URL! "
        f"Browser was on {current_url_before_save} but session saved {saved_url}. "
        f"Window handles: {len(all_handles)}, Active handle: {current_handle_before_save}"
    )
    assert test_url in saved_url, f"BUG: Session did not save the actual URL! " f"Browser was on {current_url_before_save} but session saved {saved_url}"

    # Verify the active tab handle matches what we had
    assert active_tab_handle == str(current_handle_before_save), (
        f"BUG: Active tab handle mismatch! " f"Current was {current_handle_before_save} but saved {active_tab_handle}"
    )

    # Also check tabs array - find the tab with our URL
    matching_tabs = [tab for tab in saved_tabs if test_url in tab["url"]]
    assert len(matching_tabs) >= 1, f"BUG: No tab with {test_url} found in saved tabs! " f"Saved tabs: {[tab['url'] for tab in saved_tabs]}"

    # The saved primary URL should match the active tab
    active_tab = next((tab for tab in saved_tabs if tab["handle"] == active_tab_handle), None)
    assert active_tab is not None, f"BUG: Active tab handle {active_tab_handle} not found in saved tabs!"
    assert test_url in active_tab["url"], f"BUG: Active tab has wrong URL! Expected {test_url}, got {active_tab['url']}"


@pytest.mark.asyncio
async def test_save_session_when_tab_focus_was_switched_by_browser(worker_data_dirs: dict[str, Path]) -> None:
    """Test bug where browser switches focus to different tab before session save.

    This reproduces the ACTUAL bug: user is on localhost:3000, but some browser behavior
    (like opening a link in background, or extension, or timing) causes Chrome to switch
    the active tab to chrome://new-tab-page before we call save_session.
    """
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    profile_name = "focus-switch-profile"
    if profile_name in manager.profile_manager.profiles:
        manager.profile_manager.delete_profile(profile_name)
    manager.profile_manager.create_profile(profile_name)

    instance = await manager.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    # Simulate: User navigates to example.com in a new tab
    assert instance.driver is not None
    instance.driver.execute_script("window.open('');")
    await asyncio.sleep(0.5)
    all_handles = instance.driver.window_handles
    instance.driver.switch_to.window(all_handles[-1])

    test_url = "https://example.com/"
    instance.driver.get(test_url)
    await asyncio.sleep(1)

    # User sees example.com in their browser
    user_visible_url = instance.driver.current_url
    user_visible_handle = instance.driver.current_window_handle
    print(f"DEBUG: User sees: {user_visible_url}")
    assert test_url in user_visible_url

    # BUG SCENARIO: Something causes Chrome to switch focus back to first tab
    # (could be browser behavior, extension, timing issue, etc.)
    instance.driver.switch_to.window(all_handles[0])

    # Now driver is focused on chrome://new-tab-page but USER thinks they're on example.com
    actual_focused_url = instance.driver.current_url
    actual_focused_handle = instance.driver.current_window_handle
    print(f"DEBUG: Chrome actually focused on: {actual_focused_url}")
    print(f"DEBUG: User expects to save: {user_visible_url}")
    print(f"DEBUG: But current_window_handle is: {actual_focused_handle}")

    # NOW we save the session (like MCP browser_session save action does)
    session_id = await manager.session_manager.save_session(instance, "focus-switch-test")

    # Check what was saved
    session_file = worker_data_dirs["sessions_dir"] / session_id / "session.json"
    with session_file.open() as f:
        saved_data = json.load(f)

    saved_url = saved_data.get("url")
    saved_tabs = saved_data.get("tabs", [])
    saved_active_handle = saved_data.get("active_tab_handle")

    print(f"DEBUG: Saved URL: {saved_url}")
    print(f"DEBUG: Saved active handle: {saved_active_handle}")
    print(f"DEBUG: Saved tabs: {json.dumps(saved_tabs, indent=2)}")

    # Clean up
    await manager.terminate_instance(instance.id)
    await manager.shutdown()

    # THESE ASSERTIONS SHOULD PASS WHEN THE BUG IS FIXED
    # Currently they will FAIL because the bug exists

    # BUG: Session saves whatever tab Chrome has focused, not what user was viewing
    assert "chrome://new-tab-page" not in saved_url, (
        f"BUG: Session saved chrome://new-tab-page instead of user's actual tab! " f"User was viewing {user_visible_url} but session saved {saved_url}"
    )

    assert test_url in saved_url, f"BUG: Session should save the URL user was viewing ({user_visible_url}), " f"but saved {saved_url}"

    assert saved_active_handle == str(user_visible_handle), (
        f"BUG: Saved wrong active tab! User was on handle {user_visible_handle}, " f"but session saved handle {saved_active_handle} as active"
    )

    # The session should capture BOTH tabs
    assert len(saved_tabs) == 2, f"Should have saved 2 tabs, got {len(saved_tabs)}"

    # And mark the CORRECT one (example.com) as active
    active_tab = next((t for t in saved_tabs if t["handle"] == saved_active_handle), None)
    assert active_tab is not None
    assert test_url in active_tab["url"], f"BUG: Active tab should be {test_url}, got {active_tab['url']}"


@pytest.mark.asyncio
async def test_multiple_real_websites_session_save_and_restore(worker_data_dirs: dict[str, Path]) -> None:
    """Test that saving a session with MULTIPLE real websites captures ALL tabs correctly."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Create fresh profile
    profile_name = "multi-real-website-profile"
    profile_dir = worker_data_dirs["profiles_dir"] / profile_name
    if profile_dir.exists():
        manager1.profile_manager.delete_profile(profile_name)
    manager1.profile_manager.create_profile(profile_name)

    # Launch browser with profile
    instance1 = await manager1.get_or_create_instance(profile=profile_name, headless=True, use_pool=False)

    # Tab 1: example.com
    assert instance1.driver is not None
    # Set page load timeout to 30 seconds
    instance1.driver.set_page_load_timeout(30)
    instance1.driver.get("https://example.com")
    await asyncio.sleep(2)
    tab1_title = instance1.driver.title

    # Tab 2: example.org (more reliable than httpbin.org)
    instance1.driver.execute_script("window.open('');")
    instance1.driver.switch_to.window(instance1.driver.window_handles[1])
    instance1.driver.get("https://example.org")
    await asyncio.sleep(2)
    tab2_title = instance1.driver.title

    # Switch back to first tab before saving
    instance1.driver.switch_to.window(instance1.driver.window_handles[0])

    # Save session
    session_id = await manager1.session_manager.save_session(instance1, "multi-real-website-session")

    # Terminate first instance
    await manager1.terminate_instance(instance1.id)
    await manager1.shutdown()

    # Create new manager and restore session
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    # Restore session WITH EXPLICIT PROFILE (same as save)
    instance2 = await manager2.session_manager.restore_session(
        session_id,
        manager2,
        profile_override=profile_name,
        headless=True,
        kill_orphaned=True,
    )
    manager2.set_current_instance(instance2.id)

    # VERIFY: The restored session has ALL tabs with CORRECT URLs
    await asyncio.sleep(2)  # Wait for pages to load

    assert instance2.driver is not None
    assert len(instance2.driver.window_handles) == 2, f"BUG: Expected 2 tabs, got {len(instance2.driver.window_handles)}"

    # Check first tab
    instance2.driver.switch_to.window(instance2.driver.window_handles[0])
    restored_tab1_url = instance2.driver.current_url
    restored_tab1_title = instance2.driver.title

    # Check second tab
    instance2.driver.switch_to.window(instance2.driver.window_handles[1])
    restored_tab2_url = instance2.driver.current_url
    restored_tab2_title = instance2.driver.title

    # Cleanup
    await manager2.terminate_instance(instance2.id)
    await manager2.shutdown()

    # Assertions for tab 1
    assert "example.com" in restored_tab1_url.lower(), f"BUG: Tab 1 URL is '{restored_tab1_url}' instead of example.com"
    assert tab1_title == restored_tab1_title, "BUG: Tab 1 title mismatch"

    # Assertions for tab 2
    assert "example.org" in restored_tab2_url.lower(), f"BUG: Tab 2 URL is '{restored_tab2_url}' instead of example.org"
    assert tab2_title == restored_tab2_title, "BUG: Tab 2 title mismatch"
