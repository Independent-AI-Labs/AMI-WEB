"""Test to reproduce bug where window.open() causes original tab URL to become about:blank.

This test reproduces the specific issue where:
1. Navigate to a URL (e.g., x.com)
2. Use window.open() to create a new tab
3. Save the session
4. The original tab's URL is incorrectly saved as "about:blank"
"""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_window_open_corrupts_original_tab_url() -> None:
    """Reproduce bug where window.open() causes first tab to save as about:blank."""

    # Create test directories
    test_profiles_dir = Path("data/test_profiles_window_open_bug")
    test_sessions_dir = Path("data/test_sessions_window_open_bug")
    test_profiles_dir.mkdir(parents=True, exist_ok=True)
    test_sessions_dir.mkdir(parents=True, exist_ok=True)

    config_overrides = {
        "backend.storage.profiles_dir": str(test_profiles_dir),
        "backend.storage.session_dir": str(test_sessions_dir),
    }

    # Create manager and instance
    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    profile_name = "window-open-bug-profile"
    profile_dir = test_profiles_dir / profile_name
    if profile_dir.exists():
        manager.profile_manager.delete_profile(profile_name)
    manager.profile_manager.create_profile(profile_name)

    instance = await manager.get_or_create_instance(
        headless=True,
        profile=profile_name,
        use_pool=False,
    )

    # Navigate to first URL
    first_url = "https://x.com/"
    assert instance.driver is not None
    instance.driver.get(first_url)
    await asyncio.sleep(1)

    # Verify we're on the first URL
    current_url_after_nav = instance.driver.current_url
    print(f"✓ Navigated to: {current_url_after_nav}")
    assert (
        first_url in current_url_after_nav
    ), f"Should be on {first_url}, got {current_url_after_nav}"

    # Record the handle of the first tab
    first_tab_handle = instance.driver.current_window_handle
    print(f"✓ First tab handle: {first_tab_handle}")

    # Use window.open() to create a new tab (this mimics the user's action)
    instance.driver.execute_script("window.open('https://reddit.com', '_blank')")
    await asyncio.sleep(1)

    # Check if we have 2 tabs now
    num_tabs = len(instance.driver.window_handles)
    print(f"✓ Number of tabs after window.open(): {num_tabs}")
    assert num_tabs == 2, f"Should have 2 tabs, got {num_tabs}"

    # Switch to the new tab to verify it worked
    instance.driver.switch_to.window(instance.driver.window_handles[1])
    second_tab_url = instance.driver.current_url
    print(f"✓ Second tab URL: {second_tab_url}")

    # Switch back to the first tab to check its URL
    instance.driver.switch_to.window(first_tab_handle)
    first_tab_url_after_open = instance.driver.current_url
    print(f"✓ First tab URL after window.open(): {first_tab_url_after_open}")

    # THE BUG: First tab URL might be "about:blank" now
    # For now, just log it - we'll verify it in the saved session
    print(f"DEBUG: First tab URL is now: {first_tab_url_after_open}")

    # Save the session
    session_id = await manager.session_manager.save_session(
        instance, "window-open-bug-test"
    )
    print(f"✓ Saved session {session_id}")

    # Read the saved session file to inspect what was actually saved
    session_file = test_sessions_dir / session_id / "session.json"
    with session_file.open() as f:
        import json

        saved_data = json.load(f)

    saved_tabs = saved_data.get("tabs", [])
    print("\n=== SAVED SESSION DATA ===")
    print(f"Number of saved tabs: {len(saved_tabs)}")
    for i, tab in enumerate(saved_tabs):
        print(
            f"Tab {i}: handle={tab['handle']}, url={tab['url']}, title={tab['title']}"
        )

    # ASSERTION: The bug is that the first tab's URL is saved as "about:blank"
    # instead of the original URL
    first_saved_tab = saved_tabs[0]
    first_saved_url = first_saved_tab["url"]

    print("\n=== BUG CHECK ===")
    print(f"Expected first tab URL: {first_url}")
    print(f"Actual saved first tab URL: {first_saved_url}")

    # This assertion will FAIL if the bug exists
    assert first_url in first_saved_url, (
        f"BUG REPRODUCED: First tab URL was saved as '{first_saved_url}' "
        f"instead of '{first_url}' after using window.open()!"
    )

    # Also verify the second tab was saved correctly
    second_saved_tab = saved_tabs[1]
    second_saved_url = second_saved_tab["url"]
    assert (
        "reddit.com" in second_saved_url
    ), f"Second tab should be reddit.com, got {second_saved_url}"

    # Clean up
    await manager.shutdown()
