"""Base MCP server implementation with middleware support."""

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import websockets
from loguru import logger

from .auth import AuthenticationMiddleware
from .protocol import JSONRPCHandler
from .rate_limit import RateLimitMiddleware


class BaseMCPServer(ABC):
    """Base class for MCP servers with middleware support."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the base MCP server.

        Args:
            config: Server configuration including:
                - server_host: Host to bind to (default: localhost)
                - server_port: Port to bind to (default: 8765)
                - max_message_size: Max WebSocket message size (default: 10MB)
                - auth_enabled: Enable authentication (default: False)
                - auth_tokens: List of valid auth tokens
                - rate_limit_enabled: Enable rate limiting (default: False)
                - rate_limit_requests: Max requests per window (default: 100)
                - rate_limit_window: Time window in seconds (default: 60)
        """
        self.config = config or {}
        self._websocket_server = None
        self._connections: set[Any] = set()
        self._middlewares: list[Callable] = []

        # Initialize protocol handler
        self.protocol_handler = JSONRPCHandler()

        # Setup middlewares
        self._setup_middlewares()

        logger.info(f"Initialized {self.__class__.__name__} with {len(self._middlewares)} middlewares")

    def _setup_middlewares(self):
        """Setup server middlewares based on configuration."""
        # Authentication middleware
        if self.config.get("auth_enabled", False):
            auth_tokens = self.config.get("auth_tokens", [])
            if not auth_tokens:
                logger.warning("Authentication enabled but no tokens configured")
            auth_middleware = AuthenticationMiddleware(auth_tokens)
            self._middlewares.append(auth_middleware.process)
            logger.info(f"Authentication middleware enabled with {len(auth_tokens)} tokens")

        # Rate limiting middleware
        if self.config.get("rate_limit_enabled", False):
            max_requests = self.config.get("rate_limit_requests", 100)
            window_seconds = self.config.get("rate_limit_window", 60)
            rate_limiter = RateLimitMiddleware(max_requests, window_seconds)
            self._middlewares.append(rate_limiter.process)
            logger.info(f"Rate limiting enabled: {max_requests} requests per {window_seconds}s")

    async def start(self):
        """Start the WebSocket server."""
        host = self.config.get("server_host", "localhost")
        port = self.config.get("server_port", 8765)
        max_size = self.config.get("max_message_size", 10 * 1024 * 1024)

        self._websocket_server = await websockets.serve(
            self._handle_connection,
            host,
            port,
            max_size=max_size,
        )

        logger.info(f"{self.__class__.__name__} started on ws://{host}:{port}")

    async def stop(self):
        """Stop the WebSocket server."""
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()

        # Close all connections
        for ws in self._connections:
            await ws.close()
        self._connections.clear()

        logger.info(f"{self.__class__.__name__} stopped")

    async def _handle_connection(self, websocket, path=None):  # noqa: ARG002
        """Handle a WebSocket connection with middleware processing."""
        self._connections.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"New connection from {client_addr}")

        # Create connection context
        context = {
            "websocket": websocket,
            "client_addr": client_addr,
            "authenticated": False,
            "rate_limiter": None,
        }

        try:
            async for message in websocket:
                try:
                    # Parse message
                    data = json.loads(message)

                    # Apply middlewares
                    for middleware in self._middlewares:
                        result = await middleware(context, data)
                        if result is not None:
                            # Middleware blocked the request
                            await websocket.send(json.dumps(result))
                            continue

                    # Handle the request
                    response = await self._handle_request(context, data)
                    if response:
                        await websocket.send(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = self.protocol_handler.format_error(-32700, f"Parse error: {e}", None)
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    error_response = self.protocol_handler.format_error(-32603, "Internal error", data.get("id") if isinstance(data, dict) else None)
                    await websocket.send(json.dumps(error_response))

        except websockets.ConnectionClosed:
            logger.info(f"Connection closed from {client_addr}")
        finally:
            self._connections.discard(websocket)

    async def _handle_request(self, context: dict[str, Any], request: dict) -> dict | None:  # noqa: ARG002
        """Handle a request after middleware processing.

        Args:
            context: Connection context
            request: The request data

        Returns:
            Response dictionary or None
        """
        return await self.protocol_handler.handle_request(request, self.get_method_handler)

    @abstractmethod
    def get_method_handler(self, method: str) -> Callable | None:
        """Get handler for a specific method.

        Args:
            method: The method name

        Returns:
            Handler function or None if not found
        """

    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients.

        Args:
            event_type: Type of event to broadcast
            data: Event data
        """
        message = self.protocol_handler.format_notification(event_type, data)

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
