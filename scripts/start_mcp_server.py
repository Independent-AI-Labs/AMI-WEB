#!/usr/bin/env python
"""Browser MCP Server wrapper using the generic base MCP launcher."""

import os
import sys
from pathlib import Path

# Magic setup: Find project root and set CWD regardless of where script is run from
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent  # Go up from scripts/ to browser/

# Change working directory to project root FIRST
os.chdir(PROJECT_ROOT)
print(f"Working directory set to: {PROJECT_ROOT}")

# First, ensure the parent base module is in path for setup.py
PARENT_DIR = PROJECT_ROOT.parent
PARENT_BASE = PARENT_DIR / "base"

# Add parent directory to path so setup.py can find base module
if PARENT_BASE.exists():
    sys.path.insert(0, str(PARENT_DIR))
    print(f"Added parent to path for base module: {PARENT_DIR}")

# Now add base/scripts to path for the generic launcher
BASE_SCRIPTS_PATH = PARENT_BASE / "scripts"
if BASE_SCRIPTS_PATH.exists():
    sys.path.insert(0, str(BASE_SCRIPTS_PATH))
    print(f"Using base scripts from: {BASE_SCRIPTS_PATH}")
else:
    print(f"ERROR: Base scripts not found at {BASE_SCRIPTS_PATH}")
    sys.exit(1)

# Import the generic MCP launcher
from start_mcp_server import main as start_mcp_main  # noqa: E402


def main():
    """Run MCP server for the browser module."""
    # The MCP scripts are in backend/mcp/browser/
    mcp_base_path = PROJECT_ROOT / "backend" / "mcp" / "browser"

    return start_mcp_main(project_root=PROJECT_ROOT, mcp_base_path=mcp_base_path, project_name="AMI-WEB MCP Server")


if __name__ == "__main__":
    sys.exit(main())
