#!/usr/bin/env python
"""MCP Server launcher that ensures correct environment using uv."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # Go up one level from scripts/
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

    # Install from requirements files
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        subprocess.run(["uv", "pip", "install", "-r", str(requirements_file)], check=True, cwd=PROJECT_ROOT)
    else:
        print("ERROR: requirements.txt not found!")
        sys.exit(1)

    if not VENV_PYTHON.exists():
        print(f"ERROR: Virtual environment Python not found at {VENV_PYTHON}")
        sys.exit(1)

    return VENV_PYTHON


def run_mcp_server(mode="stdio", host="localhost", port=8765):
    """Run the MCP server with the virtual environment.

    Args:
        mode: "stdio" for Claude Desktop or "websocket" for WebSocket server
        host: Host for WebSocket mode (ignored in stdio mode)
        port: Port for WebSocket mode (ignored in stdio mode)
    """
    venv_python = setup_environment()

    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    # Set LOG_LEVEL if not already set
    if "LOG_LEVEL" not in env:
        env["LOG_LEVEL"] = "INFO"

    # Determine which script to run based on mode
    if mode == "stdio":
        mcp_script = PROJECT_ROOT / "backend" / "mcp" / "browser" / "run_stdio.py"
        cmd = [str(venv_python), str(mcp_script)]
        server_type = "MCP Stdio Server (for Claude Desktop)"
    elif mode == "websocket":
        mcp_script = PROJECT_ROOT / "backend" / "mcp" / "browser" / "run_websocket.py"
        cmd = [str(venv_python), str(mcp_script), host, str(port)]
        server_type = f"MCP WebSocket Server at ws://{host}:{port}"
    else:
        print(f"ERROR: Invalid mode '{mode}'. Use 'stdio' or 'websocket'")
        sys.exit(1)

    if not mcp_script.exists():
        print(f"ERROR: MCP server script not found at {mcp_script}")
        sys.exit(1)

    # Print startup info
    print("=" * 60)
    print("AMI-WEB MCP Server")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Server: {server_type}")
    print(f"Python: {venv_python}")
    print(f"Script: {mcp_script}")
    print(f"Working Directory: {PROJECT_ROOT}")
    print(f"Log Level: {env.get('LOG_LEVEL', 'INFO')}")
    print("=" * 60)
    print(f"\nStarting {mode} server...")
    print("Press Ctrl+C to stop\n")

    # Run the server
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print(f"\n{mode.capitalize()} server stopped by user")
        return 0
    except Exception as e:
        print(f"\nERROR: Failed to run {mode} server: {e}")
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AMI-WEB MCP Server Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_mcp_server.py              # Start stdio server (default)
  python start_mcp_server.py stdio        # Explicitly start stdio server
  python start_mcp_server.py websocket    # Start WebSocket server on localhost:8765
  python start_mcp_server.py websocket --host 0.0.0.0 --port 8080  # Custom host/port

Environment Variables:
  LOG_LEVEL  - Set logging level (DEBUG, INFO, WARNING, ERROR)

The server will automatically:
  1. Create a virtual environment if needed
  2. Install all required dependencies
  3. Start the appropriate MCP server
""",
    )

    parser.add_argument(
        "mode",
        nargs="?",
        default="stdio",
        choices=["stdio", "websocket"],
        help="Server mode: 'stdio' for Claude Desktop (default) or 'websocket' for WebSocket server",
    )

    parser.add_argument("--host", default="localhost", help="Host for WebSocket server (default: localhost)")

    parser.add_argument("--port", type=int, default=8765, help="Port for WebSocket server (default: 8765)")

    args = parser.parse_args()

    return run_mcp_server(args.mode, args.host, args.port)


if __name__ == "__main__":
    sys.exit(main())
