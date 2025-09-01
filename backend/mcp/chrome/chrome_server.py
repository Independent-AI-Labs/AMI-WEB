"""Chrome MCP server using FastMCP."""

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from typing import Any, Literal  # noqa: E402

from mcp.server import FastMCP  # noqa: E402

from backend.core.management.manager import ChromeManager  # noqa: E402

from .response import BrowserResponse  # noqa: E402
from .tools.browser_tools import (  # noqa: E402
    browser_get_active_tool,
    browser_launch_tool,
    browser_list_tool,
    browser_terminate_tool,
)
from .tools.extraction_tools import (  # noqa: E402
    browser_exists_tool,
    browser_get_attribute_tool,
    browser_get_cookies_tool,
    browser_get_text_tool,
    browser_wait_for_tool,
)
from .tools.input_tools import (  # noqa: E402
    browser_click_tool,
    browser_hover_tool,
    browser_press_tool,
    browser_scroll_tool,
    browser_select_tool,
    browser_type_tool,
)
from .tools.javascript_tools import (  # noqa: E402
    browser_evaluate_tool,
    browser_execute_tool,
)
from .tools.navigation_tools import (  # noqa: E402
    browser_back_tool,
    browser_forward_tool,
    browser_get_url_tool,
    browser_navigate_tool,
    browser_refresh_tool,
)
from .tools.screenshot_tools import (  # noqa: E402
    browser_element_screenshot_tool,
    browser_screenshot_tool,
)


class ChromeFastMCPServer:
    """Chrome MCP server using FastMCP."""

    def __init__(self, config: dict[str, Any | None] | None = None):
        """Initialize Chrome FastMCP server."""
        self.config = config or {}

        # Create FastMCP server
        self.mcp = FastMCP(name="ChromeMCPServer")

        # Initialize Chrome manager
        config_file = self.config.get("config_file") if self.config else None
        self.manager = ChromeManager(config_file=config_file)

        # Manager will be started when needed, not in __init__
        # This avoids event loop issues when the server is already in an async context

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:  # noqa: C901
        """Register Chrome tools with FastMCP."""

        # Browser lifecycle tools
        @self.mcp.tool(description="Launch a new browser instance")
        async def browser_launch(headless: bool = False, profile: str | None = None, anti_detect: bool = False, use_pool: bool = True) -> str:
            """Launch a browser instance."""
            response = await browser_launch_tool(self.manager, headless, profile, anti_detect, use_pool)
            return response.model_dump_json()

        @self.mcp.tool(description="Terminate a browser instance")
        async def browser_terminate(instance_id: str) -> str:
            """Terminate a browser instance."""
            response = await browser_terminate_tool(self.manager, instance_id)
            return response.model_dump_json()

        @self.mcp.tool(description="List all browser instances")
        async def browser_list() -> BrowserResponse:
            """List all browser instances."""
            return await browser_list_tool(self.manager)

        @self.mcp.tool(description="Get the currently active browser instance")
        async def browser_get_active() -> BrowserResponse:
            """Get active browser instance."""
            return await browser_get_active_tool(self.manager)

        # Navigation tools
        @self.mcp.tool(description="Navigate to a URL")
        async def browser_navigate(url: str, wait_for: str | None = None, timeout: float = 30) -> BrowserResponse:
            """Navigate to URL."""
            return await browser_navigate_tool(self.manager, url, wait_for, timeout)

        @self.mcp.tool(description="Navigate back in browser history")
        async def browser_back() -> BrowserResponse:
            """Navigate back."""
            return await browser_back_tool(self.manager)

        @self.mcp.tool(description="Navigate forward in browser history")
        async def browser_forward() -> BrowserResponse:
            """Navigate forward."""
            return await browser_forward_tool(self.manager)

        @self.mcp.tool(description="Refresh the current page")
        async def browser_refresh() -> BrowserResponse:
            """Refresh page."""
            return await browser_refresh_tool(self.manager)

        @self.mcp.tool(description="Get the current page URL")
        async def browser_get_url() -> BrowserResponse:
            """Get current URL."""
            return await browser_get_url_tool(self.manager)

        # Input tools
        @self.mcp.tool(description="Click on an element")
        async def browser_click(selector: str, button: str = "left", click_count: int = 1) -> BrowserResponse:
            """Click element."""
            return await browser_click_tool(self.manager, selector, button, click_count)

        @self.mcp.tool(description="Type text into an element")
        async def browser_type(selector: str, text: str, clear: bool = False, delay: float = 0) -> BrowserResponse:
            """Type text."""
            return await browser_type_tool(self.manager, selector, text, clear, delay)

        @self.mcp.tool(description="Select an option from a dropdown")
        async def browser_select(selector: str, value: str | None = None, index: int | None = None, label: str | None = None) -> BrowserResponse:
            """Select option."""
            return await browser_select_tool(self.manager, selector, value, index, label)

        @self.mcp.tool(description="Hover over an element")
        async def browser_hover(selector: str) -> BrowserResponse:
            """Hover over element."""
            return await browser_hover_tool(self.manager, selector)

        @self.mcp.tool(description="Scroll page or element")
        async def browser_scroll(direction: str = "down", amount: int = 100) -> BrowserResponse:
            """Scroll page."""
            return await browser_scroll_tool(self.manager, direction, amount)

        @self.mcp.tool(description="Press keyboard keys")
        async def browser_press(key: str, modifiers: list[str | None] | None = None) -> BrowserResponse:
            """Press keys."""
            return await browser_press_tool(self.manager, key, modifiers)

        # Extraction tools
        @self.mcp.tool(description="Get text content of an element")
        async def browser_get_text(selector: str) -> BrowserResponse:
            """Get element text."""
            return await browser_get_text_tool(self.manager, selector)

        @self.mcp.tool(description="Get attribute value of an element")
        async def browser_get_attribute(selector: str, attribute: str) -> BrowserResponse:
            """Get element attribute."""
            return await browser_get_attribute_tool(self.manager, selector, attribute)

        @self.mcp.tool(description="Check if an element exists")
        async def browser_exists(selector: str) -> BrowserResponse:
            """Check element exists."""
            return await browser_exists_tool(self.manager, selector)

        @self.mcp.tool(description="Wait for an element to appear")
        async def browser_wait_for(selector: str, state: str = "visible", timeout: float = 30) -> BrowserResponse:
            """Wait for element."""
            return await browser_wait_for_tool(self.manager, selector, state, timeout)

        @self.mcp.tool(description="Get browser cookies")
        async def browser_get_cookies() -> BrowserResponse:
            """Get cookies."""
            return await browser_get_cookies_tool(self.manager)

        # Screenshot tools
        @self.mcp.tool(description="Take a screenshot of the page")
        async def browser_screenshot(full_page: bool = False) -> BrowserResponse:
            """Take screenshot."""
            return await browser_screenshot_tool(self.manager, full_page)

        @self.mcp.tool(description="Take a screenshot of an element")
        async def browser_element_screenshot(selector: str) -> BrowserResponse:
            """Take element screenshot."""
            return await browser_element_screenshot_tool(self.manager, selector)

        # JavaScript tools
        @self.mcp.tool(description="Execute JavaScript code")
        async def browser_execute(script: str, args: list[Any | None] | None = None) -> BrowserResponse:
            """Execute JavaScript."""
            return await browser_execute_tool(self.manager, script, args)

        @self.mcp.tool(description="Evaluate JavaScript expression")
        async def browser_evaluate(expression: str) -> BrowserResponse:
            """Evaluate JavaScript."""
            return await browser_evaluate_tool(self.manager, expression)

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
        """Run the server.

        Args:
            transport: Transport type (stdio, sse, or streamable-http)
        """
        self.mcp.run(transport=transport)
