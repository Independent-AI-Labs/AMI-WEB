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

        # Basic capability check: list tools and ensure key tools are present
        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        expected = {"browser_launch", "browser_terminate", "browser_navigate", "browser_click", "browser_screenshot"}
        assert expected.issubset(tool_names)

        # Optional: call a lightweight info-like tool if present; skip if absent
        # Not all servers expose an explicit info endpoint; avoid requiring a running browser instance here.
        if "browser_get_url" in tool_names:
            # Should return a structured BrowserResponse or text when no instance is running
            res = await session.call_tool("browser_get_url", arguments={})
            assert res is not None and len(res.content) > 0
            # Accept either text or object; validate JSON shape if text provided
            if res.content[0].type == "text":
                try:
                    payload = json.loads(res.content[0].text)
                    assert isinstance(payload, dict)
                except json.decoder.JSONDecodeError:
                    # Non-JSON textual response is acceptable in absence of an active browser
                    assert isinstance(res.content[0].text, str)
