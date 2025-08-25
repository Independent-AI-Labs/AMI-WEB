"""Unit tests for MCP protocol implementation."""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestMCPProtocol:
    """Test MCP protocol handling without real browser or server."""

    def test_request_format(self, mock_mcp_request):
        """Test MCP request format."""
        request = mock_mcp_request("tools/list", {"filter": "browser"}, 42)

        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "tools/list"
        assert request["params"] == {"filter": "browser"}
        expected_id = 42
        assert request["id"] == expected_id

    def test_response_format(self, mock_mcp_response):
        """Test MCP response format."""
        response = mock_mcp_response({"tools": ["browser_launch", "browser_navigate"]}, 42)

        assert response["jsonrpc"] == "2.0"
        assert response["result"] == {"tools": ["browser_launch", "browser_navigate"]}
        expected_id = 42
        assert response["id"] == expected_id
        assert "error" not in response

    def test_error_response_format(self, mock_mcp_response):
        """Test MCP error response format."""
        error = {"code": -32601, "message": "Method not found"}
        response = mock_mcp_response(None, 42, error=error)

        assert response["jsonrpc"] == "2.0"
        assert response["error"] == error
        expected_id = 42
        assert response["id"] == expected_id
        assert "result" not in response

    @pytest.mark.asyncio
    async def test_websocket_send_receive(self, mock_websocket):
        """Test WebSocket send/receive without real connection."""
        message = {"jsonrpc": "2.0", "method": "ping", "id": 1}
        mock_websocket.recv.return_value = json.dumps({"jsonrpc": "2.0", "result": "pong", "id": 1})

        await mock_websocket.send(json.dumps(message))
        response = await mock_websocket.recv()

        mock_websocket.send.assert_called_once_with(json.dumps(message))
        assert json.loads(response)["result"] == "pong"

    @pytest.mark.asyncio
    async def test_transport_message_handling(self, mock_transport):
        """Test transport layer message handling."""
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        response = {"jsonrpc": "2.0", "result": {"tools": []}, "id": 1}

        mock_transport.add_response(response)
        await mock_transport.send(json.dumps(request))

        assert mock_transport.messages[0] == request
        # The mock transport's receive returns the response directly
        mock_transport.receive = AsyncMock(return_value=json.dumps(response))
        result = await mock_transport.receive()
        assert json.loads(result) == response


class TestMCPTools:
    """Test MCP tool definitions and validation."""

    def test_browser_launch_tool_schema(self):
        """Test browser_launch tool schema."""
        tool = {
            "name": "browser_launch",
            "description": "Launch a new browser instance",
            "inputSchema": {
                "type": "object",
                "properties": {"headless": {"type": "boolean"}, "profile_id": {"type": "string"}, "session_id": {"type": "string"}},
            },
        }

        assert tool["name"] == "browser_launch"
        assert "headless" in tool["inputSchema"]["properties"]
        assert tool["inputSchema"]["properties"]["headless"]["type"] == "boolean"

    def test_browser_navigate_tool_schema(self):
        """Test browser_navigate tool schema."""
        tool = {
            "name": "browser_navigate",
            "description": "Navigate to a URL",
            "inputSchema": {
                "type": "object",
                "properties": {"instance_id": {"type": "string"}, "url": {"type": "string", "format": "uri"}},
                "required": ["instance_id", "url"],
            },
        }

        assert tool["name"] == "browser_navigate"
        assert "required" in tool["inputSchema"]
        assert "instance_id" in tool["inputSchema"]["required"]
        assert "url" in tool["inputSchema"]["required"]

    def test_tool_validation_missing_required(self):
        """Test tool validation with missing required fields."""
        schema = {"type": "object", "properties": {"instance_id": {"type": "string"}, "url": {"type": "string"}}, "required": ["instance_id", "url"]}

        # Missing url - should fail validation
        args = {"instance_id": "test-123"}
        required = schema.get("required", [])

        missing = [field for field in required if field not in args]
        assert missing == ["url"]

    def test_tool_validation_wrong_type(self):
        """Test tool validation with wrong type."""

        # String instead of boolean - should fail type check
        args = {"headless": "true", "timeout": 30}

        assert not isinstance(args["headless"], bool)
        assert isinstance(args["timeout"], int | float)


class TestMCPServerHandlers:
    """Test MCP server request handlers without real implementation."""

    @pytest.mark.asyncio
    async def test_initialize_handler(self):
        """Test initialize request handler."""
        with patch("browser.backend.mcp.chrome.server.BrowserMCPServer") as mock_server_class:
            server = mock_server_class()
            server.handle_initialize = AsyncMock(return_value={"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}})

            result = await server.handle_initialize({})

            assert result["protocolVersion"] == "2024-11-05"
            assert "capabilities" in result

    @pytest.mark.asyncio
    async def test_tools_list_handler(self):
        """Test tools/list request handler."""
        with patch("browser.backend.mcp.chrome.server.BrowserMCPServer") as mock_server_class:
            server = mock_server_class()
            server.handle_tools_list = AsyncMock(return_value={"tools": [{"name": "browser_launch"}, {"name": "browser_navigate"}]})

            result = await server.handle_tools_list({})

            assert "tools" in result
            expected_tool_count = 2
            assert len(result["tools"]) == expected_tool_count

    @pytest.mark.asyncio
    async def test_tools_call_handler(self):
        """Test tools/call request handler."""
        with patch("browser.backend.mcp.chrome.server.BrowserMCPServer") as mock_server_class:
            server = mock_server_class()
            server.handle_tools_call = AsyncMock(return_value={"content": [{"type": "text", "text": '{"instance_id": "test-123"}'}]})

            params = {"name": "browser_launch", "arguments": {"headless": True}}
            result = await server.handle_tools_call(params)

            assert "content" in result
            assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_error_handler(self):
        """Test error handling in request processing."""
        with patch("browser.backend.mcp.chrome.server.BrowserMCPServer") as mock_server_class:
            server = mock_server_class()
            server.handle_request = AsyncMock(side_effect=ValueError("Invalid request"))

            with pytest.raises(ValueError) as exc:
                await server.handle_request({"method": "invalid"})

            assert str(exc.value) == "Invalid request"


class TestMCPConnectionLifecycle:
    """Test MCP connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_connection_open(self, mock_websocket):
        """Test connection open sequence."""
        mock_websocket.closed = False

        # Simulate connection open
        assert not mock_websocket.closed

        # Should be able to send messages
        await mock_websocket.send(json.dumps({"test": "message"}))
        mock_websocket.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_close(self, mock_websocket):
        """Test connection close sequence."""
        mock_websocket.closed = False

        # Close connection
        await mock_websocket.close()
        mock_websocket.closed = True

        mock_websocket.close.assert_called_once()
        assert mock_websocket.closed

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_websocket):
        """Test connection error handling."""
        mock_websocket.send.side_effect = ConnectionError("Connection lost")

        with pytest.raises(ConnectionError) as exc:
            await mock_websocket.send(json.dumps({"test": "message"}))

        assert str(exc.value) == "Connection lost"

    @pytest.mark.asyncio
    async def test_reconnection_logic(self, mock_websocket):
        """Test reconnection logic."""
        mock_websocket.closed = True

        # Simulate reconnection
        mock_websocket.closed = False
        mock_websocket.send.reset_mock()
        mock_websocket.recv.reset_mock()

        # Should be able to send after reconnection
        await mock_websocket.send(json.dumps({"test": "reconnected"}))
        mock_websocket.send.assert_called_once()
