#!/usr/bin/env python
"""Run Chrome MCP server with stdio/websocket support."""

import asyncio
import sys
from pathlib import Path

# Get module root
MODULE_ROOT = Path(__file__).resolve().parent.parent

# Add browser and parent (for base imports) to path
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

from base.backend.utils.path_utils import ModuleSetup  # noqa: E402

from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402

# Ensure we're in the correct virtual environment
ModuleSetup.ensure_running_in_venv(Path(__file__))


async def main():
    """Run the Chrome MCP server."""
    # BrowserMCPServer needs special handling - it requires a ChromeManager instance
    import argparse

    from browser.backend.core.management.manager import ChromeManager

    # Parse arguments ourselves since we need to create manager first
    parser = argparse.ArgumentParser(description="Chrome MCP Server")
    parser.add_argument("--transport", choices=["stdio", "websocket"], default="stdio", help="Transport mode")
    parser.add_argument("--host", default="localhost", help="Host for websocket mode")
    parser.add_argument("--port", type=int, default=8765, help="Port for websocket mode")
    parser.add_argument("--config", help="Configuration file")
    args = parser.parse_args()

    # Create Chrome manager
    manager = ChromeManager(config_file=args.config)

    # Create and run server
    config = {}
    if args.config:
        from base.backend.utils.config import Config

        config = Config.load(args.config).to_dict()

    server = BrowserMCPServer(manager=manager, config=config)

    if args.transport == "websocket":
        await server.run_websocket(args.host, args.port)
    else:
        await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
