#!/usr/bin/env python
"""Integration tests for Chrome FastMCP server using official MCP client."""

import json
import sys
from pathlib import Path

import pytest
from base.backend.utils.environment_setup import EnvironmentSetup
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add browser to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestChromeFastMCPServer:
    """Test Chrome FastMCP server using official MCP client."""

    @pytest.mark.asyncio
    async def test_chrome_server_with_client(self) -> None:
        """Test Chrome FastMCP server using official MCP client."""
        # Get the server script path
        server_script = Path(__file__).parent.parent.parent / "scripts" / "run_chrome_fastmcp.py"

        # Use the module's venv python

        venv_python = EnvironmentSetup.get_module_venv_python(Path(__file__))

        # Create stdio server parameters
        server_params = StdioServerParameters(command=str(venv_python), args=["-u", str(server_script)], env=None)

        # Use the stdio client to connect
        async with stdio_client(server_params) as (read_stream, write_stream), ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            result = await session.initialize()

            # Check server info
            assert result.serverInfo.name == "ChromeMCPServer"
            assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

            # List available tools
            tools_response = await session.list_tools()
            tool_names = [tool.name for tool in tools_response.tools]

            # Verify expected browser tools exist
            assert "browser_launch" in tool_names
            assert "browser_terminate" in tool_names
            assert "browser_navigate" in tool_names
            assert "browser_click" in tool_names
            assert "browser_screenshot" in tool_names

    @pytest.mark.asyncio
    @pytest.mark.integration  # Mark as integration test that requires Chrome
    async def test_browser_launch_and_terminate(self) -> None:
        """Test launching and terminating a browser instance."""
        server_script = Path(__file__).parent.parent.parent / "scripts" / "run_chrome_fastmcp.py"

        venv_python = EnvironmentSetup.get_module_venv_python(Path(__file__))
        server_params = StdioServerParameters(command=str(venv_python), args=["-u", str(server_script)], env=None)

        async with stdio_client(server_params) as (read_stream, write_stream), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Launch a browser
            launch_result = await session.call_tool("browser_launch", arguments={"headless": True, "anti_detect": True, "use_pool": False})

            assert launch_result is not None
            assert len(launch_result.content) > 0

            # Parse the response
            if launch_result.content[0].type == "text":
                response = json.loads(launch_result.content[0].text)
                assert response.get("success") is True
                assert "instance_id" in response

                # Terminate the browser
                terminate_result = await session.call_tool("browser_terminate", arguments={"instance_id": response["instance_id"]})

                assert terminate_result is not None
                if terminate_result.content[0].type == "text":
                    term_response = json.loads(terminate_result.content[0].text)
                    assert term_response.get("success") is True
