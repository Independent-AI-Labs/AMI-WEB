"""MCP Server for Chrome Manager - compatibility wrapper."""

from chrome_manager.mcp.chrome_server import ChromeMCPServer

# Export ChromeMCPServer as MCPServer for backward compatibility
MCPServer = ChromeMCPServer

__all__ = ["MCPServer"]
