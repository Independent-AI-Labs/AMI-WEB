#!/usr/bin/env bash
'exec "$(dirname "$0")/../../../scripts/ami-run" "$(dirname "$0")/test_run_mcp_runner.py" "$@" #'

from __future__ import annotations

"""Integration tests for the unified MCP runner (run_mcp) targeting Chrome.

Validates that the unified runner can launch the Chrome MCP server and that
the official MCP client can initialize and discover core tools over stdio.
"""

import json
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from base.scripts.env.venv import get_venv_python

pytestmark = pytest.mark.xdist_group(name="browser_lifecycle")


@pytest.mark.asyncio
async def test_run_mcp_chrome_stdio_client(browser_root: Path) -> None:
    """Launch Chrome via unified runner and validate MCP handshake/tools."""
    # Path to the unified runner script (lives in base module)
    run_mcp_script = browser_root.parent / "base" / "scripts" / "run_mcp.py"

    # Use the browser module venv's Python
    venv_python = get_venv_python(browser_root)

    # Create stdio server parameters for `run_mcp chrome`
    server_params = StdioServerParameters(
        command=str(venv_python),
        args=["-u", str(run_mcp_script), "chrome"],
        env=None,
    )

    async with (
        stdio_client(server_params) as (
            read_stream,
            write_stream,
        ),
        ClientSession(read_stream, write_stream) as session,
    ):
        # Initialize the connection and check server info
        result = await session.initialize()
        assert result.serverInfo.name == "ChromeMCPServer"
        assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

        # Basic capability check: list tools and ensure key tools are present (V02 API)
        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        expected = {
            "browser_session",
            "browser_navigate",
            "browser_interact",
            "browser_capture",
        }
        assert expected.issubset(tool_names)

        # Optional: if navigate is available, it should respond without a running instance
        if "browser_navigate" in tool_names:
            res = await session.call_tool("browser_navigate", arguments={"action": "get_url"})
            assert res is not None and len(res.content) > 0
            if res.content[0].type == "text":
                try:
                    payload = json.loads(res.content[0].text)
                    assert isinstance(payload, dict)
                except json.decoder.JSONDecodeError:
                    # Non-JSON textual response is acceptable when no browser instance is active
                    assert isinstance(res.content[0].text, str)
