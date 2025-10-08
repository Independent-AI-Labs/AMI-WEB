"""Integration tests for script validation in browser execution."""

import asyncio
from pathlib import Path

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.mark.asyncio
async def test_window_open_blank_is_blocked(worker_data_dirs: dict[str, Path]) -> None:
    """Test that window.open with _blank is blocked by validation."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    instance = await manager.get_or_create_instance(
        headless=True,
        use_pool=False,
    )
    manager.set_current_instance(instance.id)

    # Navigate to a page first
    assert instance.driver is not None
    instance.driver.get("https://example.com")
    await asyncio.sleep(0.5)

    # Try to execute forbidden window.open script
    from browser.backend.mcp.chrome.tools.javascript_tools import browser_execute_tool

    script = "window.open('https://reddit.com', '_blank')"
    result = await browser_execute_tool(manager, script)

    # Should be blocked
    assert not result.success
    assert result.error is not None
    assert "Script validation failed" in result.error
    assert "_blank" in result.error or "tab_management" in result.error

    # Verify only one tab exists (window.open was blocked)
    num_tabs = len(instance.driver.window_handles)
    assert num_tabs == 1, f"Should still have 1 tab, got {num_tabs}"

    await manager.shutdown()


@pytest.mark.asyncio
async def test_safe_script_is_allowed(worker_data_dirs: dict[str, Path]) -> None:
    """Test that safe scripts are allowed through validation."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    instance = await manager.get_or_create_instance(
        headless=True,
        use_pool=False,
    )
    manager.set_current_instance(instance.id)

    # Navigate to a page first
    assert instance.driver is not None
    instance.driver.get("https://example.com")
    await asyncio.sleep(0.5)

    # Try to execute safe script
    from browser.backend.mcp.chrome.tools.javascript_tools import browser_execute_tool

    script = "return document.title"
    result = await browser_execute_tool(manager, script)

    # Should succeed
    assert result.success
    assert result.error is None
    assert result.result is not None

    await manager.shutdown()


@pytest.mark.asyncio
async def test_window_close_is_blocked(worker_data_dirs: dict[str, Path]) -> None:
    """Test that window.close() is blocked by validation."""
    config_overrides = {
        "backend.storage.profiles_dir": str(worker_data_dirs["profiles_dir"]),
        "backend.storage.session_dir": str(worker_data_dirs["sessions_dir"]),
    }

    manager = ChromeManager(config_overrides=config_overrides)
    await manager.initialize()

    instance = await manager.get_or_create_instance(
        headless=True,
        use_pool=False,
    )
    manager.set_current_instance(instance.id)

    # Navigate to a page first
    assert instance.driver is not None
    instance.driver.get("https://example.com")
    await asyncio.sleep(0.5)

    # Try to execute forbidden window.close script
    from browser.backend.mcp.chrome.tools.javascript_tools import browser_execute_tool

    script = "window.close()"
    result = await browser_execute_tool(manager, script)

    # Should be blocked
    assert not result.success
    assert result.error is not None
    assert "Script validation failed" in result.error
    assert "window.close" in result.error or "tab_management" in result.error

    # Verify browser is still alive
    assert instance.driver is not None
    assert len(instance.driver.window_handles) >= 1

    await manager.shutdown()
