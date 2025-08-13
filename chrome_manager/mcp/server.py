"""MCP Server implementation for browser automation."""

import json
from collections.abc import Callable
from typing import Any

from loguru import logger

from chrome_manager.core import ChromeManager
from chrome_manager.mcp.base import AsyncExecutor, BaseMCPServer
from chrome_manager.mcp.tools import ToolRegistry
from chrome_manager.mcp.tools.definitions import register_all_tools
from chrome_manager.mcp.tools.executor import ToolExecutor


class MCPServer(BaseMCPServer):
    """Model Context Protocol server for browser automation."""

    def __init__(self, manager: ChromeManager, config: dict | None = None):
        """Initialize MCP server with Chrome manager.

        Args:
            manager: Chrome manager instance
            config: Server configuration
        """
        super().__init__(config)
        self.manager = manager
        self.async_executor = AsyncExecutor()

        # Initialize tool registry and executor
        self.registry = ToolRegistry()
        register_all_tools(self.registry)
        self.executor = ToolExecutor(manager)

        logger.info(f"Initialized MCP server with {len(self.registry.list_tools())} tools")

    def get_method_handler(self, method: str) -> Callable | None:
        """Get handler for a specific method.

        Args:
            method: The method name

        Returns:
            Handler function or None if not found
        """
        # Map method to handler
        handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_tool_call,
            "ping": self._handle_ping,
        }
        return handlers.get(method)

    async def _handle_request(self, context: dict[str, Any], request: dict) -> dict | None:  # noqa: ARG002
        """Handle a request with method routing.

        Args:
            context: Connection context
            request: The request data

        Returns:
            Response dictionary or None
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Get handler using base class method resolution
        handler = self.get_method_handler(method)
        if not handler:
            return self.protocol_handler.format_error(-32601, f"Method not found: {method}", request_id)

        try:
            # Execute handler
            result = await handler(params, request_id)
            if request_id is None:
                return None  # No response for notifications
            return result
        except Exception as e:
            logger.error(f"Error executing method {method}: {e}")
            return self.protocol_handler.format_error(-32603, f"Internal error: {str(e)}", request_id)

    async def _handle_initialize(self, params: dict, request_id: Any) -> dict:  # noqa: ARG002
        """Handle initialize request.

        Args:
            params: Request parameters
            request_id: Request ID

        Returns:
            Initialize response
        """
        return self.protocol_handler.format_response(
            {
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
            request_id,
        )

    async def _handle_list_tools(self, params: dict, request_id: Any) -> dict:  # noqa: ARG002
        """Handle tools/list request.

        Args:
            params: Request parameters
            request_id: Request ID

        Returns:
            Tools list response
        """
        tools = self.registry.to_mcp_format()
        return self.protocol_handler.format_response({"tools": tools}, request_id)

    async def _handle_tool_call(self, params: dict, request_id: Any) -> dict:
        """Handle tools/call request.

        Args:
            params: Request parameters with 'name' and 'arguments'
            request_id: Request ID

        Returns:
            Tool execution response
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return self.protocol_handler.format_error(-32602, "Missing tool name", request_id)

        # Check if tool exists
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return self.protocol_handler.format_error(-32602, f"Unknown tool: {tool_name}", request_id)

        try:
            # Execute the tool
            result = await self.executor.execute(tool_name, arguments)

            # Format response
            content = self._format_tool_response(tool_name, result)

            return self.protocol_handler.format_response({"content": content}, request_id)

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return self.protocol_handler.format_error(-32603, f"Tool execution failed: {str(e)}", request_id)

    def _format_tool_response(self, tool_name: str, result: dict) -> list[dict]:  # noqa: ARG002
        """Format tool response for MCP protocol."""
        # Always return as JSON for consistent parsing in tests
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async def _handle_ping(self, params: dict, request_id: Any) -> dict:  # noqa: ARG002
        """Handle ping request.

        Args:
            params: Request parameters
            request_id: Request ID

        Returns:
            Pong response
        """
        return self.protocol_handler.format_response({"status": "pong"}, request_id)
