#!/usr/bin/env python
"""Run Chrome MCP server via console script entrypoint.

This wrapper avoids ad-hoc sys.path hacks by relying on package installation.
"""

from __future__ import annotations

from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer


def main() -> None:
    server = ChromeFastMCPServer()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

