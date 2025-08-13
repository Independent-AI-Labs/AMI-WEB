#!/usr/bin/env python
"""Run Browser MCP server with WebSocket transport."""

import asyncio
import contextlib
import subprocess
import sys
from pathlib import Path

# Ensure base module is available before imports
project_root = Path(__file__).parent.parent.parent.parent.resolve()
parent_base = project_root.parent / "base"
local_base = project_root / "base"
BASE_REPO_URL = "https://github.com/Independent-AI-Labs/AMI-BASE.git"

if parent_base.exists() and (parent_base / "mcp").exists():
    # Using base from parent directory
    sys.path.insert(0, str(parent_base.parent))
elif local_base.exists() and (local_base / "mcp").exists():
    # Using local base
    sys.path.insert(0, str(project_root))
else:
    # Clone the base module repository
    try:
        subprocess.run(["git", "clone", BASE_REPO_URL, str(local_base)], check=True, cwd=project_root, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        sys.path.insert(0, str(project_root))
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If cloning fails, try to continue anyway
        pass

from loguru import logger

from backend.core.management.manager import ChromeManager
from backend.mcp.browser.server import BrowserMCPServer


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
