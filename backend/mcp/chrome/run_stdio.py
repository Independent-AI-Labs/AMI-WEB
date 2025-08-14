#!/usr/bin/env python
"""Run Chrome MCP server with stdio transport (for Claude Desktop)."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure environment is set up
project_root = Path(__file__).parent.parent.parent.parent.resolve()
venv_path = project_root / ".venv"

# Add project root to path
sys.path.insert(0, str(project_root))

# Check if virtual environment exists, if not run setup
if not venv_path.exists():
    print("Setting up environment...", file=sys.stderr)
    from setup import run_environment_setup

    result = run_environment_setup()
    if result != 0:
        print("Failed to set up environment", file=sys.stderr)
        sys.exit(1)

# Ensure base module is available
from setup import ensure_base_module  # noqa: E402

ensure_base_module()

# IMPORTANT: Re-add browser directory to front of path to avoid namespace collision
# ensure_base_module() adds parent directory at position 0, which contains a different 'backend' module
if str(project_root) in sys.path:
    sys.path.remove(str(project_root))
sys.path.insert(0, str(project_root))

from loguru import logger  # noqa: E402

from backend.core.management.manager import ChromeManager  # noqa: E402
from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402

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
