"""Integration tests for MCP server functionality."""
# ruff: noqa: ARG002

import asyncio
import contextlib
import json
import os
import threading
import time
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
import websockets
from loguru import logger

from chrome_manager.core import ChromeManager
from chrome_manager.mcp.server import MCPServer

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"  # Default to headless


class MCPTestServer:
    """Test MCP server that runs properly for testing."""

    def __init__(self, port=8766):
        self.port = port
        self.server = None
        self.manager = None
        self.loop = None
        self.thread = None
        self.ready_event = threading.Event()
        self.stop_event = threading.Event()

    def _run_server(self):
        """Run server with its own event loop."""
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # Initialize manager and server synchronously in the thread
            self.loop.run_until_complete(self._setup_server())
            self.ready_event.set()

            # Keep the server running
            self.loop.run_until_complete(self._serve_forever())

        except Exception as e:
            logger.error(f"Server error: {e}")
            self.ready_event.set()  # Signal even on error
        finally:
            self.loop.run_until_complete(self._cleanup())
            self.loop.close()

    async def _setup_server(self):
        """Set up the server components."""
        self.manager = ChromeManager(config_file="config.yaml")
        # Override pool settings for efficient test reuse
        self.manager.pool.min_instances = 1  # Keep 1 instance ready
        self.manager.pool.warm_instances = 1  # Keep 1 warm for reuse
        self.manager.pool.max_instances = 3  # Limit max instances (for concurrent tests)
        await self.manager.start()

        config = {"server_host": "localhost", "server_port": self.port, "max_connections": 10}
        self.server = MCPServer(self.manager, config)
        await self.server.start()

        logger.info(f"Test MCP server started on port {self.port}")

    async def _serve_forever(self):
        """Keep server running until stop is signaled."""
        while not self.stop_event.is_set():
            await asyncio.sleep(0.1)

    async def _cleanup(self):
        """Clean up server resources."""
        if self.server:
            await self.server.stop()
        if self.manager:
            # Force shutdown of all browser instances and pool
            await self.manager.shutdown()
            # Extra cleanup - ensure all instances are terminated
            for instance in list(self.manager._instances.values()):
                with contextlib.suppress(Exception):
                    await instance.terminate()
            self.manager._instances.clear()

    def start(self):
        """Start the server in a thread."""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        # Wait for server to be ready
        if not self.ready_event.wait(timeout=10):
            raise TimeoutError("Server failed to start")

        # Extra wait for socket binding
        time.sleep(0.5)

    def stop(self):
        """Stop the server."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                logger.warning("Server thread did not stop gracefully")
        # Force cleanup the event loop if it exists
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.stop()
                self.loop.close()
            except Exception as e:
                logger.error(f"Error closing loop: {e}")


@pytest_asyncio.fixture(scope="session")
async def mcp_server():
    """Start MCP test server once for the entire test session."""
    server = MCPTestServer(port=8766)
    server.start()

    yield server

    server.stop()


class TestMCPServerConnection:
    """Test MCP server connection and capabilities."""

    @pytest.mark.asyncio
    async def test_connect_to_server(self, mcp_server):
        """Test connecting to MCP server."""
        # mcp_server is the test server instance

        # Connect to the server
        async with websockets.connect("ws://localhost:8766", open_timeout=5) as websocket:
            # Server should send capabilities immediately
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)

            assert data["type"] == "capabilities"
            assert "tools" in data
            assert len(data["tools"]) > 0

            # Verify expected tools are registered
            tool_names = [tool["name"] for tool in data["tools"]]
            assert "browser_launch" in tool_names
            assert "browser_navigate" in tool_names
            assert "browser_screenshot" in tool_names
            assert "browser_click" in tool_names
            assert "browser_type" in tool_names

            logger.info(f"MCP server has {len(tool_names)} tools available")

    @pytest.mark.asyncio
    async def test_ping_pong(self, mcp_server):
        """Test ping-pong messaging."""
        # mcp_server is the test server instance

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
        # mcp_server is the test server instance

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
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}

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
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766", ping_interval=None) as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}

            await websocket.send(json.dumps(launch_request))
            response = await asyncio.wait_for(websocket.recv(), timeout=30)
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
            response = await asyncio.wait_for(websocket.recv(), timeout=30)
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
            assert "path" in screenshot_data["result"]

            # Verify screenshot file was created
            screenshot_path = Path(screenshot_data["result"]["path"])
            assert screenshot_path.exists()
            assert screenshot_path.suffix == ".png"

            # Verify it's a valid PNG file
            with screenshot_path.open("rb") as f:
                header = f.read(8)
                png_header = b"\x89PNG\r\n\x1a\n"
                assert header == png_header  # PNG header

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )

    @pytest.mark.asyncio
    async def test_input_operations(self, mcp_server, test_html_server):
        """Test input operations via MCP."""
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}

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
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
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
            captcha_length = 6
            assert len(script_data["result"]["result"]) == captcha_length  # CAPTCHA length

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
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch and navigate
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
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
                        {"name": "test_cookie", "value": "test_value", "domain": "127.0.0.1"},
                        {"name": "session_id", "value": "abc123", "domain": "127.0.0.1"},
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
                "parameters": {"instance_id": instance_id, "domain": "127.0.0.1"},
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
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
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
            expected_tabs = 2
            assert len(tabs) == expected_tabs

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
        # mcp_server is the test server instance

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
        # mcp_server is the test server instance

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
        # mcp_server is the test server instance

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
        # mcp_server is the test server instance

        async def client_task(client_id):
            async with websockets.connect("ws://localhost:8766") as websocket:
                await websocket.recv()  # Skip capabilities

                # Each client launches a browser
                await websocket.send(
                    json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": f"client-{client_id}"})
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
        num_clients = 3
        results = await asyncio.gather(*[client_task(i) for i in range(num_clients)])

        assert len(results) == num_clients
        assert results == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_concurrent_operations_same_instance(self, mcp_server, test_html_server):
        """Test concurrent operations on same browser instance."""
        # mcp_server is the test server instance

        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
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
            for resp in responses:
                assert resp["success"] is True
                # Results might be in different order

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
