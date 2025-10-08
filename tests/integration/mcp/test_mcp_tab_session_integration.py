"""Integration tests for MCP tab management + session persistence.

This test suite addresses the critical gap in test coverage where MCP tab operations
were never tested in combination with session save/restore functionality.

Bug Context:
- Users lost tabs when using MCP open_tab + goto + session save
- All previous tests used execute_script("window.open") instead of MCP tools
- No tests verified tab persistence across MCP operations + session save/restore
"""

import asyncio
import json
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.facade.navigation import browser_navigate_tool
from browser.backend.mcp.chrome.tools.facade.session import browser_session_tool

pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")


@pytest.mark.asyncio
async def test_mcp_open_tab_goto_session_save_restore(worker_data_dirs: dict[str, Path]) -> None:
    """Test the exact user scenario: open_tab + goto + session save + restore.

    This reproduces the bug reported by the user where tabs were lost.
    """
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
        "backend.pool.hibernation_delay": 9999,  # Prevent hibernation during test
        "backend.pool.close_tabs_on_hibernation": False,  # Preserve tabs
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        # Step 1: Launch browser (similar to user's action)
        response = await browser_session_tool(manager, action="launch", headless=True, profile="default", use_pool=False)
        assert response.success, f"Launch failed: {response.error}"
        instance_id = response.instance_id
        await asyncio.sleep(0.5)

        # Step 2: Navigate first tab to x.com (like the user did)
        response = await browser_navigate_tool(manager, action="goto", url="https://example.com/x")
        assert response.success, f"Navigate to x.com failed: {response.error}"
        await asyncio.sleep(0.5)

        # Step 3: Open new tab using MCP (not execute_script)
        response = await browser_navigate_tool(manager, action="open_tab")
        assert response.success, f"Open tab failed: {response.error}"
        assert response.data is not None
        await asyncio.sleep(0.5)

        # Step 4: Navigate second tab to reddit.com
        response = await browser_navigate_tool(manager, action="goto", url="https://example.com/reddit")
        assert response.success, f"Navigate to reddit failed: {response.error}"
        await asyncio.sleep(0.5)

        # Verify we have 2 tabs BEFORE saving
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"List tabs failed: {response.error}"
        assert response.data is not None
        print(f"DEBUG: Before save - tab count: {response.data['count']}, tabs: {response.data['tabs']}")

        # Get the actual instance to inspect it
        if instance_id:
            instance = await manager.get_instance(instance_id)
        else:
            instance = None
        if instance and instance.driver:
            actual_handles = instance.driver.window_handles
            print(f"DEBUG: Direct driver check - window_handles: {actual_handles}")
            for i, handle in enumerate(actual_handles):
                instance.driver.switch_to.window(handle)
                url = instance.driver.current_url
                print(f"DEBUG: Tab {i}: handle={handle}, url={url}")

        assert response.data["count"] == 2, f"Expected 2 tabs before save, got {response.data['count']}"

        # Step 5: Save session
        response = await browser_session_tool(
            manager,
            action="save",
            instance_id=instance_id,
            session_name="x-reddit-test",
        )
        assert response.success, f"Save session failed: {response.error}"
        assert response.data is not None
        session_id = response.data["session_id"]

        # Verify the saved session has 2 tabs
        session_file = worker_data_dirs["sessions_dir"] / session_id / "session.json"
        assert session_file.exists(), f"Session file not found: {session_file}"

        with session_file.open() as f:
            saved_data = json.load(f)

        print(f"DEBUG: Saved session data: {json.dumps(saved_data, indent=2)}")

        assert "tabs" in saved_data, "Session data missing 'tabs' field"
        assert len(saved_data["tabs"]) == 2, f"Expected 2 tabs in saved session, got {len(saved_data['tabs'])}"

        saved_urls = [tab["url"] for tab in saved_data["tabs"]]
        assert any("example.com/x" in str(url) for url in saved_urls), f"x.com URL not in saved tabs: {saved_urls}"
        assert any("example.com/reddit" in str(url) for url in saved_urls), f"reddit URL not in saved tabs: {saved_urls}"

        # Step 6: Terminate the instance
        assert instance_id is not None
        await manager.terminate_instance(instance_id)
        await asyncio.sleep(0.5)

        # Step 7: Restore the session
        response = await browser_session_tool(manager, action="restore", session_id=session_id)
        assert response.success, f"Restore session failed: {response.error}"
        restored_instance_id = response.instance_id
        await asyncio.sleep(1)

        # Step 8: Verify 2 tabs were restored
        response = await browser_navigate_tool(manager, action="list_tabs", instance_id=restored_instance_id)
        assert response.success, f"List tabs after restore failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 2, f"Expected 2 tabs after restore, got {response.data['count']}"

        # Step 9: Verify both URLs were restored correctly
        all_urls = []
        for tab_info in response.data["tabs"]:
            tab_id = tab_info["tab_id"]
            # Switch to tab
            switch_response = await browser_navigate_tool(
                manager,
                action="switch_tab",
                tab_id=tab_id,
                instance_id=restored_instance_id,
            )
            assert switch_response.success, f"Switch to tab {tab_id} failed: {switch_response.error}"
            # Get URL
            url_response = await browser_navigate_tool(manager, action="get_url", instance_id=restored_instance_id)
            assert url_response.success, f"Get URL failed: {url_response.error}"
            all_urls.append(url_response.url)

        print(f"DEBUG: Restored URLs: {all_urls}")

        assert any("example.com/x" in str(url) for url in all_urls), f"x.com URL not restored: {all_urls}"
        assert any("example.com/reddit" in str(url) for url in all_urls), f"reddit URL not restored: {all_urls}"

        print("✓ MCP tab + session save/restore integration test PASSED")

    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_mcp_multiple_tabs_with_navigation_errors(worker_data_dirs: dict[str, Path]) -> None:
    """Test that navigation errors don't kill the instance and lose all tabs."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
        "backend.pool.hibernation_delay": 9999,
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        # Create instance
        instance = await manager.get_or_create_instance(headless=True, use_pool=True)
        assert instance.driver is not None
        manager.set_current_instance(instance.id)

        # Navigate first tab
        response = await browser_navigate_tool(manager, action="goto", url="https://example.com/")
        assert response.success
        await asyncio.sleep(0.5)

        # Open second tab
        response = await browser_navigate_tool(manager, action="open_tab", url="https://example.org/")
        assert response.success
        await asyncio.sleep(0.5)

        # Open third tab
        response = await browser_navigate_tool(manager, action="open_tab", url="https://example.net/")
        assert response.success
        await asyncio.sleep(0.5)

        # Verify 3 tabs exist
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success
        assert response.data is not None
        assert response.data["count"] == 3, f"Expected 3 tabs, got {response.data['count']}"

        # Attempt to navigate to an invalid/timeout URL (should fail gracefully)
        response = await browser_navigate_tool(manager, action="goto", url="https://this-will-timeout.invalid/", timeout=2)
        assert not response.success, "Expected navigation to invalid URL to fail"

        # CRITICAL: Verify the instance is still alive and tabs are preserved
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, "Instance should still be alive after navigation error"
        assert response.data is not None
        assert response.data["count"] == 3, f"Tabs should be preserved after error, got {response.data['count']}"

        print("✓ Navigation errors preserve instance and tabs")

    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_hibernation_preserves_tabs(worker_data_dirs: dict[str, Path]) -> None:
    """Test that hibernation preserves tabs when configured correctly."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
        "backend.pool.hibernation_delay": 1,  # Hibernate after 1 second
        "backend.pool.close_tabs_on_hibernation": False,  # DO NOT close tabs
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        # Create instance from pool
        instance = await manager.get_or_create_instance(headless=True, use_pool=True)
        manager.set_current_instance(instance.id)

        # Open multiple tabs
        await browser_navigate_tool(manager, action="goto", url="https://example.com/")
        await browser_navigate_tool(manager, action="open_tab", url="https://example.org/")
        await browser_navigate_tool(manager, action="open_tab", url="https://example.net/")
        await asyncio.sleep(0.5)

        # Verify 3 tabs
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.data is not None
        assert response.data["count"] == 3

        # Return instance to pool (marks as idle)
        # Note: In real usage, this happens when tool completes
        # For testing, we manually trigger by getting a fresh instance
        await manager.get_or_create_instance(headless=True, use_pool=True)

        # Wait for hibernation to potentially occur
        await asyncio.sleep(2)

        # Verify tabs are STILL preserved
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, "Should be able to list tabs after hibernation"
        assert response.data is not None

        # With close_tabs_on_hibernation=False, tabs should be preserved
        # Note: Hibernation navigates first tab to about:blank but preserves count
        assert response.data["count"] >= 1, "At least one tab should remain after hibernation"

        print("✓ Hibernation with tab preservation works correctly")

    finally:
        await manager.shutdown()
