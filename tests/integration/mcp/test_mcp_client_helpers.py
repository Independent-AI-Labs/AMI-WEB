#!/usr/bin/env bash
'exec "$(dirname "$0")/../../../scripts/ami-run.sh" "$(dirname "$0")/test_mcp_client_helpers.py" "$@" #'

from __future__ import annotations

"""MCP client helper tests for browser module.

Mirrors base coverage: verify error handling and timeout behavior when
connecting to a failing or hanging server process using stdio transport.
"""

import asyncio
from pathlib import Path

import pytest
from base.scripts.env.venv import get_venv_python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError


@pytest.mark.asyncio
async def test_client_error_handling(browser_root: Path) -> None:
    """Expect MCP client to surface errors when the server exits immediately."""
    venv_python = get_venv_python(browser_root)
    server_params = StdioServerParameters(command=str(venv_python), args=["-c", "import sys; sys.exit(1)"], env=None)

    with pytest.raises((McpError, ExceptionGroup)):
        async with (
            stdio_client(server_params) as (
                read_stream,
                write_stream,
            ),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()


@pytest.mark.asyncio
async def test_client_timeout(browser_root: Path) -> None:
    """Expect a TimeoutError when the server never responds to initialize."""
    venv_python = get_venv_python(browser_root)
    server_params = StdioServerParameters(command=str(venv_python), args=["-c", "import time; time.sleep(100)"], env=None)

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(2.0):
            async with (
                stdio_client(server_params) as (
                    read_stream,
                    write_stream,
                ),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
