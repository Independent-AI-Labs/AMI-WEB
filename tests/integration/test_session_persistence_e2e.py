"""E2E tests for session save/restore that validate actual Chrome state persistence."""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_session_save_and_restore_validates_actual_chrome_state() -> None:
    """E2E test: Save session, terminate Chrome, restore in NEW process, verify cookies/URL/tabs."""
    test_file = Path(__file__).resolve()
    browser_root = test_file.parent.parent.parent

    session_dir = browser_root / "data" / "test_sessions_e2e"
    profiles_dir = browser_root / "data" / "test_profiles_e2e"

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    if "e2e-profile" in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile("e2e-profile")
    manager1.profile_manager.create_profile("e2e-profile", "E2E test profile")

    # STEP 1: Launch real Chrome, set cookies, navigate to URL
    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile="e2e-profile",
        use_pool=False,
    )

    # REPRODUCE THE BUG: Simulate real user workflow with background tabs
    assert instance1.driver is not None
    instance1.driver.set_page_load_timeout(30)

    # Browser starts with initial tab (might be new tab page)
    await asyncio.sleep(0.5)
    initial_url = instance1.driver.current_url
    print(f"DEBUG: Browser started with: {initial_url}")

    # Open a new tab (simulates clicking through UI)
    instance1.driver.execute_script("window.open('');")
    await asyncio.sleep(0.5)

    # Switch to new tab and navigate to example.com
    all_handles = instance1.driver.window_handles
    instance1.driver.switch_to.window(all_handles[-1])

    test_url = "https://example.com/"
    instance1.driver.get(test_url)
    instance1.driver.add_cookie(
        {
            "name": "e2e_test_cookie",
            "value": "session_data_123",
            "domain": ".example.com",
            "path": "/",
        }
    )
    instance1.driver.get(test_url)  # Navigate again after setting cookie

    # Verify cookie is set
    cookies_before = instance1.driver.get_cookies()
    test_cookie_before = next((c for c in cookies_before if c["name"] == "e2e_test_cookie"), None)
    assert test_cookie_before is not None, "Test cookie should be set before save"
    assert test_cookie_before["value"] == "session_data_123"

    # Check all tabs (should have background new tab + example.com tab)
    all_handles_before = instance1.driver.window_handles
    current_handle_before = instance1.driver.current_window_handle
    print(f"DEBUG: Found {len(all_handles_before)} tabs before save")
    for i, handle in enumerate(all_handles_before):
        instance1.driver.switch_to.window(handle)
        url = instance1.driver.current_url
        print(f"DEBUG: Tab {i}: {url}")

    # Make sure we're on example.com tab
    instance1.driver.switch_to.window(current_handle_before)
    final_url_before_save = instance1.driver.current_url
    final_handle_before_save = instance1.driver.current_window_handle
    print(f"DEBUG: Active tab before save: {final_url_before_save}")
    print(f"DEBUG: Active handle before save: {final_handle_before_save}")

    assert "example.com" in final_url_before_save, f"Should be on example.com, got {final_url_before_save}"

    # STEP 2: Save session
    session_id = await manager1.save_session(instance1.id, "e2e-test-session")

    # Verify what was saved
    session_file = session_dir / session_id / "session.json"
    import json

    with session_file.open() as f:
        saved_data = json.load(f)

    saved_url = saved_data.get("url")
    saved_tabs = saved_data.get("tabs", [])
    saved_active_handle = saved_data.get("active_tab_handle")

    print(f"DEBUG: Saved URL: {saved_url}")
    print(f"DEBUG: Saved {len(saved_tabs)} tabs")
    print(f"DEBUG: Saved active handle: {saved_active_handle}")

    assert "chrome://new-tab-page" not in saved_url, (
        f"BUG: Saved chrome://new-tab-page instead of example.com! " f"Active was {final_url_before_save} but saved {saved_url}"
    )
    assert "example.com" in saved_url, f"BUG: Saved URL {saved_url} doesn't contain example.com"

    # STEP 3: TERMINATE Chrome completely (this is the critical part)
    await manager1.terminate_instance(instance1.id)
    await manager1.shutdown()

    # STEP 4: Create NEW manager and restore session in NEW Chrome process
    manager2 = ChromeManager(config_overrides=config_overrides)
    await manager2.initialize()

    instance2 = await manager2.session_manager.restore_session(
        session_id,
        manager2,
    )

    # STEP 5: VERIFY actual Chrome state was restored
    # Verify we're on the same URL
    assert instance2.driver is not None
    instance2.driver.set_page_load_timeout(30)
    current_url = instance2.driver.current_url
    assert "example.com" in current_url, f"URL not restored. Expected example.com in URL, got: {current_url}"

    # Verify cookies were actually restored in Chrome
    cookies_after = instance2.driver.get_cookies()
    test_cookie_after = next((c for c in cookies_after if c["name"] == "e2e_test_cookie"), None)
    assert test_cookie_after is not None, f"Test cookie not restored. Cookies present: {[c['name'] for c in cookies_after]}"
    assert test_cookie_after["value"] == "session_data_123", f"Cookie value incorrect: {test_cookie_after['value']}"

    # Verify page title is similar (might not be exact due to Google changes)
    title_after = instance2.driver.title
    assert len(title_after) > 0, "Page title should not be empty after restore"

    # Cleanup
    await manager2.terminate_instance(instance2.id)
    manager2.session_manager.delete_session(session_id)
    await manager2.shutdown()


@pytest.mark.asyncio
async def test_session_restore_with_multiple_tabs() -> None:
    """E2E test: Verify multiple tabs are tracked in session (even if not fully restored yet)."""
    test_file = Path(__file__).resolve()
    browser_root = test_file.parent.parent.parent

    session_dir = browser_root / "data" / "test_sessions_e2e"
    profiles_dir = browser_root / "data" / "test_profiles_e2e"

    config_overrides = {
        "backend.storage.session_dir": str(session_dir),
        "backend.storage.profiles_dir": str(profiles_dir),
    }

    manager1 = ChromeManager(config_overrides=config_overrides)
    await manager1.initialize()

    if "e2e-tabs-profile" in manager1.profile_manager.profiles:
        manager1.profile_manager.delete_profile("e2e-tabs-profile")
    manager1.profile_manager.create_profile("e2e-tabs-profile", "E2E tabs test profile")

    instance1 = await manager1.get_or_create_instance(
        headless=True,
        profile="e2e-tabs-profile",
        use_pool=False,
    )

    # Open multiple tabs
    assert instance1.driver is not None
    instance1.driver.get("https://www.google.com/")
    instance1.driver.execute_script("window.open('https://www.example.com/', '_blank');")
    instance1.driver.execute_script("window.open('https://www.wikipedia.org/', '_blank');")

    tab_count_before = len(instance1.driver.window_handles)
    assert tab_count_before == 3, f"Should have 3 tabs, got {tab_count_before}"

    # Save session
    session_id = await manager1.save_session(instance1.id, "e2e-tabs-session")

    # Read session data to verify tab count was saved
    session_file = session_dir / session_id / "session.json"
    assert session_file.exists(), "Session file should exist"

    import json

    with session_file.open() as f:
        session_data = json.load(f)

    assert session_data["window_handles"] == 3, f"Session should record 3 tabs, got {session_data.get('window_handles')}"

    # Cleanup
    await manager1.terminate_instance(instance1.id)
    manager1.session_manager.delete_session(session_id)
    await manager1.shutdown()
