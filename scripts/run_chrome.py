#!/usr/bin/env python
"""Run Chrome MCP server using base module's runner."""

import subprocess
import sys
from pathlib import Path

# Find base module's run_mcp.py
current = Path(__file__).resolve()
orchestrator_root = current.parent.parent.parent
base_run_mcp = orchestrator_root / "base" / "scripts" / "run_mcp.py"

if not base_run_mcp.exists():
    print(f"Error: Could not find base run_mcp.py at {base_run_mcp}")
    sys.exit(1)

# Use base module's Python to run the MCP script
base_venv = orchestrator_root / "base" / ".venv"
if sys.platform == "win32":
    python_exe = base_venv / "Scripts" / "python.exe"
else:
    python_exe = base_venv / "bin" / "python"

if not python_exe.exists():
    print(f"Error: Base module virtual environment not found at {base_venv}")
    sys.exit(1)

# Run with base module's Python
result = subprocess.run([str(python_exe), str(base_run_mcp), "chrome"] + sys.argv[1:], check=False)
sys.exit(result.returncode)
