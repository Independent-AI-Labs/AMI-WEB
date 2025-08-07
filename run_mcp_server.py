#!/usr/bin/env python
"""Standalone MCP server launcher for Chrome Manager."""

import argparse
import asyncio
import contextlib

from loguru import logger

from chrome_manager.core.manager import ChromeManager
from chrome_manager.mcp.server import MCPServer


async def main(host: str = "localhost", port: int = 8765):
    """Start the MCP server with configurable host and port."""
    # Initialize Chrome Manager
    logger.info("Initializing Chrome Manager...")
    manager = ChromeManager()
    await manager.start()

    # Configure MCP server
    config = {"server_host": host, "server_port": port, "max_connections": 10}

    # Start MCP server
    logger.info(f"Starting MCP Server on {host}:{port}...")
    server = MCPServer(manager, config)
    await server.start()

    logger.info(f"MCP Server running on ws://{host}:{port}")
    logger.info("Available tools: browser_launch, browser_navigate, browser_click, browser_type, browser_screenshot, and more...")
    logger.info("Press Ctrl+C to stop")

    try:
        # Keep server running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await server.stop()
        await manager.shutdown()
        logger.info("Server stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chrome Manager MCP Server")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    args = parser.parse_args()

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(args.host, args.port))
