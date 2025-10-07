#!/usr/bin/env python
"""Integration tests for the browser run_chrome runner using MCP client.

Validates that the runner can launch the Chrome MCP server over stdio and
respond to initialize and basic tool discovery requests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from base.backend.utils.environment_setup import EnvironmentSetup


@pytest.mark.asyncio
async def test_run_chrome_stdio_client_initialization(
    browser_root: Path, scripts_dir: Path
) -> None:
    """Launch Chrome via runner and validate MCP handshake and tools."""
    # Path to the Chrome runner script
    run_script = scripts_dir / "run_chrome.py"

    # Use the module venv's Python
    venv_python = EnvironmentSetup.get_module_venv_python(browser_root)

    # Create stdio server parameters for the runner
    server_params = StdioServerParameters(
        command=str(venv_python),
        args=["-u", str(run_script)],
        env=None,
    )

    async with stdio_client(server_params) as (
        read_stream,
        write_stream,
    ), ClientSession(read_stream, write_stream) as session:
        # Initialize the connection and check server info
        result = await session.initialize()
        assert result.serverInfo.name == "ChromeMCPServer"
        assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

        # Ensure the server advertises the V02 simplified facade tool surface.
        # This catches accidental regressions where the runner fails to wire modules correctly.
        response = await session.list_tools()
        tool_names = {tool.name for tool in response.tools}
        expected_tools = {
            "browser_session",
            "browser_navigate",
            "browser_interact",
            "browser_inspect",
            "browser_extract",
            "browser_capture",
            "browser_execute",
            "browser_storage",
            "browser_react",
            "browser_profile",
            "web_search",
        }
        assert tool_names == expected_tools

        # Call a representative tool twice to ensure the server keeps responding.
        for attempt in range(2):
            res = await session.call_tool(
                "browser_navigate", arguments={"action": "get_url"}
            )
            assert res is not None and len(res.content) > 0
            if res.content[0].type == "text":
                try:
                    json.loads(res.content[0].text)
                except json.decoder.JSONDecodeError:
                    assert isinstance(res.content[0].text, str)

        # Double-check that listing tools remains stable on a second invocation.
        follow_up = await session.list_tools()
        assert {tool.name for tool in follow_up.tools} == expected_tools
