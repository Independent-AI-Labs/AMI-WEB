#!/usr/bin/env python
"""Run Chrome MCP server using FastMCP."""

import sys
from pathlib import Path

# Add browser and base to path
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))  # For base imports

from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer  # noqa: E402

if __name__ == "__main__":
    # Create and run server
    server = ChromeFastMCPServer()
    server.run(transport="stdio")
