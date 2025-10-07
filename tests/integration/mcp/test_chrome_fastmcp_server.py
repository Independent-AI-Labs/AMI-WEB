#!/usr/bin/env python
"""Integration tests for Chrome FastMCP server using official MCP client."""

import json
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from base.backend.utils.environment_setup import EnvironmentSetup


class TestChromeFastMCPServer:
    """Test Chrome FastMCP server using official MCP client."""

    @pytest.mark.asyncio
    async def test_chrome_server_with_client(
        self, browser_root: Path, scripts_dir: Path
    ) -> None:
        """Test Chrome FastMCP server using official MCP client."""
        # Get the server script path
        server_script = scripts_dir / "run_chrome.py"

        # Use the module's venv python
        venv_python = EnvironmentSetup.get_module_venv_python(browser_root)

        # Create stdio server parameters
        server_params = StdioServerParameters(
            command=str(venv_python), args=["-u", str(server_script)], env=None
        )

        # Use the stdio client to connect
        async with stdio_client(server_params) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            result = await session.initialize()

            # Check server info
            assert result.serverInfo.name == "ChromeMCPServer"
            assert result.protocolVersion in ["2024-11-05", "2025-06-18"]

            # List available tools
            tools_response = await session.list_tools()
            tool_names = [tool.name for tool in tools_response.tools]

            # Verify V02 simplified facade tools exist
            assert "browser_session" in tool_names
            assert "browser_navigate" in tool_names
            assert "browser_interact" in tool_names
            assert "browser_inspect" in tool_names
            assert "browser_extract" in tool_names
            assert "browser_capture" in tool_names
            assert "browser_execute" in tool_names
            assert "web_search" in tool_names

    @pytest.mark.asyncio
    @pytest.mark.integration  # Mark as integration test that requires Chrome
    async def test_browser_launch_and_terminate(
        self, browser_root: Path, scripts_dir: Path
    ) -> None:
        """Test launching and terminating a browser instance."""
        server_script = scripts_dir / "run_chrome.py"

        venv_python = EnvironmentSetup.get_module_venv_python(browser_root)
        server_params = StdioServerParameters(
            command=str(venv_python), args=["-u", str(server_script)], env=None
        )

        async with stdio_client(server_params) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Launch a browser using V02 API
            launch_result = await session.call_tool(
                "browser_session",
                arguments={
                    "action": "launch",
                    "headless": True,
                    "anti_detect": True,
                    "use_pool": False,
                },
            )

            assert launch_result is not None
            assert len(launch_result.content) > 0

            # Parse the response
            content_item = launch_result.content[0]
            if content_item.type == "text":
                assert hasattr(content_item, "text")
                response = json.loads(content_item.text)
                assert response.get("success") is True
                assert "instance_id" in response

                # Terminate the browser using V02 API
                terminate_result = await session.call_tool(
                    "browser_session",
                    arguments={
                        "action": "terminate",
                        "instance_id": response["instance_id"],
                    },
                )

                assert terminate_result is not None
                term_content = terminate_result.content[0]
                if term_content.type == "text":
                    assert hasattr(term_content, "text")
                    term_response = json.loads(term_content.text)
                    assert term_response.get("success") is True
                    # Verify auto-save behavior
                    assert "session_id" in term_response["data"]
                    assert term_response["data"]["session_id"] is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_session_save_and_restore(
        self, browser_root: Path, scripts_dir: Path
    ) -> None:
        """Test saving and restoring a browser session."""
        server_script = scripts_dir / "run_chrome.py"
        venv_python = EnvironmentSetup.get_module_venv_python(browser_root)
        server_params = StdioServerParameters(
            command=str(venv_python), args=["-u", str(server_script)], env=None
        )

        async with stdio_client(server_params) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Launch a browser
            launch_result = await session.call_tool(
                "browser_session",
                arguments={
                    "action": "launch",
                    "headless": True,
                    "anti_detect": False,
                    "use_pool": False,
                },
            )

            assert launch_result is not None
            assert len(launch_result.content) > 0

            # Parse launch response
            launch_content = launch_result.content[0]
            if launch_content.type == "text":
                assert hasattr(launch_content, "text")
                launch_response = json.loads(launch_content.text)
                assert launch_response.get("success") is True
                instance_id = launch_response["instance_id"]

                # Navigate to a test URL
                nav_result = await session.call_tool(
                    "browser_navigate",
                    arguments={"action": "goto", "url": "https://example.com"},
                )
                assert nav_result is not None
                nav_content = nav_result.content[0]
                assert hasattr(nav_content, "text")
                nav_response = json.loads(nav_content.text)
                assert nav_response.get("success") is True

                # Save the session
                save_result = await session.call_tool(
                    "browser_session",
                    arguments={
                        "action": "save",
                        "instance_id": instance_id,
                        "session_name": "test_session",
                    },
                )
                assert save_result is not None

                # Parse save response
                save_content = save_result.content[0]
                if save_content.type == "text":
                    assert hasattr(save_content, "text")
                    save_response = json.loads(save_content.text)
                    assert save_response.get("success") is True
                    session_id = save_response["data"]["session_id"]
                    assert session_id is not None

                    # Terminate the browser (this will auto-save another session)
                    term_result = await session.call_tool(
                        "browser_session",
                        arguments={"action": "terminate", "instance_id": instance_id},
                    )
                    term_content = term_result.content[0]
                    assert hasattr(term_content, "text")
                    term_response = json.loads(term_content.text)
                    assert term_response.get("success") is True
                    autosaved_session_id = term_response["data"]["session_id"]
                    # Verify auto-save created a different session
                    assert autosaved_session_id != session_id

                    # Restore the session
                    restore_result = await session.call_tool(
                        "browser_session",
                        arguments={"action": "restore", "session_id": session_id},
                    )
                    assert restore_result is not None

                    restore_content = restore_result.content[0]
                    if restore_content.type == "text":
                        assert hasattr(restore_content, "text")
                        restore_response = json.loads(restore_content.text)
                        assert restore_response.get("success") is True
                        restored_instance_id = restore_response["data"]["instance_id"]
                        assert restored_instance_id is not None

                        # Clean up: terminate restored instance and delete both sessions
                        term_restore_result = await session.call_tool(
                            "browser_session",
                            arguments={
                                "action": "terminate",
                                "instance_id": restored_instance_id,
                            },
                        )
                        # This creates yet another auto-saved session
                        term_restore_content = term_restore_result.content[0]
                        assert hasattr(term_restore_content, "text")
                        term_restore_response = json.loads(term_restore_content.text)
                        third_session_id = term_restore_response["data"]["session_id"]

                        # Delete all three sessions
                        await session.call_tool(
                            "browser_session",
                            arguments={
                                "action": "delete_session",
                                "session_id": session_id,
                            },
                        )
                        await session.call_tool(
                            "browser_session",
                            arguments={
                                "action": "delete_session",
                                "session_id": autosaved_session_id,
                            },
                        )
                        delete_result = await session.call_tool(
                            "browser_session",
                            arguments={
                                "action": "delete_session",
                                "session_id": third_session_id,
                            },
                        )
                        delete_content = delete_result.content[0]
                        assert hasattr(delete_content, "text")
                        delete_response = json.loads(delete_content.text)
                        assert delete_response.get("success") is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_session_list_and_delete(
        self, browser_root: Path, scripts_dir: Path
    ) -> None:
        """Test listing and deleting sessions."""
        server_script = scripts_dir / "run_chrome.py"
        venv_python = EnvironmentSetup.get_module_venv_python(browser_root)
        server_params = StdioServerParameters(
            command=str(venv_python), args=["-u", str(server_script)], env=None
        )

        async with stdio_client(server_params) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            # Initialize
            await session.initialize()

            # Launch a browser
            launch_result = await session.call_tool(
                "browser_session",
                arguments={"action": "launch", "headless": True, "use_pool": False},
            )
            launch_content = launch_result.content[0]
            assert hasattr(launch_content, "text")
            launch_response = json.loads(launch_content.text)
            instance_id = launch_response["instance_id"]

            # Save a session
            save_result = await session.call_tool(
                "browser_session",
                arguments={
                    "action": "save",
                    "instance_id": instance_id,
                    "session_name": "test_list_session",
                },
            )
            save_content = save_result.content[0]
            assert hasattr(save_content, "text")
            save_response = json.loads(save_content.text)
            session_id = save_response["data"]["session_id"]

            # Terminate instance (creates an auto-saved session too)
            term_result = await session.call_tool(
                "browser_session",
                arguments={"action": "terminate", "instance_id": instance_id},
            )
            term_content = term_result.content[0]
            assert hasattr(term_content, "text")
            term_response = json.loads(term_content.text)
            autosaved_session_id = term_response["data"]["session_id"]

            # List sessions
            list_result = await session.call_tool(
                "browser_session", arguments={"action": "list_sessions"}
            )
            list_content = list_result.content[0]
            assert hasattr(list_content, "text")
            list_response = json.loads(list_content.text)
            assert list_response.get("success") is True
            assert list_response["data"]["count"] >= 1

            # Find our session in the list
            sessions = list_response["data"]["sessions"]
            our_session = next((s for s in sessions if s["id"] == session_id), None)
            assert our_session is not None

            # Delete the session
            delete_result = await session.call_tool(
                "browser_session",
                arguments={"action": "delete_session", "session_id": session_id},
            )
            delete_content = delete_result.content[0]
            assert hasattr(delete_content, "text")
            delete_response = json.loads(delete_content.text)
            assert delete_response.get("success") is True

            # Verify it's deleted by listing again
            list_result2 = await session.call_tool(
                "browser_session", arguments={"action": "list_sessions"}
            )
            list_content2 = list_result2.content[0]
            assert hasattr(list_content2, "text")
            list_response2 = json.loads(list_content2.text)
            sessions2 = list_response2["data"]["sessions"]
            deleted_session = next(
                (s for s in sessions2 if s["id"] == session_id), None
            )
            assert deleted_session is None

            # Clean up the autosaved session
            await session.call_tool(
                "browser_session",
                arguments={
                    "action": "delete_session",
                    "session_id": autosaved_session_id,
                },
            )
