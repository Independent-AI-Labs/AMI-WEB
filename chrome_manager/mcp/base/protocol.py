"""Protocol handlers for MCP servers."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from loguru import logger


class BaseProtocolHandler(ABC):
    """Abstract base class for protocol handlers."""

    @abstractmethod
    async def handle_request(self, request: dict, method_resolver: Callable[[str], Callable | None]) -> dict | None:
        """Handle a protocol request.

        Args:
            request: The request data
            method_resolver: Function to resolve method handlers

        Returns:
            Response dictionary or None
        """

    @abstractmethod
    def format_error(self, code: int, message: str, request_id: Any = None) -> dict:
        """Format an error response.

        Args:
            code: Error code
            message: Error message
            request_id: Request ID

        Returns:
            Error response dictionary
        """

    @abstractmethod
    def format_response(self, result: Any, request_id: Any = None) -> dict:
        """Format a successful response.

        Args:
            result: The result data
            request_id: Request ID

        Returns:
            Response dictionary
        """

    @abstractmethod
    def format_notification(self, method: str, params: dict) -> dict:
        """Format a notification (no response expected).

        Args:
            method: Notification method
            params: Notification parameters

        Returns:
            Notification dictionary
        """


class JSONRPCHandler(BaseProtocolHandler):
    """JSON-RPC 2.0 protocol handler."""

    async def handle_request(self, request: dict, method_resolver: Callable[[str], Callable | None]) -> dict | None:
        """Handle a JSON-RPC request.

        Args:
            request: The JSON-RPC request
            method_resolver: Function to resolve method handlers

        Returns:
            JSON-RPC response or None for notifications
        """
        # Validate JSON-RPC request
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return self.format_error(-32600, "Invalid Request", request.get("id"))

        method = request.get("method")
        if not method:
            return self.format_error(-32600, "Invalid Request - missing method", request.get("id"))

        params = request.get("params", {})
        request_id = request.get("id")

        # Get method handler
        handler = method_resolver(method)
        if not handler:
            return self.format_error(-32601, f"Method not found: {method}", request_id)

        try:
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(params, request_id)
            else:
                result = handler(params, request_id)

            # Don't return response for notifications (no id)
            if request_id is None:
                return None

            return self.format_response(result, request_id)

        except Exception as e:
            logger.error(f"Error executing method {method}: {e}")
            return self.format_error(-32603, f"Internal error: {str(e)}", request_id)

    def format_error(self, code: int, message: str, request_id: Any = None) -> dict:
        """Format a JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            request_id: Request ID

        Returns:
            JSON-RPC error response
        """
        return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id}

    def format_response(self, result: Any, request_id: Any = None) -> dict:
        """Format a JSON-RPC successful response.

        Args:
            result: The result data
            request_id: Request ID

        Returns:
            JSON-RPC response
        """
        return {"jsonrpc": "2.0", "result": result, "id": request_id}

    def format_notification(self, method: str, params: dict) -> dict:
        """Format a JSON-RPC notification.

        Args:
            method: Notification method
            params: Notification parameters

        Returns:
            JSON-RPC notification
        """
        return {"jsonrpc": "2.0", "method": method, "params": params}


class MCPProtocolHandler(JSONRPCHandler):
    """MCP-specific protocol handler extending JSON-RPC."""

    def __init__(self):
        """Initialize MCP protocol handler."""
        super().__init__()
        self.protocol_version = "2024-11-05"

    async def handle_request(self, request: dict, method_resolver: Callable[[str], Callable | None]) -> dict | None:
        """Handle an MCP request with special handling for MCP methods.

        Args:
            request: The request data
            method_resolver: Function to resolve method handlers

        Returns:
            Response dictionary or None
        """
        method = request.get("method")

        # Handle MCP-specific methods
        if method == "initialize":
            return self._handle_initialize(request.get("id"))

        # Delegate to JSON-RPC handler
        return await super().handle_request(request, method_resolver)

    def _handle_initialize(self, request_id: Any) -> dict:
        """Handle MCP initialize request.

        Args:
            request_id: Request ID

        Returns:
            Initialize response
        """
        return self.format_response(
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "mcp-base-server",
                    "version": "1.0.0",
                },
            },
            request_id,
        )
