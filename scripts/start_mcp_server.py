#!/usr/bin/env python
"""Browser MCP Server wrapper - follows files module pattern."""

import os
import sys
from pathlib import Path

# Smart path setup - works from ANYWHERE
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Find the main git root by looking for base/ directory
# This handles both submodules and main repo
MAIN_ROOT = None
current = SCRIPT_DIR

while current != current.parent:
    # The main repo has base/ directory at its root
    if (current / "base").exists() and (current / ".git").exists():
        MAIN_ROOT = current
        break
    current = current.parent

if not MAIN_ROOT:
    print("ERROR: Could not find main repository root (with base/ directory)")
    print(f"Started search from: {SCRIPT_DIR}")
    sys.exit(1)

print(f"Found main repository at: {MAIN_ROOT}")

# Determine project root (browser directory)
# Start from script directory and go up until we find backend/mcp/chrome
PROJECT_ROOT = SCRIPT_DIR.parent  # Default: parent of scripts/
current = SCRIPT_DIR
while current != current.parent:
    if (current / "backend" / "mcp" / "chrome").exists():
        PROJECT_ROOT = current
        break
    current = current.parent

print(f"Project root (browser): {PROJECT_ROOT}")

# Change working directory to project root
os.chdir(PROJECT_ROOT)
print(f"Working directory set to: {PROJECT_ROOT}")

# Set up Python paths
# 1. Project root first (to avoid namespace collisions)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Added to path: {PROJECT_ROOT}")

# 2. Main repository root
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(1, str(MAIN_ROOT))
    print(f"Added to path: {MAIN_ROOT}")

# 3. Base module
BASE_PATH = MAIN_ROOT / "base"
if BASE_PATH.exists() and str(BASE_PATH) not in sys.path:
    sys.path.insert(1, str(BASE_PATH))
    print(f"Added to path: {BASE_PATH}")


# Now we can import and run the browser MCP server
def main():
    """Run MCP server for the browser module."""
    # Import and run the run_stdio.py directly
    import subprocess

    # Path to the run_stdio.py script
    run_stdio_path = PROJECT_ROOT / "backend" / "mcp" / "chrome" / "run_stdio.py"

    if not run_stdio_path.exists():
        print(f"ERROR: MCP server script not found at {run_stdio_path}")
        return 1

    # Get Python executable from virtual environment if it exists
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    print("Starting Browser MCP Server...")
    print(f"Python: {python_exe}")
    print(f"Script: {run_stdio_path}")

    # Run the MCP server
    try:
        result = subprocess.run([python_exe, str(run_stdio_path)], cwd=str(PROJECT_ROOT), check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nMCP Server stopped by user")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to start MCP server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
