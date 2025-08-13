"""Chrome Manager MCP Server - Only defines browser automation tools."""

from typing import Any

from loguru import logger

from chrome_manager.core import ChromeManager
from chrome_manager.mcp.base.mcp_server import BaseMCPServer
from chrome_manager.mcp.tools import ToolRegistry
from chrome_manager.mcp.tools.definitions import register_all_tools
from chrome_manager.mcp.tools.executor import ToolExecutor


class ChromeMCPServer(BaseMCPServer):
    """MCP server for Chrome Manager - defines browser automation tools only."""

    def __init__(self, manager: ChromeManager, config: dict | None = None):
        """Initialize Chrome MCP server.

        Args:
            manager: Chrome manager instance
            config: Server configuration
        """
        self.manager = manager

        # Initialize tool registry and executor for execution
        self.registry = ToolRegistry()
        register_all_tools(self.registry)
        self.executor = ToolExecutor(manager)

        # Initialize base with config
        super().__init__(config)

        logger.info(f"Chrome MCP server initialized with {len(self.tools)} tools")

    def register_tools(self) -> None:
        """Register all Chrome Manager tools."""
        # Convert tool registry to MCP format
        for tool in self.registry.list_tools():
            self.tools[tool.name] = {"description": tool.description, "inputSchema": tool.parameters}

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a browser automation tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Execute using the tool executor
        return await self.executor.execute(tool_name, arguments)
