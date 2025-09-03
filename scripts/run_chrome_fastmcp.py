#!/usr/bin/env python
"""Run Chrome MCP server using FastMCP."""

import sys
from pathlib import Path

# Path setup FIRST
MODULE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MODULE_ROOT))
sys.path.insert(0, str(MODULE_ROOT.parent))
sys.path.insert(0, str(MODULE_ROOT / "scripts"))

from ami_path import setup_ami_paths  # noqa: E402, I001

ORCHESTRATOR_ROOT, MODULE_ROOT, MODULE_NAME = setup_ami_paths()

# NOW other imports
from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer  # noqa: E402

if __name__ == "__main__":
    # Create and run server
    server = ChromeFastMCPServer()
    server.run(transport="stdio")
