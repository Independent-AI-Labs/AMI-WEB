"""Browser MCP Server - Only defines browser automation tools."""

import sys
from pathlib import Path

from loguru import logger

# STANDARD IMPORT SETUP - DO NOT MODIFY
current_file = Path(__file__).resolve()
orchestrator_root = current_file
while orchestrator_root != orchestrator_root.parent:
    if (orchestrator_root / ".git").exists() and (orchestrator_root / "base").exists():
        break
    orchestrator_root = orchestrator_root.parent
else:
    raise RuntimeError(f"Could not find orchestrator root from {current_file}")

if str(orchestrator_root) not in sys.path:
    sys.path.insert(0, str(orchestrator_root))

module_names = {"base", "browser", "files", "compliance", "domains", "streams"}
module_root = current_file.parent
while module_root != orchestrator_root:
    if module_root.name in module_names:
        if str(module_root) not in sys.path:
            sys.path.insert(0, str(module_root))
        break
    module_root = module_root.parent

from base.backend.mcp.server_base import StandardMCPServer  # noqa: E402
from browser.backend.core.management.manager import ChromeManager  # noqa: E402

# Add chrome directory to path for tool imports
sys.path.insert(0, str(Path(__file__).parent))
from tools.definitions import register_all_tools  # noqa: E402
from tools.executor import ToolExecutor  # noqa: E402
from tools.registry import ToolRegistry  # noqa: E402


class BrowserMCPServer(StandardMCPServer[ToolRegistry, ToolExecutor]):
    """MCP server for Chrome Manager - defines browser automation tools only."""

    def __init__(self, manager: ChromeManager, config: dict | None = None):
        """Initialize Chrome MCP server.

        Args:
            manager: Chrome manager instance
            config: Server configuration
        """
        self.manager = manager
        # Pass manager to parent for executor initialization
        super().__init__(config, manager=manager)
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
