#!/usr/bin/env python
"""Run Chrome MCP server with stdio transport (for Claude Desktop)."""

import asyncio
import sys
from pathlib import Path

# Add parent paths to find base module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from base.backend.mcp.generic.run_stdio import main as run_stdio_main  # noqa: E402
from base.backend.mcp.generic.runner import init_environment  # noqa: E402
from loguru import logger  # noqa: E402

# Initialize environment
module_root, config_file = init_environment(Path(__file__))

from backend.core.management.manager import ChromeManager  # noqa: E402
from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402


async def create_manager_and_server():
    """Create and initialize Chrome Manager and MCP Server."""
    if config_file:
        logger.info(f"Using config file: {config_file}")
        manager = ChromeManager(config_file=str(config_file))
    else:
        logger.info("Using default Chrome Manager configuration")
        manager = ChromeManager()

    await manager.initialize()

    # Set pool to not create instances on startup
    manager.pool.min_instances = 0
    manager.pool.warm_instances = 0

    # Create server with manager
    server_args = {"manager": manager}

    # Define cleanup callback
    async def cleanup():
        await manager.shutdown()

    return BrowserMCPServer, server_args, cleanup


if __name__ == "__main__":
    # Run the async setup and then use base stdio runner
    server_class, server_args, cleanup = asyncio.run(create_manager_and_server())

    # Use the base run_stdio implementation
    run_stdio_main(server_class=server_class, server_args=server_args, config_file=config_file, cleanup_callback=cleanup)
