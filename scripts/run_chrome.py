#!/usr/bin/env python
"""Run Chrome MCP server with stdio/websocket support."""

import sys
from pathlib import Path

# Get module root
MODULE_ROOT = Path(__file__).resolve().parent.parent

# Add browser and parent (for base imports) to path
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))

from base.backend.mcp.mcp_runner import run_mcp_server_with_env  # noqa: E402

from backend.mcp.chrome.server import BrowserMCPServer  # noqa: E402

if __name__ == "__main__":
    import asyncio

    asyncio.run(run_mcp_server_with_env(server_class=BrowserMCPServer, server_name="Chrome", config_files=["chrome_config.yaml", "config.yaml"]))
