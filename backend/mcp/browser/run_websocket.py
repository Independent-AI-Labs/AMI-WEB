#!/usr/bin/env python
"""Run Browser MCP server with WebSocket transport."""

import asyncio
import contextlib
import sys

from loguru import logger

from backend.core.management.manager import ChromeManager
from backend.mcp.browser.server import BrowserMCPServer


async def main(host: str = "localhost", port: int = 8765):
    """Run Browser MCP server with WebSocket transport.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    # Initialize Chrome Manager
    logger.info("Initializing Chrome Manager...")
    manager = ChromeManager()
    await manager.initialize()

    # Create and run MCP server
    server = BrowserMCPServer(manager)

    try:
        logger.info(f"Starting Browser MCP Server on ws://{host}:{port}")
        await server.run_websocket(host, port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        await manager.shutdown()
        logger.info("Chrome Manager shutdown complete")


if __name__ == "__main__":
    # Get host and port from command line or use defaults
    DEFAULT_PORT = 8765
    MIN_ARGS = 2
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > MIN_ARGS else DEFAULT_PORT

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(host, port))
