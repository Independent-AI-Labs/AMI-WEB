#!/usr/bin/env python
"""Run Browser MCP server with stdio transport."""

import asyncio
import sys
from pathlib import Path

# Bootstrap paths - add base first so we can import smart_path
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / "base").exists() and (current / ".git").exists():
        sys.path.insert(0, str(current / "base"))
        break
    current = current.parent

# Now use the base smart path setup
from backend.utils.smart_path import auto_setup  # noqa: E402

# Auto setup with venv requirement
paths = auto_setup(require_venv=True)

from loguru import logger  # noqa: E402

from backend.core.management.manager import ChromeManager  # noqa: E402

# Import server directly from chrome directory
sys.path.insert(0, str(Path(__file__).parent))  # Add chrome directory
from server import BrowserMCPServer  # noqa: E402

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")


async def main():
    """Main entry point for stdio server."""
    # Look for config file
    config_file = None
    for config_name in ["config.yaml", "config.test.yaml", "config.sample.yaml"]:
        config_path = paths.project_root / config_name if paths.project_root else Path.cwd() / config_name
        if config_path.exists():
            config_file = str(config_path)
            break

    # Create Chrome manager
    if config_file:
        logger.info(f"Using config file: {config_file}")
        manager = ChromeManager(config_file=config_file)
    else:
        logger.info("Using default Chrome Manager configuration")
        manager = ChromeManager()

    # Initialize manager
    await manager.initialize()

    # Set pool to not create instances on startup
    manager.pool.min_instances = 0
    manager.pool.warm_instances = 0

    # Create and run server
    try:
        server = BrowserMCPServer(manager=manager)
        logger.info("Starting Browser MCP server (stdio)")
        await server.run_stdio()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
