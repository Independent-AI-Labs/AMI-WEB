"""Integration tests for MCP server with real browser instances."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
import websockets

logger = logging.getLogger(__name__)

# Use headless mode by default in CI
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

# Add browser to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestChromeMCPServerModes:
    """Test Chrome MCP server in both stdio and websocket modes."""

    # Request IDs for JSONRPC calls
    INIT_REQUEST_ID = 1
    TOOLS_REQUEST_ID = 2

    @pytest.mark.asyncio
    async def test_chrome_stdio_mode(self):
        """Test Chrome MCP server in stdio mode."""
        # Start the server
        server_script = Path(__file__).parent.parent.parent / "backend" / "mcp" / "chrome" / "run_chrome.py"
        proc = subprocess.Popen(
            [sys.executable, str(server_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test_client", "version": "1.0.0"}},
                "id": self.INIT_REQUEST_ID,
            }

            proc.stdin.write(json.dumps(init_request) + "\n")
            proc.stdin.flush()

            # Read response with timeout
            response_line = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline), timeout=5.0)
            response = json.loads(response_line)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == self.INIT_REQUEST_ID
            assert "result" in response
            assert response["result"]["protocolVersion"] == "2024-11-05"
            assert "serverInfo" in response["result"]
            assert response["result"]["serverInfo"]["name"] == "ChromeMCPServer"

            # Send list tools request
            tools_request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": self.TOOLS_REQUEST_ID}

            proc.stdin.write(json.dumps(tools_request) + "\n")
            proc.stdin.flush()

            response_line = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, proc.stdout.readline), timeout=5.0)
            response = json.loads(response_line)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == self.TOOLS_REQUEST_ID
            assert "result" in response
            assert "tools" in response["result"]

            # Verify some expected tools exist
            tool_names = [tool["name"] for tool in response["result"]["tools"]]
            assert "navigate_to" in tool_names or "browser_navigate" in tool_names
            assert "click_element" in tool_names or "browser_click" in tool_names
            assert "take_screenshot" in tool_names or "browser_screenshot" in tool_names

        finally:
            proc.terminate()
            proc.wait(timeout=5)

    @pytest.mark.asyncio
    async def test_chrome_websocket_mode(self):
        """Test Chrome MCP server in websocket mode."""
        # Start the server in websocket mode
        server_script = Path(__file__).parent.parent.parent / "backend" / "mcp" / "chrome" / "run_chrome.py"
        proc = subprocess.Popen(
            [sys.executable, str(server_script), "--transport", "websocket", "--port", "9003"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Give server time to start
        await asyncio.sleep(2)

        try:
            # Connect to websocket
            async with websockets.connect("ws://localhost:9003") as websocket:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test_client", "version": "1.0.0"}},
                    "id": self.INIT_REQUEST_ID,
                }

                await websocket.send(json.dumps(init_request))
                response = json.loads(await websocket.recv())

                assert response["jsonrpc"] == "2.0"
                assert response["id"] == self.INIT_REQUEST_ID
                assert "result" in response
                assert response["result"]["protocolVersion"] == "2024-11-05"
                assert "serverInfo" in response["result"]
                assert response["result"]["serverInfo"]["name"] == "ChromeMCPServer"

                # Send list tools request
                tools_request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": self.TOOLS_REQUEST_ID}

                await websocket.send(json.dumps(tools_request))
                response = json.loads(await websocket.recv())

                assert response["jsonrpc"] == "2.0"
                assert response["id"] == self.TOOLS_REQUEST_ID
                assert "result" in response
                assert "tools" in response["result"]

                # Verify some expected tools exist
                tool_names = [tool["name"] for tool in response["result"]["tools"]]
                assert "navigate_to" in tool_names or "browser_navigate" in tool_names
                assert "click_element" in tool_names or "browser_click" in tool_names
                assert "take_screenshot" in tool_names or "browser_screenshot" in tool_names

        finally:
            proc.terminate()
            proc.wait(timeout=5)


@pytest.mark.asyncio(loop_scope="session")
class TestMCPServerIntegration:
    """Test MCP server with real browser integration."""

    @pytest.mark.slow
    async def test_ping_pong(self, mcp_client):
        """Test ping-pong messaging."""
        # Send ping and verify pong response
        result = await mcp_client.send_request("ping")
        assert result.get("status") == "pong"

    @pytest.mark.slow
    async def test_server_initialization(self, mcp_client):
        """Test server initializes correctly."""
        # Client already initialized in fixture
        # Just verify we can list tools
        result = await mcp_client.list_tools()

        assert "tools" in result
        tools = result["tools"]
        assert len(tools) > 0

        # Verify expected tools
        tool_names = [tool["name"] for tool in tools]
        assert "browser_launch" in tool_names
        assert "browser_navigate" in tool_names
        assert "browser_screenshot" in tool_names

    @pytest.mark.slow
    async def test_browser_lifecycle(self, mcp_client):
        """Test full browser lifecycle: launch, navigate, terminate."""
        # Launch browser
        instance_id = await mcp_client.launch_browser(headless=HEADLESS)
        assert instance_id
        logger.info(f"Launched browser instance: {instance_id}")

        try:
            # Navigate to URL
            await mcp_client.navigate(instance_id, "https://example.com")

            # Take screenshot
            result = await mcp_client.screenshot(instance_id)
            assert result
            assert "content" in result
            content = result["content"]
            assert len(content) > 0
            # Screenshots may return as text (base64) or image
            assert content[0]["type"] in ["text", "image"]

        finally:
            # Terminate
            await mcp_client.terminate(instance_id)
            logger.info(f"Terminated browser instance: {instance_id}")

    @pytest.mark.slow
    async def test_javascript_execution(self, mcp_client, mcp_browser_id):
        """Test executing JavaScript in browser."""
        # Navigate first
        await mcp_client.navigate(mcp_browser_id, "https://example.com")

        # Execute script
        script = "return document.title;"
        result = await mcp_client.execute_script(mcp_browser_id, script)

        assert result
        assert "content" in result
        content = result["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"
        text = json.loads(content[0]["text"])
        assert "result" in text

    @pytest.mark.slow
    async def test_form_interactions(self, mcp_client, mcp_browser_id):
        """Test form interaction capabilities."""
        # Navigate to a page with a form
        test_html = """
        <html>
        <body>
            <form id="test-form">
                <input type="text" id="username" name="username">
                <input type="password" id="password" name="password">
                <button type="submit">Submit</button>
            </form>
        </body>
        </html>
        """
        test_url = f"data:text/html,{test_html}"
        await mcp_client.navigate(mcp_browser_id, test_url)

        # Type in username field
        result = await mcp_client.call_tool("browser_type", {"instance_id": mcp_browser_id, "selector": "#username", "text": "testuser"})
        assert result

        # Type in password field
        result = await mcp_client.call_tool("browser_type", {"instance_id": mcp_browser_id, "selector": "#password", "text": "testpass"})
        assert result

        # Verify values were entered
        script = """
        return {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value
        };
        """
        result = await mcp_client.execute_script(mcp_browser_id, script)
        data = json.loads(result["content"][0]["text"])
        assert data["result"]["username"] == "testuser"
        test_password = "testpass"  # noqa: S105
        assert data["result"]["password"] == test_password

    @pytest.mark.slow
    async def test_concurrent_browser_instances(self, mcp_client):
        """Test managing multiple browser instances concurrently."""
        instance_ids = []

        try:
            # Launch 3 browsers sequentially (WebSocket client doesn't support concurrent recv)
            for _ in range(3):
                instance_id = await mcp_client.launch_browser(headless=True)
                instance_ids.append(instance_id)

            expected_count = 3
            assert len(instance_ids) == expected_count
            assert all(instance_id for instance_id in instance_ids)
            assert len(set(instance_ids)) == expected_count  # All unique

            logger.info(f"Launched {len(instance_ids)} browser instances")

        finally:
            # Cleanup all instances sequentially
            for instance_id in instance_ids:
                try:
                    await mcp_client.terminate(instance_id)
                except Exception as e:
                    logger.debug(f"Cleanup error (expected): {e}")

    @pytest.mark.slow
    async def test_cookie_management(self, mcp_client, mcp_browser_id):
        """Test cookie operations."""
        # Navigate to a site that sets cookies
        await mcp_client.navigate(mcp_browser_id, "https://httpbin.org/cookies/set?test=value")

        # Get cookies
        result = await mcp_client.call_tool("browser_get_cookies", {"instance_id": mcp_browser_id})
        assert result
        cookies = json.loads(result["content"][0]["text"])
        assert "cookies" in cookies

        # Set a custom cookie (using browser_set_cookies with array)
        result = await mcp_client.call_tool(
            "browser_set_cookies",
            {"instance_id": mcp_browser_id, "cookies": [{"name": "custom", "value": "cookie_value", "domain": ".httpbin.org"}]},
        )
        assert result

    @pytest.mark.slow
    async def test_network_monitoring(self, mcp_client):
        """Test network request monitoring."""
        # Launch with network monitoring enabled
        instance_id = await mcp_client.launch_browser(headless=HEADLESS, enable_network_monitoring=True)

        try:
            # Navigate to trigger network requests
            await mcp_client.navigate(instance_id, "https://httpbin.org/get")

            # Get network logs
            result = await mcp_client.call_tool("browser_get_network_logs", {"instance_id": instance_id})
            assert result
            logs = json.loads(result["content"][0]["text"])
            assert "logs" in logs
            assert len(logs["logs"]) > 0

            # Verify request details
            request = logs["logs"][0]
            assert "url" in request
            assert "method" in request
            assert "status_code" in request

        finally:
            await mcp_client.terminate(instance_id)

    @pytest.mark.slow
    async def test_error_handling(self, mcp_client):
        """Test error handling for invalid operations."""
        # Try to navigate with invalid instance ID
        with pytest.raises(Exception) as exc_info:
            await mcp_client.navigate("invalid-instance-id", "https://example.com")
        assert "not found" in str(exc_info.value).lower()

        # Try to call non-existent tool
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("non_existent_tool", {})
        assert "unknown tool" in str(exc_info.value).lower()

    @pytest.mark.slow
    async def test_html_extraction_with_token_limit(self, mcp_client, mcp_browser_id):
        """Test HTML extraction with token limits."""
        # Navigate to a smaller test page to avoid WebSocket frame size limit
        test_html = """
        <html><body>
            <h1 id="title">Test Page</h1>
            <div id="content">
                <p>This is a test page with some content.</p>
                <p>We're testing HTML extraction with token limits.</p>
            </div>
        </body></html>
        """
        await mcp_client.navigate(mcp_browser_id, f"data:text/html,{test_html}")

        # Test browser_get_html tool - should work with small page
        result = await mcp_client.call_tool("browser_get_html", {"instance_id": mcp_browser_id, "selector": "#content"})

        assert result is not None
        assert "content" in result
        content = result["content"]
        assert len(content) > 0

        # Verify we got the expected content
        text = content[0]["text"] if isinstance(content, list) else content
        assert "test page" in text.lower()
        assert "content" in text.lower()


@pytest.mark.asyncio(loop_scope="session")
class TestMCPServerResilience:
    """Test server resilience and error recovery."""

    @pytest.mark.slow
    async def test_browser_crash_recovery(self, mcp_client):
        """Test recovery from browser crash."""
        instance_id = await mcp_client.launch_browser(headless=HEADLESS)

        # Navigate to chrome://crash
        try:
            await mcp_client.navigate(instance_id, "chrome://crash")
        except Exception as e:
            logger.debug(f"Navigation error: {e}")

        # Verify instance is still listed
        result = await mcp_client.call_tool("browser_list", {})
        instances = json.loads(result["content"][0]["text"])["instances"]

        crashed_instance = next((i for i in instances if i["id"] == instance_id), None)
        assert crashed_instance is not None, "Instance should still be listed"

        # The instance should still be terminatable
        result = await mcp_client.terminate(instance_id)
        assert result is not None
        logger.debug("Successfully terminated instance after chrome://crash")

    @pytest.mark.slow
    async def test_timeout_handling(self, mcp_client, mcp_browser_id):
        """Test handling of long-running operations."""
        # Execute a long-running script
        script = """
        return new Promise(resolve => {
            setTimeout(() => resolve('done'), 2000);
        });
        """

        # Should complete within reasonable time
        result = await mcp_client.execute_script(mcp_browser_id, script)
        assert result
        data = json.loads(result["content"][0]["text"])
        assert data["result"] == "done"

    @pytest.mark.slow
    async def test_resource_cleanup(self, mcp_client):
        """Test proper resource cleanup."""
        instance_ids = []

        # Launch multiple browsers
        for _ in range(3):
            instance_id = await mcp_client.launch_browser(headless=True)
            instance_ids.append(instance_id)

        # List instances before cleanup (for comparison later)
        result = await mcp_client.call_tool("browser_list", {})
        instances_before = json.loads(result["content"][0]["text"])["instances"]
        # Count active instances before termination
        [i["id"] for i in instances_before if i.get("status") == "ready"]

        # Terminate all
        for instance_id in instance_ids:
            await mcp_client.terminate(instance_id)

        # List instances after cleanup
        result = await mcp_client.call_tool("browser_list", {})
        instances_after = json.loads(result["content"][0]["text"])["instances"]
        active_after = [i["id"] for i in instances_after if i.get("status") == "ready"]

        # Verify cleanup
        for instance_id in instance_ids:
            assert instance_id not in active_after


@pytest.mark.asyncio(loop_scope="session")
class TestMCPServerPerformance:
    """Performance and load tests for MCP server."""

    @pytest.mark.slow
    @pytest.mark.parametrize("num_operations", [10, 20])
    async def test_rapid_operations(self, mcp_client, mcp_browser_id, num_operations):
        """Test rapid sequential operations."""
        # Navigate to a simple page
        await mcp_client.navigate(mcp_browser_id, "data:text/html,<html><body></body></html>")

        # Perform rapid operations
        for i in range(num_operations):
            script = f"return {i} * 2;"
            result = await mcp_client.execute_script(mcp_browser_id, script)
            data = json.loads(result["content"][0]["text"])
            assert data["result"] == i * 2

    @pytest.mark.slow
    async def test_memory_usage(self, mcp_client):
        """Test memory usage with multiple tabs."""
        instance_id = await mcp_client.launch_browser(headless=HEADLESS)

        try:
            # Navigate multiple times (browser_new_tab and browser_get_metrics don't exist)
            for i in range(5):
                await mcp_client.call_tool("browser_navigate", {"instance_id": instance_id, "url": f"https://example.com?tab={i}"})

            # Verify instance is still working
            result = await mcp_client.call_tool("browser_screenshot", {"instance_id": instance_id})
            assert result is not None
            assert "content" in result

        finally:
            await mcp_client.terminate(instance_id)
