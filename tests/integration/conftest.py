"""Shared fixtures for browser integration tests."""

import asyncio
import json
import os
from typing import Any

import pytest
import pytest_asyncio
import websockets
from loguru import logger

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"  # Default to headless


class MCPTestServer:
    """Test MCP server that runs properly for testing."""

    def __init__(self, port=8766):
        self.port = port
        self.server = None
        self.manager = None
        self._server_task = None

    async def start(self):
        """Start the server asynchronously."""
        # Import here to avoid import issues
        from pathlib import Path

        from browser.backend.core.management.manager import ChromeManager
        from browser.backend.mcp.chrome.server import BrowserMCPServer

        # Use config.yaml if it exists, otherwise config.test.yaml, otherwise defaults
        config_file = "config.test.yaml"
        if Path("config.yaml").exists():
            config_file = "config.yaml"
        elif not Path("config.test.yaml").exists():
            # Will use defaults if neither exists
            config_file = None

        self.manager = ChromeManager(config_file=config_file)
        # Override pool settings for efficient test reuse
        self.manager.pool.min_instances = 2  # Keep 2 instances ready
        self.manager.pool.warm_instances = 2  # Keep 2 warm for reuse
        self.manager.pool.max_instances = 5  # Allow more for concurrent tests
        await self.manager.start()

        config = {"server_host": "localhost", "server_port": self.port, "max_connections": 10, "response_format": "json"}
        self.server = BrowserMCPServer(config)
        # Replace the server's manager with our test manager
        self.server.manager = self.manager
        await self.server.start()

        logger.info(f"Test MCP server started on port {self.port}")

        # Give the server time to fully initialize
        await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the server."""
        if self.server:
            await self.server.stop()
        if self.manager:
            # Force shutdown of all browser instances and pool
            await self.manager.shutdown()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mcp_server():
    """Start MCP test server for the session."""
    import random

    # Use a random port to avoid conflicts
    port = random.randint(9000, 9999)  # noqa: S311
    server = MCPTestServer(port=port)
    await server.start()  # Start asynchronously in same event loop

    yield server

    await server.stop()  # Stop asynchronously


class MCPClient:
    """Helper class for MCP protocol communication in tests."""

    def __init__(self, websocket):
        """Initialize MCP client with WebSocket connection."""
        self.websocket = websocket
        self._request_id = 0

    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    async def send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send MCP request and wait for response."""
        request_id = self._next_id()
        request = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": request_id}

        await self.websocket.send(json.dumps(request))
        response = await asyncio.wait_for(self.websocket.recv(), timeout=30)
        data = json.loads(response)

        # Verify response matches request
        assert data.get("id") == request_id, f"Response ID mismatch: expected {request_id}, got {data.get('id')}"

        if "error" in data:
            raise Exception(f"MCP error: {data['error']}")

        return data.get("result", {})

    async def initialize(self) -> dict[str, Any]:
        """Send initialize request."""
        return await self.send_request("initialize")

    async def list_tools(self) -> dict[str, Any]:
        """List available tools."""
        return await self.send_request("tools/list")

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a specific tool."""
        return await self.send_request("tools/call", {"name": name, "arguments": arguments or {}})

    async def launch_browser(self, headless: bool = True, **kwargs) -> str:
        """Launch browser and return instance ID."""
        result = await self.call_tool("browser_launch", {"headless": headless, **kwargs})

        # Extract instance ID from response
        if result and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "{}")
                data = json.loads(text)
                return data.get("instance_id")

        raise Exception("Failed to get instance ID from browser_launch response")

    async def navigate(self, instance_id: str, url: str) -> dict[str, Any]:
        """Navigate browser to URL."""
        return await self.call_tool("browser_navigate", {"instance_id": instance_id, "url": url})

    async def screenshot(self, instance_id: str) -> dict[str, Any]:
        """Take screenshot."""
        return await self.call_tool("browser_screenshot", {"instance_id": instance_id})

    async def execute_script(self, instance_id: str, script: str) -> dict[str, Any]:
        """Execute JavaScript."""
        return await self.call_tool("browser_execute_script", {"instance_id": instance_id, "script": script})

    async def terminate(self, instance_id: str) -> dict[str, Any]:
        """Terminate browser instance."""
        return await self.call_tool("browser_terminate", {"instance_id": instance_id})


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def mcp_client(mcp_server):
    """Create MCP client connected to test server - new connection per test."""
    async with websockets.connect(f"ws://localhost:{mcp_server.port}", ping_interval=None, open_timeout=5) as websocket:
        client = MCPClient(websocket)
        # Initialize connection
        await client.initialize()
        yield client


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def mcp_browser_id(mcp_client):
    """Create a browser instance ID via MCP for testing."""
    # Use headless mode from environment
    instance_id = await mcp_client.launch_browser(headless=HEADLESS)
    try:
        yield instance_id
    finally:
        # Cleanup
        try:
            await mcp_client.terminate(instance_id)
        except Exception as e:
            logger.debug(f"Cleanup error (expected): {e}")


@pytest.fixture
async def browser_with_page(mcp_client, mcp_browser_id):
    """Create a browser instance navigated to a test page."""
    # Navigate to a simple test page
    test_url = "data:text/html,<html><body><h1>Test Page</h1></body></html>"
    await mcp_client.navigate(mcp_browser_id, test_url)

    yield mcp_browser_id, test_url
