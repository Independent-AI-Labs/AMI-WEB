"""Refactored MCP Server implementation using tool registry."""

import json
from typing import Any

import websockets
from loguru import logger

from chrome_manager.core import ChromeManager
from chrome_manager.mcp.tools import ToolRegistry
from chrome_manager.mcp.tools.definitions import register_all_tools
from chrome_manager.mcp.tools.executor import ToolExecutor


class MCPServer:
    """Model Context Protocol server for browser automation."""

    def __init__(self, manager: ChromeManager, config: dict | None = None):
        self.manager = manager
        self.config = config or {}
        self._websocket_server = None
        self._connections: set[Any] = set()

        # Initialize tool registry and executor
        self.registry = ToolRegistry()
        register_all_tools(self.registry)
        self.executor = ToolExecutor(manager)

        logger.info(f"Initialized MCP server with {len(self.registry.list_tools())} tools")

    async def start(self):
        """Start the WebSocket server."""
        host = self.config.get("server_host", "localhost")
        port = self.config.get("server_port", 8765)

        self._websocket_server = await websockets.serve(
            self._handle_connection,
            host,
            port,
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )

        logger.info(f"MCP server started on ws://{host}:{port}")

    async def stop(self):
        """Stop the WebSocket server."""
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()

        # Close all connections
        for ws in self._connections:
            await ws.close()
        self._connections.clear()

        logger.info("MCP server stopped")

    async def _handle_connection(self, websocket, path=None):  # noqa: ARG002
        """Handle a WebSocket connection."""
        self._connections.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"New connection from {client_addr}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self._handle_request(data)
                    if response:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                        "id": None,
                    }
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": "Internal error"},
                        "id": data.get("id") if isinstance(data, dict) else None,
                    }
                    await websocket.send(json.dumps(error_response))

        except websockets.ConnectionClosed:
            logger.info(f"Connection closed from {client_addr}")
        finally:
            self._connections.discard(websocket)

    async def _handle_request(self, request: dict) -> dict | None:  # noqa: RET505
        """Handle JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Handle different MCP methods
        if method == "initialize":
            return await self._handle_initialize(request_id)
        if method == "tools/list":
            return await self._handle_list_tools(request_id)
        if method == "tools/call":
            return await self._handle_tool_call(params, request_id)
        if method == "ping":
            return {"jsonrpc": "2.0", "result": {"status": "pong"}, "id": request_id}
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id,
        }

    async def _handle_initialize(self, request_id: Any) -> dict:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "chrome-manager-mcp",
                    "version": "1.0.0",
                },
            },
            "id": request_id,
        }

    async def _handle_list_tools(self, request_id: Any) -> dict:
        """Handle tools/list request."""
        tools = self.registry.to_mcp_format()
        return {
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": request_id,
        }

    async def _handle_tool_call(self, params: dict, request_id: Any) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Missing tool name"},
                "id": request_id,
            }

        # Check if tool exists
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
                "id": request_id,
            }

        try:
            # Execute the tool
            result = await self.executor.execute(tool_name, arguments)

            # Format response
            content = self._format_tool_response(tool_name, result)

            return {
                "jsonrpc": "2.0",
                "result": {"content": content},
                "id": request_id,
            }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"},
                "id": request_id,
            }

    def _format_tool_response(self, tool_name: str, result: dict) -> list[dict]:  # noqa: ARG002
        """Format tool response for MCP protocol."""
        # Convert result to MCP content format
        if "text" in result:
            return [{"type": "text", "text": result["text"]}]
        if "html" in result:
            return [{"type": "text", "text": f"```html\n{result['html']}\n```"}]
        if "screenshot" in result:
            # Return as JSON text for compatibility with tests
            # The actual base64 data is in the result
            return [{"type": "text", "text": json.dumps(result, indent=2)}]
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        # Default: return as JSON
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients."""
        message = {
            "jsonrpc": "2.0",
            "method": f"notifications/{event_type}",
            "params": data,
        }

        # Send to all connected clients
        disconnected = []
        for ws in self._connections:
            try:
                await ws.send(json.dumps(message))
            except websockets.ConnectionClosed:
                disconnected.append(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self._connections.discard(ws)
