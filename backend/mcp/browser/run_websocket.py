#!/usr/bin/env python
"""Run Browser MCP server with WebSocket transport."""

import asyncio
import contextlib
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

from loguru import logger  # noqa: E402

from backend.core.management.manager import ChromeManager  # noqa: E402
from backend.mcp.browser.server import BrowserMCPServer  # noqa: E402


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
