"""MCP Server entry point for Chrome Manager."""

import asyncio
import contextlib
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger  # noqa: E402

from chrome_manager.core import ChromeManager  # noqa: E402
from chrome_manager.mcp.server import MCPServer  # noqa: E402


async def main():
    """Start the MCP server."""
    # Configure logging
    logger.add(sys.stderr, level="INFO")

    # Initialize Chrome Manager
    logger.info("Initializing Chrome Manager...")
    manager = ChromeManager()
    await manager.start()

    # Configure MCP server
    config = {"server_host": "localhost", "server_port": 8765, "max_connections": 10}

    # Start MCP server
    logger.info("Starting MCP Server...")
    server = MCPServer(manager, config)
    await server.start()

    logger.info("MCP Server running on ws://localhost:8765")
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
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
