#!/usr/bin/env python
"""Run Browser MCP server with stdio transport."""

import asyncio
import sys
from pathlib import Path

# Smart path discovery - find project roots by looking for .git/.venv
current = Path(__file__).resolve().parent
module_root = None
main_root = None

while current != current.parent:
    # Found module root (has .venv or .git and backend/)
    if not module_root and ((current / ".venv").exists() or (current / ".git").exists()) and (current / "backend").exists():
        module_root = current
    # Found main orchestrator (has base/ and .git)
    if not main_root and (current / "base").exists() and (current / ".git").exists():
        main_root = current
    current = current.parent

# Add paths in correct order: module first, then main
if module_root and str(module_root) not in sys.path:
    sys.path.insert(0, str(module_root))
if main_root and str(main_root) not in sys.path:
    sys.path.insert(0, str(main_root))

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
        config_path = module_root / config_name if module_root else Path.cwd() / config_name
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
