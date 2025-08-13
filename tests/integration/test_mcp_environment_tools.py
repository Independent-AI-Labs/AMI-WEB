"""Integration tests for MCP environment management tools."""

import asyncio
import contextlib
import json
import os
import threading
import time

import pytest
import pytest_asyncio
import websockets
from loguru import logger

from chrome_manager.core.management.manager import ChromeManager
from chrome_manager.mcp.browser.server import BrowserMCPServer

# Set headless mode for tests
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"


class MCPTestServer:
    """Test MCP server that runs properly for testing."""

    def __init__(self, port=8767):  # Different port from main test
        self.port = port
        self.server = None
        self.manager = None
        self.loop = None
        self.thread = None
        self.ready_event = threading.Event()
        self.stop_event = threading.Event()

    def _run_server(self):
        """Run server with its own event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._setup_server())
            self.ready_event.set()
            self.loop.run_until_complete(self._serve_forever())
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.ready_event.set()
        finally:
            self.loop.run_until_complete(self._cleanup())
            self.loop.close()

    async def _setup_server(self):
        """Set up the server components."""
        self.manager = ChromeManager(config_file="config.test.yaml")
        await self.manager.initialize()

        # Configure for testing
        self.manager.pool.min_instances = 0
        self.manager.pool.warm_instances = 0
        self.manager.pool.max_instances = 2

        config = {"server_host": "localhost", "server_port": self.port, "max_connections": 10}
        self.server = BrowserMCPServer(self.manager, config)
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
            await self.manager.shutdown()

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
            with contextlib.suppress(Exception):
                self.loop.stop()
                self.loop.close()


@pytest_asyncio.fixture(scope="module")
async def mcp_server():
    """Start MCP test server for environment tests."""
    server = MCPTestServer(port=8767)
    server.start()

    yield server

    server.stop()


class TestProfileManagement:
    """Test profile management tools."""

    @pytest.mark.asyncio
    async def test_list_profiles(self, mcp_server):
        """Test listing browser profiles."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            # Send request using JSON-RPC
            request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "profile_list", "arguments": {}}, "id": 1}
            await websocket.send(json.dumps(request))

            # Get response
            response = json.loads(await websocket.recv())
            assert "result" in response
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            assert "profiles" in result
            assert isinstance(result["profiles"], list)

    @pytest.mark.asyncio
    async def test_create_and_delete_profile(self, mcp_server):
        """Test creating and deleting a profile."""
        profile_name = "test_profile_mcp"

        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            # Create profile using JSON-RPC
            create_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "profile_create", "arguments": {"name": profile_name, "description": "Test profile"}},
                "id": 1,
            }
            await websocket.send(json.dumps(create_request))
            response = json.loads(await websocket.recv())
            assert "result" in response

            # List profiles to verify creation
            list_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "profile_list", "arguments": {}}, "id": 2}
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            profiles = result["profiles"]
            profile_names = [p["name"] for p in profiles]
            assert profile_name in profile_names

            # Delete the profile
            delete_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "profile_delete", "arguments": {"name": profile_name}}, "id": 3}
            await websocket.send(json.dumps(delete_request))
            response = json.loads(await websocket.recv())
            assert "result" in response

            # Verify deletion
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            profiles = result["profiles"]
            profile_names = [p["name"] for p in profiles]
            assert profile_name not in profile_names


class TestSessionManagement:
    """Test session management tools."""

    @pytest.mark.asyncio
    async def test_save_and_list_sessions(self, mcp_server):
        """Test saving and listing sessions."""
        session_name = "test_session_mcp"

        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            # Launch a browser first to have something to save
            launch_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1}
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            assert "result" in response
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            instance_id = result["instance_id"]

            # Save session
            save_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "session_save", "arguments": {"name": session_name}}, "id": 2}
            await websocket.send(json.dumps(save_request))
            response = json.loads(await websocket.recv())
            assert "result" in response

            # List sessions
            list_request = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "session_list", "arguments": {}}, "id": 3}
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            assert "result" in response
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            sessions = result["sessions"]
            session_names = [s["name"] for s in sessions]
            assert session_name in session_names

            # Clean up browser
            close_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}},
                "id": 4,
            }
            await websocket.send(json.dumps(close_request))
            await websocket.recv()


class TestSecurityConfiguration:
    """Test security configuration tools."""

    @pytest.mark.asyncio
    async def test_launch_with_antidetect(self, mcp_server):
        """Test launching browser with anti-detection enabled."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            # Launch with anti-detect
            launch_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS, "anti_detect": True}},
                "id": 1,
            }
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            assert "result" in response
            content = response["result"]["content"][0]
            result = json.loads(content["text"])
            instance_id = result["instance_id"]

            # Verify browser is running (can navigate)
            nav_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": "https://example.com"}},
                "id": 2,
            }
            await websocket.send(json.dumps(nav_request))
            response = json.loads(await websocket.recv())
            assert "result" in response

            # Clean up
            close_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}},
                "id": 3,
            }
            await websocket.send(json.dumps(close_request))
            await websocket.recv()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
