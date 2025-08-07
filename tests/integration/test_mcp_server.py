"""Integration tests for MCP server functionality."""

import asyncio
import base64
import json
import uuid

import pytest
import websockets

from chrome_manager.core.manager import ChromeManager
from chrome_manager.mcp.server import MCPServer
from tests.fixtures.test_server import HTMLTestServer


@pytest.fixture(scope="session")
def test_html_server(event_loop):
    """Start test HTML server."""

    async def _start_server():
        server = HTMLTestServer(port=8889)
        base_url = await server.start()
        return server, base_url

    server, base_url = event_loop.run_until_complete(_start_server())
    yield base_url
    event_loop.run_until_complete(server.stop())


@pytest.fixture
def mcp_server(event_loop):
    """Start MCP server for testing."""

    async def _start_mcp():
        manager = ChromeManager()
        await manager.start()

        config = {"server_host": "localhost", "server_port": 8766, "max_connections": 10}

        server = MCPServer(manager, config)
        await server.start()
        return server, manager

    server, manager = event_loop.run_until_complete(_start_mcp())
    yield server, manager

    event_loop.run_until_complete(server.stop())
    event_loop.run_until_complete(manager.stop())


class TestMCPServerConnection:
    """Test MCP server connection and capabilities."""

    @pytest.mark.asyncio
    async def test_connect_to_server(self, mcp_server):
        """Test connecting to MCP server."""
        server, manager = mcp_server

        # Connect to server
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Receive capabilities
            message = await websocket.recv()
            data = json.loads(message)

            assert data["type"] == "capabilities"
            assert "tools" in data
            assert len(data["tools"]) > 0

            # Check for expected tools
            tool_names = [tool["name"] for tool in data["tools"]]
            assert "browser_launch" in tool_names
            assert "browser_navigate" in tool_names
            assert "browser_screenshot" in tool_names

    @pytest.mark.asyncio
    async def test_ping_pong(self, mcp_server):
        """Test ping-pong messaging."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            # Skip capabilities message
            await websocket.recv()

            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))

            # Receive pong
            response = await websocket.recv()
            data = json.loads(response)

            assert data["type"] == "pong"

    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server):
        """Test listing available tools."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Request tool list
            await websocket.send(json.dumps({"type": "list_tools"}))

            response = await websocket.recv()
            data = json.loads(response)

            assert data["type"] == "tools"
            assert isinstance(data["tools"], list)
            assert len(data["tools"]) > 0


class TestMCPBrowserOperations:
    """Test MCP browser operations."""

    @pytest.mark.asyncio
    async def test_launch_browser(self, mcp_server):
        """Test launching browser via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True
            assert "instance_id" in data["result"]

            instance_id = data["result"]["instance_id"]

            # Close browser
            close_request = {"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(close_request))
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_navigate_and_screenshot(self, mcp_server, test_html_server):
        """Test navigation and screenshot via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(launch_request))
            response = await websocket.recv()
            launch_data = json.loads(response)
            instance_id = launch_data["result"]["instance_id"]

            # Navigate to page
            nav_request = {
                "type": "tool",
                "tool": "browser_navigate",
                "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(nav_request))
            response = await websocket.recv()
            nav_data = json.loads(response)

            assert nav_data["success"] is True
            assert "Login" in nav_data["result"]["title"]

            # Take screenshot
            screenshot_request = {
                "type": "tool",
                "tool": "browser_screenshot",
                "parameters": {"instance_id": instance_id, "type": "viewport"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(screenshot_request))
            response = await websocket.recv()
            screenshot_data = json.loads(response)

            assert screenshot_data["success"] is True
            assert "image" in screenshot_data["result"]

            # Decode and verify screenshot
            image_data = base64.b64decode(screenshot_data["result"]["image"])
            assert len(image_data) > 0
            assert image_data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG header

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )

    @pytest.mark.asyncio
    async def test_input_operations(self, mcp_server, test_html_server):
        """Test input operations via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(launch_request))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_navigate",
                        "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Type text
            type_request = {
                "type": "tool",
                "tool": "browser_type",
                "parameters": {"instance_id": instance_id, "selector": "#username", "text": "testuser", "clear": True},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(type_request))
            response = await websocket.recv()
            type_data = json.loads(response)

            assert type_data["success"] is True

            # Click button
            click_request = {
                "type": "tool",
                "tool": "browser_click",
                "parameters": {"instance_id": instance_id, "selector": "#submit-btn"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(click_request))
            response = await websocket.recv()
            click_data = json.loads(response)

            assert click_data["success"] is True

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )

    @pytest.mark.asyncio
    async def test_script_execution(self, mcp_server, test_html_server):
        """Test script execution via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_navigate",
                        "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/captcha_form.html"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Execute script
            script_request = {
                "type": "tool",
                "tool": "browser_execute_script",
                "parameters": {"instance_id": instance_id, "script": "return window.captchaState.textCaptcha"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(script_request))
            response = await websocket.recv()
            script_data = json.loads(response)

            assert script_data["success"] is True
            assert isinstance(script_data["result"]["result"], str)
            assert len(script_data["result"]["result"]) == 6  # CAPTCHA length

            # Execute script with arguments
            script_with_args = {
                "type": "tool",
                "tool": "browser_execute_script",
                "parameters": {"instance_id": instance_id, "script": "window.testHelpers.solveCaptcha(arguments[0])", "args": ["text"]},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(script_with_args))
            response = await websocket.recv()

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )


class TestMCPCookieManagement:
    """Test cookie management via MCP."""

    @pytest.mark.asyncio
    async def test_get_and_set_cookies(self, mcp_server, test_html_server):
        """Test getting and setting cookies via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_navigate",
                        "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Set cookies
            set_cookies_request = {
                "type": "tool",
                "tool": "browser_set_cookies",
                "parameters": {
                    "instance_id": instance_id,
                    "cookies": [
                        {"name": "test_cookie", "value": "test_value", "domain": "localhost"},
                        {"name": "session_id", "value": "abc123", "domain": "localhost"},
                    ],
                },
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(set_cookies_request))
            response = await websocket.recv()
            set_data = json.loads(response)

            assert set_data["success"] is True

            # Get cookies
            get_cookies_request = {
                "type": "tool",
                "tool": "browser_get_cookies",
                "parameters": {"instance_id": instance_id, "domain": "localhost"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(get_cookies_request))
            response = await websocket.recv()
            get_data = json.loads(response)

            assert get_data["success"] is True
            cookies = get_data["result"]["cookies"]

            cookie_names = [c["name"] for c in cookies]
            assert "test_cookie" in cookie_names
            assert "session_id" in cookie_names

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )


class TestMCPTabManagement:
    """Test tab management via MCP."""

    @pytest.mark.asyncio
    async def test_tab_operations(self, mcp_server, test_html_server):
        """Test tab operations via MCP."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to first page
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_navigate",
                        "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Open new tab via script
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_execute_script",
                        "parameters": {"instance_id": instance_id, "script": f"window.open('{test_html_server}/captcha_form.html', '_blank')"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Get tabs
            get_tabs_request = {"type": "tool", "tool": "browser_get_tabs", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(get_tabs_request))
            response = await websocket.recv()
            tabs_data = json.loads(response)

            assert tabs_data["success"] is True
            tabs = tabs_data["result"]["tabs"]
            assert len(tabs) == 2

            # Switch tab
            other_tab = tabs[1] if tabs[0]["active"] else tabs[0]
            switch_request = {
                "type": "tool",
                "tool": "browser_switch_tab",
                "parameters": {"instance_id": instance_id, "tab_id": other_tab["id"]},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(switch_request))
            response = await websocket.recv()
            switch_data = json.loads(response)

            assert switch_data["success"] is True

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )


class TestMCPErrorHandling:
    """Test MCP error handling."""

    @pytest.mark.asyncio
    async def test_invalid_tool(self, mcp_server):
        """Test calling invalid tool."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Call non-existent tool
            request = {"type": "tool", "tool": "invalid_tool", "parameters": {}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is False
            assert "error" in data
            assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_instance(self, mcp_server):
        """Test operations on invalid instance."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Try to navigate with invalid instance
            request = {
                "type": "tool",
                "tool": "browser_navigate",
                "parameters": {"instance_id": "invalid-id-123", "url": "https://example.com"},
                "request_id": str(uuid.uuid4()),
            }

            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is False
            assert "error" in data
            assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_malformed_request(self, mcp_server):
        """Test handling malformed requests."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Send invalid JSON
            await websocket.send("not valid json")
            response = await websocket.recv()
            data = json.loads(response)

            assert "error" in data
            assert "Invalid JSON" in data["error"]


class TestMCPConcurrency:
    """Test MCP concurrent operations."""

    @pytest.mark.asyncio
    async def test_multiple_clients(self, mcp_server):
        """Test multiple clients connecting simultaneously."""
        server, manager = mcp_server

        async def client_task(client_id):
            async with websockets.connect("ws://localhost:8766") as websocket:
                await websocket.recv()  # Skip capabilities

                # Each client launches a browser
                await websocket.send(
                    json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": f"client-{client_id}"})
                )

                response = await websocket.recv()
                data = json.loads(response)
                assert data["success"] is True

                instance_id = data["result"]["instance_id"]

                # Clean up
                await websocket.send(
                    json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": f"close-{client_id}"})
                )

                return client_id

        # Run multiple clients concurrently
        results = await asyncio.gather(*[client_task(i) for i in range(3)])

        assert len(results) == 3
        assert results == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_concurrent_operations_same_instance(self, mcp_server, test_html_server):
        """Test concurrent operations on same browser instance."""
        server, manager = mcp_server

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": True}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate first
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_navigate",
                        "parameters": {"instance_id": instance_id, "url": f"{test_html_server}/dynamic_content.html"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Send multiple requests rapidly
            requests = [
                {
                    "type": "tool",
                    "tool": "browser_execute_script",
                    "parameters": {"instance_id": instance_id, "script": f"return {i} * 2"},
                    "request_id": str(uuid.uuid4()),
                }
                for i in range(5)
            ]

            # Send all requests
            for req in requests:
                await websocket.send(json.dumps(req))

            # Receive all responses
            responses = []
            for _ in requests:
                response = await websocket.recv()
                responses.append(json.loads(response))

            # Verify all succeeded
            for i, resp in enumerate(responses):
                assert resp["success"] is True
                # Results might be in different order

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
