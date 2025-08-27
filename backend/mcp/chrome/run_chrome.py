#!/usr/bin/env python
"""Run Chrome MCP server."""

import subprocess
import sys
from pathlib import Path

# Find base module's run_mcp.py
orchestrator_root = Path(__file__).resolve()
while orchestrator_root != orchestrator_root.parent:
    if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
        break
    orchestrator_root = orchestrator_root.parent

run_mcp = orchestrator_root / "base" / "scripts" / "run_mcp.py"

if not run_mcp.exists():
    print(f"Error: Could not find run_mcp.py at {run_mcp}")
    sys.exit(1)

# Pass through all arguments to the generic runner
result = subprocess.run([sys.executable, str(run_mcp), "chrome"] + sys.argv[1:], check=False)
sys.exit(result.returncode)
