"""Browser MCP Server - Only defines browser automation tools."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Smart path discovery - find project roots by looking for .git/.venv
current = Path(__file__).resolve().parent
while current != current.parent:
    # Found main orchestrator (has base/ and .git)
    if (current / "base").exists() and (current / ".git").exists():
        sys.path.insert(0, str(current))
        break
    # Found module root (has .venv or .git and backend/)
    if ((current / ".venv").exists() or (current / ".git").exists()) and (current / "backend").exists() and str(current) not in sys.path:
        sys.path.insert(0, str(current))
    current = current.parent

from base.backend.mcp.mcp_server import BaseMCPServer  # noqa: E402

from backend.core.management.manager import ChromeManager  # noqa: E402

# Add chrome directory to path for tool imports
sys.path.insert(0, str(Path(__file__).parent))
from tools.definitions import register_all_tools  # noqa: E402
from tools.executor import ToolExecutor  # noqa: E402
from tools.registry import ToolRegistry  # noqa: E402


class BrowserMCPServer(BaseMCPServer):
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

        logger.info(f"Browser MCP server initialized with {len(self.tools)} tools")

    def register_tools(self) -> None:
        """Register all Chrome Manager tools."""
        # Convert tool registry to MCP format
        for tool in self.registry.list_tools():
            self.tools[tool.name] = {
                "description": tool.description,
                "inputSchema": {"type": "object", "properties": tool.parameters.get("properties", {}), "required": tool.parameters.get("required", [])},
            }

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
