"""Browser MCP Server - Only defines browser automation tools."""

import sys
from pathlib import Path

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports
from loguru import logger

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from base.backend.mcp.server_base import StandardMCPServer  # noqa: E402
from browser.backend.core.management.manager import ChromeManager  # noqa: E402

# Add chrome directory to path for tool imports
sys.path.insert(0, str(Path(__file__).parent))
from tools.definitions import register_all_tools  # noqa: E402
from tools.executor import ToolExecutor  # noqa: E402
from tools.registry import ToolRegistry  # noqa: E402


class BrowserMCPServer(StandardMCPServer[ToolRegistry, ToolExecutor]):
    """MCP server for Chrome Manager - defines browser automation tools only."""

    def __init__(self, config: dict | None = None):
        """Initialize Chrome MCP server.

        Args:
            config: Server configuration
        """
        # Create Chrome manager internally
        config_file = config.get("config_file") if config else None
        self.manager = ChromeManager(config_file=config_file)

        # Pass manager to parent for executor initialization
        super().__init__(config, manager=self.manager)
        logger.info(f"Browser MCP server initialized with {len(self.tools)} tools")

    def get_registry_class(self) -> type[ToolRegistry]:
        """Get the tool registry class."""
        return ToolRegistry

    def get_executor_class(self) -> type[ToolExecutor]:
        """Get the tool executor class."""
        return ToolExecutor

    def register_tools_to_registry(self, registry: ToolRegistry) -> None:
        """Register browser tools to the registry."""
        register_all_tools(registry)

    def register_tools(self) -> None:
        """Register all Chrome Manager tools."""
        # Convert tool registry to MCP format
        for tool in self.registry.list_tools():
            self.tools[tool.name] = {
                "description": tool.description,
                "inputSchema": {"type": "object", "properties": tool.parameters.get("properties", {}), "required": tool.parameters.get("required", [])},
            }

    # execute_tool is inherited from StandardMCPServer
