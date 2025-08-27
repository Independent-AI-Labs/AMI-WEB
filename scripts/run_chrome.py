#!/usr/bin/env python
"""Run Chrome MCP server with stdio/websocket support."""

import asyncio
import sys
from pathlib import Path

# Get module root
MODULE_ROOT = Path(__file__).resolve().parent.parent

# Add both browser and base to path (base for utilities)
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent / "base"))

from base.backend.mcp.mcp_runner import MCPRunner  # noqa: E402

from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402
from backend.utils.path_utils import ModuleSetup  # noqa: E402

# Ensure we're in the correct virtual environment
ModuleSetup.ensure_running_in_venv(Path(__file__))


async def main():
    """Run the Chrome MCP server."""
    runner = MCPRunner(server_class=BrowserMCPServer, server_name="Chrome", config_files=["chrome_config.yaml", "config.yaml"])
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
