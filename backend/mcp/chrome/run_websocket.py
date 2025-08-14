#!/usr/bin/env python
"""Run Browser MCP server with WebSocket transport."""

import asyncio
import contextlib
import sys
from pathlib import Path

# Add parent paths to find base module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from base.backend.mcp.generic.run_websocket import main as run_websocket_main  # noqa: E402
from base.backend.mcp.generic.runner import init_environment  # noqa: E402
from loguru import logger  # noqa: E402

# Initialize environment
module_root, config_file = init_environment(Path(__file__))

from backend.core.management.manager import ChromeManager  # noqa: E402
from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402


async def create_manager_and_server():
    """Create and initialize Chrome Manager and MCP Server."""
    logger.info("Initializing Chrome Manager...")
    if config_file:
        logger.info(f"Using config file: {config_file}")
        manager = ChromeManager(config_file=str(config_file))
    else:
        logger.info("Using default Chrome Manager configuration")
        manager = ChromeManager()

    await manager.initialize()

    # Create server with manager
    server_args = {"manager": manager}

    # Define cleanup callback
    async def cleanup():
        await manager.shutdown()
        logger.info("Chrome Manager shutdown complete")

    return BrowserMCPServer, server_args, cleanup


if __name__ == "__main__":
    # Get host and port from command line or use defaults
    DEFAULT_PORT = 8765
    MIN_ARGS = 2
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > MIN_ARGS else DEFAULT_PORT

    # Run the async setup and then use base websocket runner
    server_class, server_args, cleanup = asyncio.run(create_manager_and_server())

    # Use the base run_websocket implementation
    with contextlib.suppress(KeyboardInterrupt):
        run_websocket_main(server_class=server_class, server_args=server_args, config_file=config_file, host=host, port=port, cleanup_callback=cleanup)
