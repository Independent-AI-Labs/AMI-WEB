#!/usr/bin/env python
"""Run Chrome MCP server using FastMCP."""

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

    from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer  # noqa: PLC0415

    server = ChromeFastMCPServer()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
