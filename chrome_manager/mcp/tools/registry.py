"""Tool registry for MCP server."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class MCPTool:
    """MCP Tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable | None = None
    category: str = "general"


class ToolRegistry:
    """Registry for MCP tools."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._categories: dict[str, list[str]] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, tool: MCPTool, handler: Callable | None = None) -> None:
        """Register a tool with the registry."""
        self._tools[tool.name] = tool

        # Store handler if provided
        if handler or tool.handler:
            self._handlers[tool.name] = handler or tool.handler

        # Add to category
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)

        logger.debug(f"Registered tool: {tool.name} in category: {tool.category}")

    def get_tool(self, name: str) -> MCPTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Callable | None:
        """Get a tool handler by name."""
        return self._handlers.get(name)

    def list_tools(self) -> list[MCPTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def get_tools_by_category(self, category: str) -> list[MCPTool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]

    def to_mcp_format(self) -> list[dict[str, Any]]:
        """Convert tools to MCP protocol format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": tool.parameters.get("properties", {}),
                    "required": tool.parameters.get("required", []),
                },
            }
            for tool in self._tools.values()
        ]
