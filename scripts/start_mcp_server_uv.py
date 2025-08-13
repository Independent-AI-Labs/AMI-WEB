#!/usr/bin/env python
"""MCP Server launcher that ensures correct environment using uv."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_PATH = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_PATH / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_PATH / "bin" / "python"


def check_uv():
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: uv is not installed!")
        print("Install it with: pip install uv")
        return False


def setup_environment():
    """Set up the virtual environment if needed."""
    if not check_uv():
        sys.exit(1)

    # Create venv if it doesn't exist
    if not VENV_PATH.exists():
        print("Creating virtual environment with uv...")
        subprocess.run(["uv", "venv", str(VENV_PATH)], check=True)

    # Install/update dependencies
    print("Ensuring dependencies are installed...")

    # Check if we need MCP dependencies
    deps_to_install = ["-e", ".[dev,mcp]"]

    subprocess.run(["uv", "pip", "install"] + deps_to_install, check=True, cwd=PROJECT_ROOT)

    if not VENV_PYTHON.exists():
        print(f"ERROR: Virtual environment Python not found at {VENV_PYTHON}")
        sys.exit(1)

    return VENV_PYTHON


def run_mcp_server():
    """Run the MCP server with the virtual environment."""
    venv_python = setup_environment()

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    # Set LOG_LEVEL if not already set
    if "LOG_LEVEL" not in env:
        env["LOG_LEVEL"] = "INFO"

    # Build the command
    mcp_script = PROJECT_ROOT / "chrome_manager" / "mcp" / "mcp_stdio_server.py"

    if not mcp_script.exists():
        print(f"ERROR: MCP server script not found at {mcp_script}")
        sys.exit(1)

    cmd = [str(venv_python), str(mcp_script)]

    # Print startup info
    print("=" * 60)
    print("AMI-WEB MCP Server")
    print("=" * 60)
    print(f"Python: {venv_python}")
    print(f"Script: {mcp_script}")
    print(f"Working Directory: {PROJECT_ROOT}")
    print(f"Log Level: {env.get('LOG_LEVEL', 'INFO')}")
    print("=" * 60)
    print("\nStarting MCP server...")
    print("Press Ctrl+C to stop\n")

    # Run the server
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nMCP server stopped by user")
        return 0
    except Exception as e:
        print(f"\nERROR: Failed to run MCP server: {e}")
        return 1


def main():
    """Main entry point."""
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("AMI-WEB MCP Server Launcher")
        print("=" * 40)
        print("\nUsage:")
        print("  python start_mcp_server_uv.py         # Start MCP server")
        print("  python start_mcp_server_uv.py --help  # Show this help")
        print("\nEnvironment Variables:")
        print("  LOG_LEVEL  - Set logging level (DEBUG, INFO, WARNING, ERROR)")
        print("\nThe server will automatically:")
        print("  1. Create a virtual environment if needed")
        print("  2. Install all required dependencies")
        print("  3. Start the MCP stdio server")
        return 0

    return run_mcp_server()


if __name__ == "__main__":
    sys.exit(main())
