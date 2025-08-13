"""Base MCP server with built-in transport support and protocol handling."""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

import websockets
from loguru import logger

from .auth import AuthenticationMiddleware
from .protocol import JSONRPCHandler
from .rate_limit import RateLimitMiddleware
from .transport import StdioTransport, WebSocketTransport


class BaseMCPServer(ABC):
    """Base MCP server with complete protocol and transport support.

    Subclasses only need to:
    1. Implement register_tools() to define their tools
    2. Implement execute_tool() to handle tool execution
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the base MCP server.

        Args:
            config: Server configuration
        """
        self.config = config or {}
        self._websocket_server: Any = None
        self._connections: set[Any] = set()

        # Initialize protocol handler
        self.protocol_handler = JSONRPCHandler()

        # Setup middlewares
        self._auth_middleware = None
        self._rate_limit_middleware = None
        self._setup_middlewares()

        # Tool registry - populated by subclass
        self.tools: dict[str, dict] = {}

        # Register tools from subclass
        self.register_tools()

        middleware_count = sum(1 for m in [self._auth_middleware, self._rate_limit_middleware] if m)
        logger.info(f"Initialized {self.__class__.__name__} with {len(self.tools)} tools and {middleware_count} middlewares")

    def _setup_middlewares(self):
        """Setup server middlewares based on configuration."""
        # Authentication middleware
        if self.config.get("auth_enabled", False):
            auth_tokens = self.config.get("auth_tokens", [])
            if auth_tokens:
                self._auth_middleware = AuthenticationMiddleware(auth_tokens)
                logger.info(f"Authentication enabled with {len(auth_tokens)} tokens")

        # Rate limiting middleware
        if self.config.get("rate_limit_enabled", False):
            max_requests = self.config.get("rate_limit_requests", 100)
            window_seconds = self.config.get("rate_limit_window", 60)
            self._rate_limit_middleware = RateLimitMiddleware(max_requests, window_seconds)
            logger.info(f"Rate limiting enabled: {max_requests} requests per {window_seconds} seconds")

    @abstractmethod
    def register_tools(self) -> None:
        """Register tools available in this server.

        Subclasses should populate self.tools with:
        {
            "tool_name": {
                "description": "Tool description",
                "inputSchema": {...}  # JSON Schema
            }
        }
        """

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """

    # Transport methods

    async def run_stdio(self) -> None:
        """Run the server using stdio transport (for Claude Desktop)."""
        logger.info("Starting MCP server with stdio transport")
        transport = StdioTransport()

        try:
            while True:
                request = await transport.receive()
                if request is None:
                    break

                response = await self._handle_request(request, "stdio")
                if response:
                    await transport.send(response)

        except KeyboardInterrupt:
            logger.info("Server interrupted")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await transport.close()
            logger.info("Stdio server stopped")

    async def run_websocket(self, host: str = "localhost", port: int = 8765) -> None:
        """Run the server using WebSocket transport.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info(f"Starting MCP server on ws://{host}:{port}")

        async def handle_connection(websocket, path=None):  # noqa: ARG001
            """Handle a WebSocket connection."""
            transport = WebSocketTransport(websocket)
            self._connections.add(websocket)
            logger.info(f"New connection from {websocket.remote_address}")

            try:
                while True:
                    request = await transport.receive()
                    if request is None:
                        break

                    # Check for parse error
                    if isinstance(request, dict) and "__parse_error__" in request:
                        response = self._format_error(-32700, "Parse error", None)
                        await transport.send(response)
                        continue

                    # Use websocket address as client ID for rate limiting
                    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else None
                    response = await self._handle_request(request, client_id)
                    if response:
                        await transport.send(response)

            except Exception as e:
                logger.error(f"Connection error: {e}")
            finally:
                self._connections.discard(websocket)
                await transport.close()
                logger.info(f"Connection closed from {websocket.remote_address}")

        async with websockets.serve(handle_connection, host, port):
            logger.info(f"WebSocket server listening on ws://{host}:{port}")
            await asyncio.Event().wait()

    async def start(self, host: str | None = None, port: int | None = None) -> None:
        """Start the WebSocket server (for compatibility with tests).

        Args:
            host: Host to bind to (uses config if not provided)
            port: Port to bind to (uses config if not provided)
        """
        host = host or self.config.get("server_host", "localhost")
        port = port or self.config.get("server_port", 8765)
        max_size = self.config.get("max_message_size", 10 * 1024 * 1024)

        self._websocket_server = await websockets.serve(
            self._handle_websocket_connection,
            host,
            port,
            max_size=max_size,
        )

        logger.info(f"{self.__class__.__name__} started on ws://{host}:{port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()

        # Close all connections
        for ws in self._connections:
            await ws.close()
        self._connections.clear()

        logger.info(f"{self.__class__.__name__} stopped")

    async def _handle_websocket_connection(self, websocket, path=None):  # noqa: ARG002
        """Handle a WebSocket connection for start/stop mode."""
        transport = WebSocketTransport(websocket)
        self._connections.add(websocket)
        logger.info(f"New connection from {websocket.remote_address}")

        try:
            while True:
                request = await transport.receive()
                if request is None:
                    break

                # Check for parse error
                if isinstance(request, dict) and "__parse_error__" in request:
                    response = self._format_error(-32700, "Parse error", None)
                    await transport.send(response)
                    continue

                # Use websocket address as client ID for rate limiting
                client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}" if websocket.remote_address else None
                response = await self._handle_request(request, client_id)
                if response:
                    await transport.send(response)

        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            self._connections.discard(websocket)
            logger.info(f"Connection closed from {websocket.remote_address}")

    # Protocol handling

    async def _apply_middlewares(self, request: dict[str, Any], client_id: str | None = None) -> dict[str, Any] | None:
        """Apply middleware checks to a request.

        Args:
            request: The request to check
            client_id: Client identifier for rate limiting

        Returns:
            Error response if middleware check fails, None otherwise
        """
        # Apply authentication
        if self._auth_middleware:
            auth_result = await self._auth_middleware.process(request)
            if auth_result:
                return auth_result

        # Apply rate limiting
        if self._rate_limit_middleware and client_id:
            rate_result = await self._rate_limit_middleware.process(request, client_id)
            if rate_result:
                return rate_result

        return None

    async def _handle_request(self, request: dict, client_id: str | None = None) -> dict | None:
        """Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request
            client_id: Client identifier for middleware

        Returns:
            JSON-RPC response or None for notifications
        """
        # Apply middlewares first
        middleware_response = await self._apply_middlewares(request, client_id)
        if middleware_response:
            return middleware_response

        # Validate JSON-RPC format
        if request.get("jsonrpc") != "2.0":
            return self._format_error(-32600, "Invalid Request: missing or invalid jsonrpc field", request.get("id"))

        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Route to appropriate handler
        try:
            # Handle notification (no response needed)
            if method == "notifications/cancelled":
                logger.info(f"Request {params.get('requestId')} cancelled")
                return None

            # Get handler for method
            handler_map = {
                "initialize": self._handle_initialize,
                "tools/list": self._handle_tools_list,
                "tools/call": self._handle_tools_call,
                "ping": lambda p: {"status": "pong"},  # noqa: ARG005
            }

            handler = handler_map.get(method)
            if not handler:
                return self._format_error(-32601, f"Method not found: {method}", request_id)

            # Execute handler
            result = await handler(params) if asyncio.iscoroutinefunction(handler) else handler(params)

            # Return response if not a notification
            return self._format_response(result, request_id) if request_id is not None else None

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._format_error(-32603, f"Internal error: {str(e)}", request_id)

    async def _handle_initialize(self, params: dict) -> dict:  # noqa: ARG002
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "serverInfo": {
                "name": self.__class__.__name__,
                "version": "1.0.0",
            },
        }

    async def _handle_tools_list(self, params: dict) -> dict:  # noqa: ARG002
        """Handle tools/list request."""
        tools = []
        for name, info in self.tools.items():
            tools.append({"name": name, "description": info["description"], "inputSchema": info.get("inputSchema", {})})
        return {"tools": tools}

    async def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Missing tool name")

        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Execute the tool
        result = await self.execute_tool(tool_name, arguments)

        # Format response for MCP
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    def _format_response(self, result: Any, request_id: Any) -> dict:
        """Format a JSON-RPC success response."""
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _format_error(self, code: int, message: str, request_id: Any) -> dict:
        """Format a JSON-RPC error response."""
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
