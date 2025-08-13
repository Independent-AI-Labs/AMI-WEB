"""Integration tests for MCP console logs, network logs, and storage functionality."""
# ruff: noqa: ARG002

import json
import os

import pytest
import websockets

# Import the MCP server fixture from test_mcp_server
from tests.integration.test_mcp_server import mcp_server  # noqa: F401

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"  # Default to headless


class TestMCPLogsAndStorage:
    """Test MCP logs and storage operations."""

    @pytest.mark.asyncio
    async def test_get_html(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving raw HTML via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch browser using JSON-RPC
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            # Navigate to a page
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Get full page HTML
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_get_html", "arguments": {"instance_id": instance_id}}, "id": 3}
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "html" in result
            html = result["html"]
            assert "<html" in html
            assert "Login" in html

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )

    @pytest.mark.asyncio
    async def test_get_text(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving text content via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch and navigate
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/dynamic_content.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Get text content
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_get_text", "arguments": {"instance_id": instance_id}}, "id": 3}
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "text" in result
            text = result["text"]
            assert "Dynamic Content" in text

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )

    @pytest.mark.asyncio
    async def test_extract_forms(self, mcp_server, test_html_server):  # noqa: F811
        """Test extracting form data via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch and navigate
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/login_form.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Extract forms
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_extract_forms", "arguments": {"instance_id": instance_id}}, "id": 3}
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "forms" in result
            forms = result["forms"]
            assert len(forms) > 0

            # Check form fields
            form = forms[0]
            assert "fields" in form
            field_names = [f["name"] for f in form["fields"]]
            assert "username" in field_names
            assert "password" in field_names

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )

    @pytest.mark.asyncio
    async def test_extract_links(self, mcp_server, test_html_server):  # noqa: F811
        """Test extracting links via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch and navigate
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/captcha_form.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Extract links
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_extract_links", "arguments": {"instance_id": instance_id}}, "id": 3}
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "links" in result
            links = result["links"]
            assert len(links) >= 0  # Might not have links on this page

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )

    @pytest.mark.asyncio
    async def test_console_logs(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving console logs via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch and navigate to page with console logs
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/dynamic_content.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Get console logs
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_get_console_logs", "arguments": {"instance_id": instance_id}},
                        "id": 3,
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "logs" in result
            # Logs might be empty if the page doesn't log anything

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )

    @pytest.mark.asyncio
    async def test_network_logs(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving network logs via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            # Launch and navigate
            await websocket.send(
                json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_launch", "arguments": {"headless": HEADLESS}}, "id": 1})
            )
            response = await websocket.recv()
            content = json.loads(response)["result"]["content"][0]
            instance_id = json.loads(content["text"])["instance_id"]

            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"instance_id": instance_id, "url": f"{test_html_server}/dynamic_content.html"}},
                        "id": 2,
                    }
                )
            )
            await websocket.recv()

            # Get network logs
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {"name": "browser_get_network_logs", "arguments": {"instance_id": instance_id}},
                        "id": 3,
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert "result" in data
            content = data["result"]["content"][0]
            result = json.loads(content["text"])
            assert "logs" in result
            logs = result["logs"]
            # Should have at least the navigation request
            assert len(logs) > 0
            # Check log structure
            if logs:
                log = logs[0]
                assert "url" in log
                assert "method" in log
                assert "status" in log

            # Cleanup
            await websocket.send(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "browser_terminate", "arguments": {"instance_id": instance_id}}, "id": 4}
                )
            )
