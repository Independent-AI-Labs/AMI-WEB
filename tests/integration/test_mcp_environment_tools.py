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

from chrome_manager.core.manager import ChromeManager
from chrome_manager.mcp.server import MCPServer

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
        self.manager = ChromeManager(config_file="config.yaml")
        self.manager.pool.min_instances = 1
        self.manager.pool.warm_instances = 1
        self.manager.pool.max_instances = 3
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
            await self.manager.shutdown()
            for instance in list(self.manager._instances.values()):
                with contextlib.suppress(Exception):
                    await instance.terminate()
            self.manager._instances.clear()

    def start(self):
        """Start the server in a thread."""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        if not self.ready_event.wait(timeout=10):
            raise TimeoutError("Server failed to start")

        time.sleep(0.5)

    def stop(self):
        """Stop the server."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                logger.warning("Server thread did not stop gracefully")
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.stop()
                self.loop.close()
            except Exception as e:
                logger.error(f"Error closing loop: {e}")


@pytest_asyncio.fixture(scope="session")
async def mcp_server():
    """Create and start test MCP server."""
    server = MCPTestServer(port=8767)
    server.start()
    yield server
    server.stop()
    await asyncio.sleep(0.5)


class TestProfileManagement:
    """Test profile management MCP tools."""

    @pytest.mark.asyncio
    async def test_list_profiles(self, mcp_server):
        """Test listing browser profiles."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            # Skip capabilities message
            await websocket.recv()

            # Send request
            request = {"type": "tool", "tool": "browser_list_profiles", "parameters": {}, "request_id": "test-1"}
            await websocket.send(json.dumps(request))

            # Get response
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            assert "profiles" in response["result"]
            assert isinstance(response["result"]["profiles"], list)

    @pytest.mark.asyncio
    async def test_create_and_delete_profile(self, mcp_server):
        """Test creating and deleting a profile."""
        profile_name = "test_profile_mcp"

        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            await websocket.recv()  # Skip capabilities

            # First, launch a browser with a profile to create it
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS, "profile": profile_name}, "request_id": "test-2"}
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            instance_id = response["result"]["instance_id"]

            # Close the browser
            close_request = {"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": "test-3"}
            await websocket.send(json.dumps(close_request))
            response = json.loads(await websocket.recv())

            # List profiles to verify it exists
            list_request = {"type": "tool", "tool": "browser_list_profiles", "parameters": {}, "request_id": "test-4"}
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            profiles = response["result"]["profiles"]
            assert any(p["name"] == profile_name for p in profiles)

            # Delete the profile
            delete_request = {"type": "tool", "tool": "browser_delete_profile", "parameters": {"profile_name": profile_name}, "request_id": "test-5"}
            await websocket.send(json.dumps(delete_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True

            # Verify it's deleted
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            profiles = response["result"]["profiles"]
            assert not any(p["name"] == profile_name for p in profiles)


class TestSessionManagement:
    """Test session management MCP tools."""

    @pytest.mark.asyncio
    async def test_save_and_list_sessions(self, mcp_server):
        """Test saving and listing browser sessions."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            launch_request = {
                "type": "tool",
                "tool": "browser_launch",
                "parameters": {"headless": HEADLESS, "profile": "test_session_profile"},
                "request_id": "test-9",
            }
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            instance_id = response["result"]["instance_id"]

            # Navigate to a page
            nav_request = {
                "type": "tool",
                "tool": "browser_navigate",
                "parameters": {"instance_id": instance_id, "url": "https://example.com"},
                "request_id": "test-10",
            }
            await websocket.send(json.dumps(nav_request))
            response = json.loads(await websocket.recv())

            # Save session
            save_request = {"type": "tool", "tool": "browser_save_session", "parameters": {"instance_id": instance_id}, "request_id": "test-11"}
            await websocket.send(json.dumps(save_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            session_id = response["result"]["session_id"]

            # List sessions
            list_request = {"type": "tool", "tool": "browser_list_sessions", "parameters": {}, "request_id": "test-13"}
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            sessions = response["result"]["sessions"]
            assert any(s["id"] == session_id for s in sessions)

            # Clean up
            close_request = {"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": "test-15"}
            await websocket.send(json.dumps(close_request))
            await websocket.recv()


class TestDownloadManagement:
    """Test download management MCP tools."""

    @pytest.mark.asyncio
    async def test_download_directory_operations(self, mcp_server):
        """Test download directory and file operations."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            launch_request = {
                "type": "tool",
                "tool": "browser_launch",
                "parameters": {"headless": HEADLESS, "profile": "test_download_profile"},
                "request_id": "test-21",
            }
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            instance_id = response["result"]["instance_id"]

            # Get download directory
            get_dir_request = {"type": "tool", "tool": "browser_get_download_dir", "parameters": {"instance_id": instance_id}, "request_id": "test-22"}
            await websocket.send(json.dumps(get_dir_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            download_dir = response["result"]["download_dir"]
            assert download_dir is not None

            # List downloads (should be empty initially)
            list_request = {"type": "tool", "tool": "browser_list_downloads", "parameters": {"instance_id": instance_id}, "request_id": "test-23"}
            await websocket.send(json.dumps(list_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            assert isinstance(response["result"]["downloads"], list)

            # Clear downloads (even if empty)
            clear_request = {"type": "tool", "tool": "browser_clear_downloads", "parameters": {"instance_id": instance_id}, "request_id": "test-24"}
            await websocket.send(json.dumps(clear_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True

            # Clean up
            close_request = {"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": "test-25"}
            await websocket.send(json.dumps(close_request))
            await websocket.recv()


class TestSecurityConfiguration:
    """Test security configuration MCP tool."""

    @pytest.mark.asyncio
    async def test_set_security_level(self, mcp_server):
        """Test setting security level."""
        async with websockets.connect(f"ws://localhost:{mcp_server.port}") as websocket:
            await websocket.recv()  # Skip capabilities

            # Set security level
            set_request = {"type": "tool", "tool": "browser_set_security", "parameters": {"level": "strict"}, "request_id": "test-sec"}
            await websocket.send(json.dumps(set_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True

            # Launch browser (which should use the security config)
            launch_request = {"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": "test-launch-sec"}
            await websocket.send(json.dumps(launch_request))
            response = json.loads(await websocket.recv())
            assert response["success"] is True
            instance_id = response["result"]["instance_id"]

            # Close browser
            close_request = {"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": "test-close-sec"}
            await websocket.send(json.dumps(close_request))
            await websocket.recv()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
