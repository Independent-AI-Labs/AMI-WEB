#!/usr/bin/env python
"""Run Chrome MCP server with stdio transport (for Claude Desktop)."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from loguru import logger

from backend.core.management.manager import ChromeManager
from backend.mcp.browser.server import BrowserMCPServer

# Configure minimal logging to stderr only
log_level = os.environ.get("MCP_LOG_LEVEL", "WARNING")
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stderr)])

# Configure loguru
logger.remove()
if log_level == "DEBUG":
    logger.add(sys.stderr, level="DEBUG")


async def main():
    """Run Chrome MCP server with stdio transport."""
    # Initialize Chrome Manager
    project_root = Path(__file__).parent.parent.parent.parent.resolve()
    config_file = project_root / "config.yaml"

    if config_file.exists():
        logger.info(f"Using config file: {config_file}")
        manager = ChromeManager(config_file=str(config_file))
    else:
        logger.info("Using default Chrome Manager configuration")
        manager = ChromeManager()

    await manager.initialize()

    # Set pool to not create instances on startup
    manager.pool.min_instances = 0
    manager.pool.warm_instances = 0

    # Create and run MCP server
    server = BrowserMCPServer(manager)

    try:
        await server.run_stdio()
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
