#!/usr/bin/env python
"""Stdio-based MCP server for Chrome Manager following the MCP specification."""

import asyncio
import json

# Add logging to stderr only
import logging
import os
import sys
import uuid
from typing import Any

# Get log level from environment or default to WARNING for production
log_level = os.environ.get("MCP_LOG_LEVEL", "WARNING")
logging.basicConfig(
    level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Also configure loguru to be quiet
from loguru import logger as loguru_logger  # noqa: E402

loguru_logger.remove()
if log_level == "DEBUG":
    loguru_logger.add(sys.stderr, level="DEBUG")

# Import Chrome Manager components
try:
    from chrome_manager.core.manager import ChromeManager
    from chrome_manager.mcp.server import MCPServer
except ImportError as e:
    logger.error(f"Failed to import Chrome Manager: {e}")
    sys.exit(1)


class StdioTransport:
    """Handle stdio transport for JSON-RPC messages."""

    async def read_message(self) -> dict | None:
        """Read a JSON-RPC message from stdin."""
        try:
            line = sys.stdin.readline()
            if not line:
                return None

            message = json.loads(line.strip())
            logger.debug(f"Received: {json.dumps(message)[:200]}")
            return message
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            # For parse errors, we should send an error with id: null per JSON-RPC spec
            # But MCP/Claude Desktop doesn't handle this well, so we just log and skip
            return None
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None

    async def send_message(self, message: dict):
        """Send a JSON-RPC message to stdout."""
        try:
            json_str = json.dumps(message)
            print(json_str, flush=True)
            logger.debug(f"Sent: {json_str[:200]}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def send_error(self, request_id: Any, code: int, message: str, data: Any = None):
        """Send a JSON-RPC error response."""
        # JSON-RPC spec requires id to be present and match the request
        # If request_id is None, we can't send a proper error response
        if request_id is None:
            # Log the error but don't send a response for notifications
            logger.error(f"Error without request ID: {code} - {message}")
            return

        error_response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
        if data is not None:
            error_response["error"]["data"] = data
        await self.send_message(error_response)

    async def send_result(self, request_id: Any, result: Any):
        """Send a JSON-RPC success response."""
        await self.send_message({"jsonrpc": "2.0", "id": request_id, "result": result})


class ChromeManagerMCPServer:
    """MCP server for Chrome Manager."""

    def __init__(self):
        self.transport = StdioTransport()
        self.manager: ChromeManager | None = None
        self.mcp_server: MCPServer | None = None
        self.initialized = False

    async def handle_initialize(self, request_id: Any, params: dict) -> None:  # noqa: ARG002
        """Handle initialize request."""
        try:
            # Initialize Chrome Manager if not already done
            if not self.manager:
                logger.info("Initializing Chrome Manager...")

                # Look for config file in project root
                from pathlib import Path

                # Get project root (two levels up from chrome_manager/mcp/)
                project_root = Path(__file__).parent.parent.parent.resolve()
                config_file = project_root / "config.yaml"

                if config_file.exists():
                    logger.info(f"Using config file: {config_file}")
                    self.manager = ChromeManager(config_file=str(config_file))
                else:
                    logger.warning(f"Config file not found at {config_file}, using defaults")
                    self.manager = ChromeManager()

                # Initialize the manager first
                await self.manager.initialize()

                # Set pool to not create instances on startup (after initialization)
                self.manager.pool.min_instances = 0
                self.manager.pool.warm_instances = 0

                # Create MCP server wrapper
                self.mcp_server = MCPServer(self.manager, {})
                logger.info("Chrome Manager initialized successfully")

            self.initialized = True

            # Send initialize response
            await self.transport.send_result(
                request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "chrome-manager", "version": "1.0.0"}}
            )

            # Send initialized notification
            await self.transport.send_message({"jsonrpc": "2.0", "method": "notifications/initialized"})

        except Exception as e:
            logger.error(f"Initialize failed: {e}", exc_info=True)
            await self.transport.send_error(request_id, -32603, f"Internal error: {str(e)}")

    async def handle_tools_list(self, request_id: Any, params: dict) -> None:  # noqa: ARG002
        """Handle tools/list request."""
        if not self.initialized or not self.mcp_server:
            await self.transport.send_error(request_id, -32002, "Server not initialized")
            return

        try:
            tools = []
            for tool_name, tool in self.mcp_server.tools.items():
                tools.append({"name": tool_name, "description": tool.description, "inputSchema": tool.parameters})

            await self.transport.send_result(request_id, {"tools": tools})

        except Exception as e:
            logger.error(f"Tools list failed: {e}", exc_info=True)
            await self.transport.send_error(request_id, -32603, f"Internal error: {str(e)}")

    async def handle_tools_call(self, request_id: Any, params: dict) -> None:
        """Handle tools/call request."""
        if not self.initialized or not self.mcp_server:
            await self.transport.send_error(request_id, -32002, "Server not initialized")
            return

        try:
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            logger.info(f"Executing tool: {tool_name}")

            # Make browser headful by default for browser_launch
            if tool_name == "browser_launch" and "headless" not in tool_params:
                tool_params["headless"] = False
                logger.info("Setting headless=False for browser_launch")

            # Execute the tool
            response = await self.mcp_server._handle_tool_request(
                {"type": "tool", "tool": tool_name, "parameters": tool_params, "request_id": str(uuid.uuid4())}
            )

            if response.get("success"):
                # Send successful result
                result = response.get("result", {})
                await self.transport.send_result(request_id, {"content": [{"type": "text", "text": json.dumps(result)}]})
            else:
                # Send error
                error_msg = response.get("error", "Tool execution failed")
                await self.transport.send_error(request_id, -32000, error_msg)

        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            await self.transport.send_error(request_id, -32603, f"Internal error: {str(e)}")

    async def handle_request(self, message: dict) -> None:
        """Handle a JSON-RPC request."""
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        logger.info(f"Handling request: {method} (id: {request_id})")

        # Route to appropriate handler
        if method == "initialize":
            await self.handle_initialize(request_id, params)
        elif method == "tools/list":
            await self.handle_tools_list(request_id, params)
        elif method == "tools/call":
            await self.handle_tools_call(request_id, params)
        elif method == "notifications/cancelled":
            # Handle cancellation
            logger.info(f"Request {params.get('requestId')} cancelled")
        else:
            await self.transport.send_error(request_id, -32601, f"Method not found: {method}")

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("Chrome Manager MCP Server starting...")

        try:
            while True:
                message = await self.transport.read_message()
                if message is None:
                    logger.info("Input closed, shutting down...")
                    break

                # Validate JSON-RPC format
                if "jsonrpc" not in message or message["jsonrpc"] != "2.0":
                    await self.transport.send_error(message.get("id"), -32600, "Invalid Request: missing or invalid jsonrpc field")
                    continue

                # Handle the request
                await self.handle_request(message)

        except KeyboardInterrupt:
            logger.info("Server interrupted")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            # Cleanup
            if self.manager:
                logger.info("Shutting down Chrome Manager...")
                await self.manager.shutdown()
            logger.info("Server stopped")


async def main():
    """Main entry point."""
    server = ChromeManagerMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        # Run the server
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
