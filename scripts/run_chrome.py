#!/usr/bin/env bash
'exec "$(dirname "$0")/../scripts/ami-run" "$(dirname "$0")/run_chrome.py" "$@" #'

from __future__ import annotations


"""Run Chrome MCP server via console script entrypoint."""

# Standard library imports FIRST
import argparse
from pathlib import Path
import sys


# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Now we can import from base
from base.scripts.env.paths import setup_imports


ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from loguru import logger  # noqa: E402

from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: E402
from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer  # noqa: E402


def main() -> None:
    ensure_module_venv(Path(__file__))

    # Configure loguru to write to stderr instead of stdout (MCP uses stdout for JSON-RPC)
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="DEBUG")  # Add stderr handler

    parser = argparse.ArgumentParser(description="Chrome MCP Server")
    parser.add_argument(
        "--data-root",
        type=str,
        default=None,
        help="Root directory for browser data (sessions, profiles, downloads, screenshots). Defaults to browser/data",
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport type",
    )

    args = parser.parse_args()

    # Resolve data root
    if args.data_root:
        data_root = Path(args.data_root).resolve()
    else:
        # Default: browser module data directory
        browser_root = ORCHESTRATOR_ROOT / "browser"
        data_root = browser_root / "data"

    server = ChromeFastMCPServer(data_root=data_root)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
