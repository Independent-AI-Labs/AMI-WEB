"""V02 simplified facade tools for Browser MCP."""

from browser.backend.mcp.chrome.tools.facade.capture import browser_capture_tool
from browser.backend.mcp.chrome.tools.facade.execution import browser_execute_tool
from browser.backend.mcp.chrome.tools.facade.extraction import browser_extract_tool
from browser.backend.mcp.chrome.tools.facade.inspection import browser_inspect_tool
from browser.backend.mcp.chrome.tools.facade.interaction import browser_interact_tool
from browser.backend.mcp.chrome.tools.facade.navigation import browser_navigate_tool
from browser.backend.mcp.chrome.tools.facade.react import browser_react_tool
from browser.backend.mcp.chrome.tools.facade.session import browser_session_tool
from browser.backend.mcp.chrome.tools.facade.storage import browser_storage_tool

__all__ = [
    "browser_session_tool",
    "browser_navigate_tool",
    "browser_interact_tool",
    "browser_inspect_tool",
    "browser_extract_tool",
    "browser_capture_tool",
    "browser_execute_tool",
    "browser_storage_tool",
    "browser_react_tool",
]
