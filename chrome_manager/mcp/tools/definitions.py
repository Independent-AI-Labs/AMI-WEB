"""Tool definitions for MCP server."""

from .registry import MCPTool

# Browser lifecycle tools
BROWSER_TOOLS = [
    MCPTool(
        name="browser_launch",
        description="Launch a new browser instance",
        category="browser",
        parameters={
            "properties": {
                "headless": {"type": "boolean", "description": "Run browser in headless mode"},
                "profile": {"type": "string", "description": "Browser profile name"},
                "anti_detect": {"type": "boolean", "description": "Enable anti-detection features"},
            },
            "required": [],
        },
    ),
    MCPTool(
        name="browser_terminate",
        description="Terminate a browser instance",
        category="browser",
        parameters={
            "properties": {
                "instance_id": {"type": "string", "description": "Browser instance ID"},
            },
            "required": ["instance_id"],
        },
    ),
    MCPTool(
        name="browser_list",
        description="List all browser instances",
        category="browser",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_get_active",
        description="Get the currently active browser instance",
        category="browser",
        parameters={"properties": {}, "required": []},
    ),
]

# Navigation tools
NAVIGATION_TOOLS = [
    MCPTool(
        name="browser_navigate",
        description="Navigate to a URL",
        category="navigation",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "wait_for": {"type": "string", "description": "Wait condition"},
                "timeout": {"type": "number", "description": "Navigation timeout in seconds"},
            },
            "required": ["url"],
        },
    ),
    MCPTool(
        name="browser_back",
        description="Navigate back in browser history",
        category="navigation",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_forward",
        description="Navigate forward in browser history",
        category="navigation",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_refresh",
        description="Refresh the current page",
        category="navigation",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_get_url",
        description="Get the current page URL",
        category="navigation",
        parameters={"properties": {}, "required": []},
    ),
]

# Input tools
INPUT_TOOLS = [
    MCPTool(
        name="browser_click",
        description="Click on an element",
        category="input",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"},
                "click_count": {"type": "number", "description": "Number of clicks"},
            },
            "required": ["selector"],
        },
    ),
    MCPTool(
        name="browser_type",
        description="Type text into an input field",
        category="input",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "text": {"type": "string", "description": "Text to type"},
                "clear": {"type": "boolean", "description": "Clear field before typing"},
            },
            "required": ["selector", "text"],
        },
    ),
    MCPTool(
        name="browser_select",
        description="Select an option from a dropdown",
        category="input",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the select element"},
                "value": {"type": "string", "description": "Option value to select"},
            },
            "required": ["selector", "value"],
        },
    ),
    MCPTool(
        name="browser_scroll",
        description="Scroll the page",
        category="input",
        parameters={
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "amount": {"type": "number", "description": "Pixels to scroll"},
            },
            "required": [],
        },
    ),
    MCPTool(
        name="browser_execute_script",
        description="Execute JavaScript in the browser",
        category="input",
        parameters={
            "properties": {
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "script": {"type": "string", "description": "JavaScript code to execute"},
                "args": {"type": "array", "description": "Arguments to pass to the script"},
            },
            "required": ["script"],
        },
    ),
]

# Content extraction tools
CONTENT_TOOLS = [
    MCPTool(
        name="browser_get_text",
        description="Extract text from the page",
        category="content",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector (optional, defaults to body)"},
            },
            "required": [],
        },
    ),
    MCPTool(
        name="browser_get_html",
        description="Get HTML content of the page",
        category="content",
        parameters={
            "properties": {
                "selector": {"type": "string", "description": "CSS selector (optional, defaults to full page)"},
            },
            "required": [],
        },
    ),
    MCPTool(
        name="browser_extract_forms",
        description="Extract all forms from the page",
        category="content",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_extract_links",
        description="Extract all links from the page",
        category="content",
        parameters={
            "properties": {
                "absolute": {"type": "boolean", "description": "Convert to absolute URLs"},
            },
            "required": [],
        },
    ),
]

# Screenshot tools
SCREENSHOT_TOOLS = [
    MCPTool(
        name="browser_screenshot",
        description="Take a screenshot of the page",
        category="screenshot",
        parameters={
            "properties": {
                "full_page": {"type": "boolean", "description": "Capture full page"},
                "selector": {"type": "string", "description": "Element to screenshot"},
            },
            "required": [],
        },
    ),
]

# Tab management tools
TAB_TOOLS = [
    MCPTool(
        name="browser_get_tabs",
        description="Get list of open tabs",
        category="tabs",
        parameters={
            "properties": {
                "instance_id": {"type": "string", "description": "Browser instance ID"},
            },
            "required": [],
        },
    ),
    MCPTool(
        name="browser_switch_tab",
        description="Switch to a specific tab",
        category="tabs",
        parameters={
            "properties": {
                "instance_id": {"type": "string", "description": "Browser instance ID"},
                "tab_id": {"type": "string", "description": "Tab ID to switch to"},
            },
            "required": ["tab_id"],
        },
    ),
]

# Cookie and storage tools
STORAGE_TOOLS = [
    MCPTool(
        name="browser_get_cookies",
        description="Get browser cookies",
        category="storage",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_set_cookies",
        description="Set browser cookies",
        category="storage",
        parameters={
            "properties": {
                "cookies": {"type": "array", "description": "List of cookie objects"},
            },
            "required": ["cookies"],
        },
    ),
    MCPTool(
        name="browser_clear_cookies",
        description="Clear browser cookies",
        category="storage",
        parameters={"properties": {}, "required": []},
    ),
]

# Console and logging tools
LOGGING_TOOLS = [
    MCPTool(
        name="browser_get_console_logs",
        description="Get browser console logs",
        category="logging",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="browser_get_network_logs",
        description="Get network activity logs",
        category="logging",
        parameters={"properties": {}, "required": []},
    ),
]

# Profile management tools
PROFILE_TOOLS = [
    MCPTool(
        name="profile_create",
        description="Create a new browser profile",
        category="profile",
        parameters={
            "properties": {
                "name": {"type": "string", "description": "Profile name"},
                "description": {"type": "string", "description": "Profile description"},
            },
            "required": ["name"],
        },
    ),
    MCPTool(
        name="profile_list",
        description="List all browser profiles",
        category="profile",
        parameters={"properties": {}, "required": []},
    ),
    MCPTool(
        name="profile_delete",
        description="Delete a browser profile",
        category="profile",
        parameters={
            "properties": {
                "name": {"type": "string", "description": "Profile name"},
            },
            "required": ["name"],
        },
    ),
]

# Session management tools
SESSION_TOOLS = [
    MCPTool(
        name="session_save",
        description="Save current browser session",
        category="session",
        parameters={
            "properties": {
                "name": {"type": "string", "description": "Session name"},
            },
            "required": ["name"],
        },
    ),
    MCPTool(
        name="session_load",
        description="Load a saved browser session",
        category="session",
        parameters={
            "properties": {
                "name": {"type": "string", "description": "Session name"},
            },
            "required": ["name"],
        },
    ),
    MCPTool(
        name="session_list",
        description="List all saved sessions",
        category="session",
        parameters={"properties": {}, "required": []},
    ),
]

# All tool collections
ALL_TOOLS = (
    BROWSER_TOOLS
    + NAVIGATION_TOOLS
    + INPUT_TOOLS
    + CONTENT_TOOLS
    + SCREENSHOT_TOOLS
    + TAB_TOOLS
    + STORAGE_TOOLS
    + LOGGING_TOOLS
    + PROFILE_TOOLS
    + SESSION_TOOLS
)


def register_all_tools(registry):
    """Register all tools with the registry."""
    for tool in ALL_TOOLS:
        registry.register(tool)
    return registry
