"""Integration tests for MCP console logs, network logs, and storage functionality."""
# ruff: noqa: ARG002

import json
import os
import uuid

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
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to a page
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

            # Get full page HTML
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_html", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True
            assert "html" in data["result"]
            html = data["result"]["html"]

            # Verify it's actual HTML
            assert "<html" in html.lower()
            assert "<body" in html.lower()
            assert "Login Form" in html  # Page title
            assert 'id="username"' in html  # Form element

            # Get HTML of specific element
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_get_html",
                        "parameters": {"instance_id": instance_id, "selector": "#login-form"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True
            element_html = data["result"]["html"]

            # Verify we got just the form HTML
            assert 'id="username"' in element_html
            assert 'id="password"' in element_html
            assert "<html" not in element_html.lower()  # Should not have the full page

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            await websocket.recv()  # Wait for close response

    @pytest.mark.asyncio
    async def test_console_logs(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving console logs via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to a page that generates console logs
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

            # Execute script to generate console logs
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_execute_script",
                        "parameters": {
                            "instance_id": instance_id,
                            "script": """
                            console.log('Test log message');
                            console.warn('Test warning');
                            console.error('Test error');
                            return 'logs generated';
                            """,
                        },
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Get console logs
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_console_logs", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True
            assert "logs" in data["result"]
            logs = data["result"]["logs"]

            # Check that we have some logs
            assert len(logs) > 0

            # Verify log structure
            for log in logs:
                assert "timestamp" in log
                assert "level" in log
                assert "message" in log

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            await websocket.recv()  # Wait for close response

    @pytest.mark.asyncio
    async def test_network_logs(self, mcp_server, test_html_server):  # noqa: F811
        """Test retrieving network logs via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to a page (this will generate network activity)
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

            # Get network logs
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_network_logs", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)

            assert data["success"] is True
            assert "logs" in data["result"]
            logs = data["result"]["logs"]

            # Verify log structure (may be empty if performance logging not enabled)
            for log in logs:
                assert "timestamp" in log
                assert "method" in log
                assert "url" in log
                assert "status_code" in log

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            await websocket.recv()  # Wait for close response

    @pytest.mark.asyncio
    async def test_local_storage_operations(self, mcp_server, test_html_server):  # noqa: F811
        """Test local storage operations via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to a page
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

            # Set local storage item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_set_local_storage",
                        "parameters": {"instance_id": instance_id, "key": "test_key", "value": "test_value"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True

            # Get specific local storage item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_get_local_storage",
                        "parameters": {"instance_id": instance_id, "key": "test_key"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True
            assert data["result"]["data"] == "test_value"

            # Set another item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_set_local_storage",
                        "parameters": {"instance_id": instance_id, "key": "another_key", "value": "another_value"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            await websocket.recv()

            # Get all local storage items
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_local_storage", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True
            storage_data = data["result"]["data"]
            assert isinstance(storage_data, dict)
            assert storage_data.get("test_key") == "test_value"
            assert storage_data.get("another_key") == "another_value"

            # Remove an item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_remove_local_storage",
                        "parameters": {"instance_id": instance_id, "key": "test_key"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True

            # Verify item was removed
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_get_local_storage",
                        "parameters": {"instance_id": instance_id, "key": "test_key"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["result"]["data"] is None

            # Clear all local storage
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_clear_local_storage",
                        "parameters": {"instance_id": instance_id},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True

            # Verify storage is empty
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_local_storage", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)
            storage_data = data["result"]["data"]
            assert storage_data == {}

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            await websocket.recv()  # Wait for close response

    @pytest.mark.asyncio
    async def test_session_storage_operations(self, mcp_server, test_html_server):  # noqa: F811
        """Test session storage operations via MCP."""
        async with websockets.connect("ws://localhost:8766") as websocket:
            await websocket.recv()  # Skip capabilities

            # Launch browser
            await websocket.send(json.dumps({"type": "tool", "tool": "browser_launch", "parameters": {"headless": HEADLESS}, "request_id": str(uuid.uuid4())}))
            response = await websocket.recv()
            instance_id = json.loads(response)["result"]["instance_id"]

            # Navigate to a page
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

            # Set session storage item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_set_session_storage",
                        "parameters": {"instance_id": instance_id, "key": "session_key", "value": "session_value"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True

            # Get session storage item
            await websocket.send(
                json.dumps(
                    {
                        "type": "tool",
                        "tool": "browser_get_session_storage",
                        "parameters": {"instance_id": instance_id, "key": "session_key"},
                        "request_id": str(uuid.uuid4()),
                    }
                )
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True
            assert data["result"]["data"] == "session_value"

            # Get all session storage items
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_get_session_storage", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            response = await websocket.recv()
            data = json.loads(response)
            assert data["success"] is True
            storage_data = data["result"]["data"]
            assert isinstance(storage_data, dict)
            assert "session_key" in storage_data

            # Cleanup
            await websocket.send(
                json.dumps({"type": "tool", "tool": "browser_close", "parameters": {"instance_id": instance_id}, "request_id": str(uuid.uuid4())})
            )
            await websocket.recv()  # Wait for close response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
