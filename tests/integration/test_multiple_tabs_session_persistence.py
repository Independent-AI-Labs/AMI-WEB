"""Test that demonstrates session persistence fails with multiple tabs.

This test proves that the session save/restore logic does NOT properly persist
multiple tabs - it only saves the current tab's URL and restores to a single tab.
"""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_multiple_tabs_are_not_persisted() -> None:
    """Demonstrate that multiple tabs are NOT saved and restored properly."""

    # Create test directories
    test_profiles_dir = Path("data/test_profiles_multi_tab")
    test_sessions_dir = Path("data/test_sessions_multi_tab")
    test_profiles_dir.mkdir(parents=True, exist_ok=True)
    test_sessions_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = {
        "backend.storage.profiles_dir": str(test_profiles_dir),
        "backend.storage.session_dir": str(test_sessions_dir),
    }

    # STEP 1: Create manager and instance with multiple tabs
    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    # Delete and recreate profile
    profile_name = "multi-tab-profile"
    profile_dir = test_profiles_dir / profile_name
    if profile_dir.exists():
        manager1.profile_manager.delete_profile(profile_name)
    manager1.profile_manager.create_profile(profile_name)

    # Create instance
    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    # Open multiple tabs with different URLs
    test_urls = [
        "https://example.com/",
        "https://example.org/",
        "https://example.net/",
    ]

    # Tab 1: Navigate to first URL (existing tab)
    assert instance1.driver is not None
    instance1.driver.get(test_urls[0])
    await asyncio.sleep(0.5)

    # Tab 2: Open new tab and navigate
    instance1.driver.execute_script("window.open('');")
    instance1.driver.switch_to.window(instance1.driver.window_handles[1])
    instance1.driver.get(test_urls[1])
    await asyncio.sleep(0.5)

    # Tab 3: Open another tab and navigate
    instance1.driver.execute_script("window.open('');")
    instance1.driver.switch_to.window(instance1.driver.window_handles[2])
    instance1.driver.get(test_urls[2])
    await asyncio.sleep(0.5)

    # Switch back to tab 2 (middle tab) to make it the active tab
    instance1.driver.switch_to.window(instance1.driver.window_handles[1])

    # Verify we have 3 tabs before saving
    tabs_before_save = len(instance1.driver.window_handles)
    assert tabs_before_save == 3, f"Should have 3 tabs before save, got {tabs_before_save}"

    # Verify current tab is tab 2
    current_url_before = instance1.driver.current_url
    current_handle_before = instance1.driver.current_window_handle
    assert test_urls[1] in current_url_before, f"Current tab should be {test_urls[1]}, got {current_url_before}"

    print(f"DEBUG: Before save - Active tab: {current_url_before}")
    print(f"DEBUG: Before save - Active handle: {current_handle_before}")

    # STEP 2: Save the session
    session_id = await manager1.session_manager.save_session(instance1, "multi-tab-test")
    print(f"✓ Saved session {session_id} with {tabs_before_save} tabs")

    # VERIFY: Read saved session to check what was actually captured
    session_file = test_sessions_dir / session_id / "session.json"
    with session_file.open() as f:
        import json

        saved_data = json.load(f)

    saved_tabs = saved_data.get("tabs", [])
    saved_active_handle = saved_data.get("active_tab_handle")
    saved_url = saved_data.get("url")

    print(f"DEBUG: Saved {len(saved_tabs)} tabs")
    print(f"DEBUG: Saved active handle: {saved_active_handle}")
    print(f"DEBUG: Saved primary URL: {saved_url}")
    for i, tab in enumerate(saved_tabs):
        print(f"DEBUG: Saved tab {i}: {tab['url']}")

    # CRITICAL: Verify the saved session has the correct active tab
    assert len(saved_tabs) == 3, f"BUG: Saved {len(saved_tabs)} tabs instead of 3!"
    assert saved_active_handle == str(current_handle_before), f"BUG: Saved wrong active tab! Expected handle {current_handle_before}, got {saved_active_handle}"
    assert test_urls[1] in saved_url, f"BUG: Saved wrong primary URL! Expected {test_urls[1]}, got {saved_url}"

    # Verify all 3 URLs are in the saved tabs
    saved_urls = [tab["url"] for tab in saved_tabs]
    for test_url in test_urls:
        assert any(test_url in url for url in saved_urls), f"BUG: Test URL {test_url} not found in saved tabs! Saved: {saved_urls}"

    # STEP 3: Terminate the instance and manager
    await manager1.terminate_instance(instance1.id)
    await manager1.shutdown()

    # STEP 4: Create NEW manager and restore session
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    instance2 = await manager2.session_manager.restore_session(
        session_id,
        manager2,
        kill_orphaned=True,
    )

    # STEP 5: Verify restoration - THIS WILL FAIL
    assert instance2.driver is not None
    tabs_after_restore = len(instance2.driver.window_handles)

    # THIS ASSERTION WILL FAIL - proving the bug
    assert tabs_after_restore == 3, (
        f"BUG DEMONSTRATED: Session had {tabs_before_save} tabs but restore only created {tabs_after_restore} tab(s). "
        f"The session save/restore does NOT persist multiple tabs!"
    )

    # If we somehow got here (we won't), verify all URLs were restored
    all_urls = []
    for handle in instance2.driver.window_handles:
        instance2.driver.switch_to.window(handle)
        all_urls.append(instance2.driver.current_url)

    for test_url in test_urls:
        assert any(test_url in url for url in all_urls), f"URL {test_url} was not restored. Restored URLs: {all_urls}"

    # Clean up
    await manager2.shutdown()
