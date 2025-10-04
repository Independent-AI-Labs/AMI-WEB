#!/usr/bin/env python
"""Run Chrome MCP server via console script entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() and (current / "base").exists():
            sys.path.insert(0, str(current))
            return
        current = current.parent


def main() -> None:
    _ensure_repo_on_path()

    from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: PLC0415

    ensure_module_venv(Path(__file__))

    # Configure loguru to write to stderr instead of stdout (MCP uses stdout for JSON-RPC)
    from loguru import logger  # noqa: PLC0415

    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level="DEBUG")  # Add stderr handler

    from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer  # noqa: PLC0415

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
        # Default: find browser module and use browser/data
        script_path = Path(__file__).resolve()
        browser_root = script_path.parent.parent
        data_root = browser_root / "data"

    server = ChromeFastMCPServer(data_root=data_root)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
