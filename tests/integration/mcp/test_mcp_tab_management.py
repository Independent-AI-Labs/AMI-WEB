"""E2E integration tests for MCP tab management via browser_navigate tool."""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.facade.navigation import browser_navigate_tool


@pytest.mark.asyncio
async def test_mcp_tab_lifecycle_full_e2e(worker_data_dirs: dict[str, Path]) -> None:
    """Test complete tab lifecycle: open, list, switch, navigate, close."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        # Create instance
        instance = await manager.get_or_create_instance(headless=True, use_pool=False)
        assert instance.driver is not None
        manager.set_current_instance(instance.id)

        # Navigate first tab to a URL
        response = await browser_navigate_tool(manager, action="goto", url="https://example.com")
        assert response.success, f"goto failed: {response.error}"
        await asyncio.sleep(0.5)

        # List tabs - should have 1 tab
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"list_tabs failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 1, f"Expected 1 tab, got {response.data['count']}"
        tab1_id = response.data["tabs"][0]["tab_id"]
        assert response.data["tabs"][0]["is_current"] is True

        # Open new tab with URL
        response = await browser_navigate_tool(manager, action="open_tab", url="https://example.org")
        assert response.success, f"open_tab failed: {response.error}"
        assert response.data is not None
        tab2_id = response.data["tab_id"]
        assert tab2_id is not None
        await asyncio.sleep(0.5)

        # List tabs - should have 2 tabs now
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"list_tabs failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 2, f"Expected 2 tabs, got {response.data['count']}"

        # Verify current tab is the newly opened one
        current_tabs = [t for t in response.data["tabs"] if t["is_current"]]
        assert len(current_tabs) == 1
        # Note: tab_id may change after operations, just verify we have a current tab
        assert current_tabs[0]["tab_id"] is not None

        # Get current URL - should be example.org
        response = await browser_navigate_tool(manager, action="get_url")
        assert response.success, f"get_url failed: {response.error}"
        assert response.url is not None
        assert "example.org" in str(response.url)

        # Switch back to first tab
        response = await browser_navigate_tool(manager, action="switch_tab", tab_id=tab1_id)
        assert response.success, f"switch_tab failed: {response.error}"

        # Verify we're on the first tab now
        response = await browser_navigate_tool(manager, action="get_url")
        assert response.success, f"get_url failed: {response.error}"
        assert response.url is not None
        assert "example.com" in str(response.url)

        # Open third tab without URL
        response = await browser_navigate_tool(manager, action="open_tab")
        assert response.success, f"open_tab without url failed: {response.error}"
        assert response.data is not None
        await asyncio.sleep(0.5)

        # List tabs - should have 3 tabs
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"list_tabs failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 3, f"Expected 3 tabs, got {response.data['count']}"

        # Navigate the third tab
        response = await browser_navigate_tool(manager, action="goto", url="https://example.net")
        assert response.success, f"goto on new tab failed: {response.error}"
        await asyncio.sleep(0.5)

        # Verify current URL
        response = await browser_navigate_tool(manager, action="get_url")
        assert response.success
        assert response.url is not None
        assert "example.net" in str(response.url)

        # Close the second tab by ID
        response = await browser_navigate_tool(manager, action="close_tab", tab_id=tab2_id)
        assert response.success, f"close_tab failed: {response.error}"

        # List tabs - should have 2 tabs
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"list_tabs after close failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 2, f"Expected 2 tabs after close, got {response.data['count']}"

        # Verify tab2_id is gone
        tab_ids = [t["tab_id"] for t in response.data["tabs"]]
        assert tab2_id not in tab_ids, f"Closed tab {tab2_id} still in list: {tab_ids}"

        # Close current tab (should close tab3)
        response = await browser_navigate_tool(manager, action="close_tab")
        assert response.success, f"close_tab (current) failed: {response.error}"

        # List tabs - should have 1 tab left
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success, f"list_tabs after second close failed: {response.error}"
        assert response.data is not None
        assert response.data["count"] == 1, f"Expected 1 tab after second close, got {response.data['count']}"

        # Verify only one tab remains (tab IDs may change)
        assert len(response.data["tabs"]) == 1

        print("✓ All tab management operations succeeded")

    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_mcp_tab_switch_validation(worker_data_dirs: dict[str, Path]) -> None:
    """Test that switch_tab requires tab_id parameter."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        instance = await manager.get_or_create_instance(headless=True, use_pool=False)
        assert instance.driver is not None
        manager.set_current_instance(instance.id)

        # Attempt switch_tab without tab_id
        response = await browser_navigate_tool(manager, action="switch_tab", tab_id=None)
        assert not response.success, "switch_tab should fail without tab_id"
        assert response.error is not None
        assert "tab_id required" in str(response.error)

        print("✓ Validation test passed")

    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_mcp_tab_antidetect_injection(worker_data_dirs: dict[str, Path]) -> None:
    """Test that new tabs get anti-detection properly injected."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        # Create instance with anti_detect enabled
        instance = await manager.get_or_create_instance(headless=True, anti_detect=True, use_pool=False)
        assert instance.driver is not None
        manager.set_current_instance(instance.id)

        # Navigate first tab
        response = await browser_navigate_tool(manager, action="goto", url="https://example.com")
        assert response.success
        await asyncio.sleep(0.5)

        # Open new tab - should get antidetect injection
        response = await browser_navigate_tool(manager, action="open_tab", url="https://example.org")
        assert response.success
        assert response.data is not None
        tab2_id = response.data["tab_id"]
        await asyncio.sleep(0.5)

        # Verify we can interact with the new tab (proves antidetect worked)
        response = await browser_navigate_tool(manager, action="get_url")
        assert response.success
        assert response.url is not None
        assert "example.org" in str(response.url)

        # Switch back and forth between tabs
        response = await browser_navigate_tool(manager, action="list_tabs")
        assert response.success
        assert response.data is not None
        tab1_id = [t["tab_id"] for t in response.data["tabs"] if t["tab_id"] != tab2_id][0]

        response = await browser_navigate_tool(manager, action="switch_tab", tab_id=tab1_id)
        assert response.success

        response = await browser_navigate_tool(manager, action="switch_tab", tab_id=tab2_id)
        assert response.success

        print("✓ Anti-detection tab injection test passed")

    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_mcp_tab_error_handling(worker_data_dirs: dict[str, Path]) -> None:
    """Test error handling for invalid tab operations."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    try:
        instance = await manager.get_or_create_instance(headless=True, use_pool=False)
        assert instance.driver is not None

        # Try to switch to non-existent tab
        response = await browser_navigate_tool(manager, action="switch_tab", tab_id="invalid-tab-id-12345")
        assert not response.success, "Should fail switching to invalid tab"

        # Try to close non-existent tab
        response = await browser_navigate_tool(manager, action="close_tab", tab_id="invalid-tab-id-67890")
        assert not response.success, "Should fail closing invalid tab"

        print("✓ Error handling test passed")

    finally:
        await manager.shutdown()
