#!/usr/bin/env python
"""Integration tests for the browser run_chrome runner using MCP client.

Validates that the runner can launch the Chrome MCP server over stdio and
respond to initialize and basic tool discovery requests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from base.backend.utils.environment_setup import EnvironmentSetup
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_run_chrome_stdio_client_initialization() -> None:
    """Launch Chrome via runner and validate MCP handshake and tools."""
    # Path to the Chrome runner script
    run_script = Path(__file__).parent.parent.parent / "scripts" / "run_chrome.py"

    # Use the module venv's Python
    venv_python = EnvironmentSetup.get_module_venv_python(Path(__file__).parent.parent)

    # Create stdio server parameters for the runner
    server_params = StdioServerParameters(
        command=str(venv_python),
        args=["-u", str(run_script)],
        env=None,
    )

    async with stdio_client(server_params) as (read_stream, write_stream), ClientSession(read_stream, write_stream) as session:
        # Initialize the connection and check server info
        result = await session.initialize()
        assert result.serverInfo.name == "ChromeMCPServer"
        assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

        # Ensure the server advertises the full tool surface we expect. This catches
        # accidental regressions where the runner fails to wire modules correctly and
        # prevents MCP clients from reconnecting because tool discovery breaks.
        response = await session.list_tools()
        tool_names = {tool.name for tool in response.tools}
        expected_tools = {
            "browser_back",
            "browser_click",
            "browser_element_screenshot",
            "browser_evaluate",
            "browser_evaluate_chunk",
            "browser_execute",
            "browser_execute_chunk",
            "browser_exists",
            "browser_forward",
            "browser_get_active",
            "browser_get_attribute",
            "browser_get_cookies",
            "browser_get_text",
            "browser_get_text_chunk",
            "browser_get_url",
            "browser_hover",
            "browser_launch",
            "browser_list",
            "browser_navigate",
            "browser_press",
            "browser_refresh",
            "browser_screenshot",
            "browser_scroll",
            "browser_select",
            "browser_terminate",
            "browser_type",
            "browser_wait_for",
            "web_search",
        }
        assert tool_names == expected_tools

        # Call a representative tool twice to ensure the server keeps responding.
        for attempt in range(2):
            res = await session.call_tool("browser_get_url", arguments={})
            assert res is not None and len(res.content) > 0
            if res.content[0].type == "text":
                try:
                    json.loads(res.content[0].text)
                except json.decoder.JSONDecodeError:
                    assert isinstance(res.content[0].text, str)

        # Double-check that listing tools remains stable on a second invocation.
        follow_up = await session.list_tools()
        assert {tool.name for tool in follow_up.tools} == expected_tools
