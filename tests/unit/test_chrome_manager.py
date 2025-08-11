#!/usr/bin/env python3
"""
Test script for Chrome Manager
"""

import asyncio
import json

from chrome_manager import ChromeManager
from chrome_manager.facade.media import ScreenshotController
from chrome_manager.facade.navigation import NavigationController


async def test_basic_operations():
    print("Testing Chrome Manager Basic Operations...")

    # Initialize manager with config file
    manager = ChromeManager(config_file="config.yaml")
    await manager.initialize()

    try:
        # Create a browser instance
        print("\n1. Creating browser instance...")
        instance = await manager.get_or_create_instance(headless=True)
        print(f"   [OK] Created instance: {instance.id}")

        # Navigate to a website
        print("\n2. Navigating to example.com...")
        nav = NavigationController(instance)
        result = await nav.navigate("https://example.com")
        print(f"   [OK] Loaded: {result.title} in {result.load_time:.2f}s")

        # Take a screenshot
        print("\n3. Taking screenshot...")
        screenshot = ScreenshotController(instance)
        image_data = await screenshot.capture_viewport()
        print(f"   [OK] Screenshot captured: {len(image_data)} bytes")

        # Execute JavaScript
        print("\n4. Executing JavaScript...")
        js_result = await nav.execute_script("return document.title")
        print(f"   [OK] JS Result: {js_result}")

        # Get browser info
        print("\n5. Getting browser info...")
        info = instance.get_info()
        print(f"   [OK] Status: {info.status.value}")
        print(f"   [OK] Memory: {info.memory_usage / 1024 / 1024:.1f} MB")
        print(f"   [OK] Tabs: {info.active_tabs}")

        # Clean up
        print("\n6. Cleaning up...")
        await manager.terminate_instance(instance.id)
        print("   [OK] Instance terminated")

        print("\n[SUCCESS] All tests passed!")

    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        raise
    finally:
        await manager.shutdown()


async def test_mcp_server():
    print("\nTesting MCP Server...")
    print("Run the server with: python -m chrome_manager.mcp_server")
    print("Then connect with WebSocket client to ws://localhost:8765")

    # Example MCP messages
    messages = {
        "list_tools": {"type": "list_tools"},
        "launch_browser": {"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}},
        "navigate": {"type": "tool", "tool": "browser_navigate", "parameters": {"instance_id": "<instance_id>", "url": "https://example.com"}},
    }

    print("\nExample MCP messages:")
    for name, msg in messages.items():
        print(f"\n{name}:")
        print(json.dumps(msg, indent=2))


if __name__ == "__main__":
    print("=" * 60)
    print("Chrome Manager Test Suite")
    print("=" * 60)

    asyncio.run(test_basic_operations())
    test_mcp_server()
