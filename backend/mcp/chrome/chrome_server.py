"""Chrome MCP server using FastMCP."""

# Use standard import setup
from base.backend.utils.standard_imports import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

from pathlib import Path  # noqa: E402
from typing import Any, Literal  # noqa: E402

from mcp.server import FastMCP  # noqa: E402

from browser.backend.core.management.manager import ChromeManager  # noqa: E402
from browser.backend.mcp.chrome.response import BrowserResponse  # noqa: E402
from browser.backend.mcp.chrome.tools.facade import (  # noqa: E402
    browser_capture_tool,
    browser_execute_tool,
    browser_extract_tool,
    browser_inspect_tool,
    browser_interact_tool,
    browser_navigate_tool,
    browser_profile_tool,
    browser_react_tool,
    browser_session_tool,
    browser_storage_tool,
)
from browser.backend.mcp.chrome.tools.search_tools import browser_web_search_tool  # noqa: E402


class ChromeFastMCPServer:
    """Chrome MCP server using FastMCP."""

    def __init__(
        self, data_root: Path | None = None, config: dict[str, Any | None] | None = None
    ):
        """Initialize Chrome FastMCP server."""

        self.config = config or {}
        self.data_root = data_root

        # Create FastMCP server
        self.mcp = FastMCP(name="ChromeMCPServer")

        # Initialize Chrome manager with absolute storage paths
        config_file = self.config.get("config_file") if self.config else None
        storage_config = {}
        if self.data_root:
            storage_config = {
                "backend.storage.session_dir": str(self.data_root / "sessions"),
                "backend.storage.profiles_dir": str(self.data_root / "profiles"),
                "backend.storage.downloads_dir": str(self.data_root / "downloads"),
                "backend.storage.screenshots_dir": str(self.data_root / "screenshots"),
            }

        self.manager = ChromeManager(
            config_file=config_file, config_overrides=storage_config
        )

        # Manager will be started when needed, not in __init__
        # This avoids event loop issues when the server is already in an async context

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register V02 simplified facade tools with FastMCP."""

        # V02 Facade Tool 1: browser_session - Instance lifecycle and session persistence
        @self.mcp.tool(
            description=(
                "Manage browser instance lifecycle (launch, terminate, list, get_active) "
                "and session persistence (save, restore, list_sessions, delete_session, rename_session). "
                "Session save captures all open tabs, cookies, and active tab state. "
                "Session restore recreates the exact browser state including all tabs. "
                "Use kill_orphaned=True when restoring to clear stale Chrome processes holding profile locks."
            )
        )
        async def browser_session(
            action: Literal[
                "launch",
                "terminate",
                "list",
                "get_active",
                "save",
                "restore",
                "list_sessions",
                "delete_session",
                "rename_session",
            ],
            instance_id: str | None = None,
            headless: bool = True,
            profile: str | None = None,
            anti_detect: bool | None = None,
            use_pool: bool = True,
            session_id: str | None = None,
            session_name: str | None = None,
            kill_orphaned: bool = False,
        ) -> BrowserResponse:
            """Manage browser sessions."""
            return await browser_session_tool(
                self.manager,
                action,
                instance_id,
                headless,
                profile,
                anti_detect,
                use_pool,
                session_id,
                session_name,
                kill_orphaned,
            )

        # V02 Facade Tool 2: browser_navigate - Page navigation, history, and tab management
        @self.mcp.tool(
            description=(
                "Navigate pages and manage browser history and tabs "
                "(goto, back, forward, refresh, get_url, open_tab, close_tab, switch_tab, list_tabs)"
            )
        )
        async def browser_navigate(
            action: Literal[
                "goto",
                "back",
                "forward",
                "refresh",
                "get_url",
                "open_tab",
                "close_tab",
                "switch_tab",
                "list_tabs",
            ],
            url: str | None = None,
            wait_for: str | None = None,
            timeout: float = 30,
            tab_id: str | None = None,
        ) -> BrowserResponse:
            """Navigate pages and manage tabs."""
            return await browser_navigate_tool(
                self.manager, action, url, wait_for, timeout, tab_id
            )

        # V02 Facade Tool 3: browser_interact - Element interaction and waiting
        @self.mcp.tool(
            description="Interact with page elements (click, type, select, hover, scroll, press, wait)"
        )
        async def browser_interact(
            action: Literal[
                "click", "type", "select", "hover", "scroll", "press", "wait"
            ],
            selector: str | None = None,
            text: str | None = None,
            clear: bool = False,
            delay: float = 0,
            button: str = "left",
            click_count: int = 1,
            value: str | None = None,
            index: int | None = None,
            label: str | None = None,
            direction: str = "down",
            amount: int = 100,
            key: str | None = None,
            modifiers: list[str | None] | None = None,
            state: str = "visible",
            timeout: float = 30,
        ) -> BrowserResponse:
            """Interact with elements."""
            return await browser_interact_tool(
                self.manager,
                action,
                selector,
                text,
                clear,
                delay,
                button,
                click_count,
                value,
                index,
                label,
                direction,
                amount,
                key,
                modifiers,
                state,
                timeout,
            )

        # V02 Facade Tool 4: browser_inspect - DOM structure inspection
        @self.mcp.tool(
            description="Inspect DOM structure and element properties (get_html, exists, get_attribute)"
        )
        async def browser_inspect(
            action: Literal["get_html", "exists", "get_attribute"],
            selector: str | None = None,
            max_depth: int | None = None,
            collapse_depth: int | None = None,
            ellipsize_text_after: int | None = None,
            attribute: str | None = None,
        ) -> BrowserResponse:
            """Inspect DOM."""
            return await browser_inspect_tool(
                self.manager,
                action,
                selector,
                max_depth,
                collapse_depth,
                ellipsize_text_after,
                attribute,
            )

        # V02 Facade Tool 5: browser_extract - Content extraction
        @self.mcp.tool(
            description=(
                "Extract text content with tags and cookies (get_text, get_cookies). "
                "Supports chunking for large text extractions with deterministic byte-offset pagination. "
                "Use snapshot_checksum to ensure consistency across chunks."
            )
        )
        async def browser_extract(
            action: Literal["get_text", "get_cookies"],
            selector: str | None = None,
            use_chunking: bool = False,
            offset: int = 0,
            length: int | None = None,
            snapshot_checksum: str | None = None,
            ellipsize_text_after: int = 128,
            include_tag_names: bool = True,
            skip_hidden: bool = True,
            max_depth: int | None = None,
        ) -> BrowserResponse:
            """Extract content."""
            return await browser_extract_tool(
                self.manager,
                action,
                selector,
                use_chunking,
                offset,
                length,
                snapshot_checksum,
                ellipsize_text_after,
                include_tag_names,
                skip_hidden,
                max_depth,
            )

        # V02 Facade Tool 6: browser_capture - Visual capture
        @self.mcp.tool(
            description="Capture screenshots (screenshot, element_screenshot)"
        )
        async def browser_capture(
            action: Literal["screenshot", "element_screenshot"],
            selector: str | None = None,
            full_page: bool = False,
            save_to_disk: bool = True,
        ) -> BrowserResponse:
            """Capture screenshots."""
            return await browser_capture_tool(
                self.manager, action, selector, full_page, save_to_disk
            )

        # V02 Facade Tool 7: browser_execute - JavaScript execution with validation
        @self.mcp.tool(
            description=(
                "Execute JavaScript code or evaluate expressions (execute, evaluate). "
                "All scripts are validated against forbidden patterns before execution. "
                "Dangerous operations like window.open('url', '_blank') and window.close() "
                "are blocked to prevent tab corruption and state loss. "
                "Use proper browser tools (browser_session, browser_navigate) instead of direct DOM manipulation."
            )
        )
        async def browser_execute(
            action: Literal["execute", "evaluate"],
            code: str,
            args: list[Any | None] | None = None,
            use_chunking: bool = False,
            offset: int = 0,
            length: int | None = None,
            snapshot_checksum: str | None = None,
        ) -> BrowserResponse:
            """Execute JavaScript with validation."""
            return await browser_execute_tool(
                self.manager,
                action,
                code,
                args,
                use_chunking,
                offset,
                length,
                snapshot_checksum,
            )

        # V02 Tool 8: web_search - Web search (unchanged from V01)
        @self.mcp.tool(description="Run a web search using the configured engine")
        async def web_search(
            query: str,
            max_results: int = 10,
            search_engine_url: str | None = None,
            timeout: float | None = None,
        ) -> BrowserResponse:
            """Run web search."""
            return await browser_web_search_tool(
                self.manager,
                query,
                max_results=max_results,
                search_engine_url=search_engine_url,
                timeout=timeout,
            )

        # V02 Tool 9: browser_storage - Download and screenshot storage management
        @self.mcp.tool(
            description="Manage downloads and screenshots (list, clear, wait, set behavior)"
        )
        async def browser_storage(
            action: Literal[
                "list_downloads",
                "clear_downloads",
                "wait_for_download",
                "list_screenshots",
                "clear_screenshots",
                "set_download_behavior",
            ],
            instance_id: str | None = None,
            filename: str | None = None,
            timeout: int = 30,
            behavior: str = "allow",
            download_path: str | None = None,
        ) -> BrowserResponse:
            """Manage storage."""
            return await browser_storage_tool(
                self.manager,
                action,
                instance_id,
                filename,
                timeout,
                behavior,
                download_path,
            )

        # V02 Tool 10: browser_react - React-specific interactions
        @self.mcp.tool(
            description="React-specific helpers for triggering handlers and inspecting components"
        )
        async def browser_react(
            action: Literal[
                "trigger_handler",
                "get_props",
                "get_state",
                "find_component",
                "get_fiber_tree",
            ],
            selector: str | None = None,
            handler_name: str | None = None,
            event_data: dict[str, Any] | None = None,
            component_name: str | None = None,
            max_depth: int = 10,
        ) -> BrowserResponse:
            """React-specific interactions."""
            return await browser_react_tool(
                self.manager,
                action,
                selector,
                handler_name,
                event_data,
                component_name,
                max_depth,
            )

        # V02 Tool 11: browser_profile - Profile management
        @self.mcp.tool(
            description="Manage browser profiles (create, delete, list, copy)"
        )
        async def browser_profile(
            action: Literal["create", "delete", "list", "copy"],
            profile_name: str | None = None,
            description: str | None = None,
            source_profile: str | None = None,
            dest_profile: str | None = None,
        ) -> BrowserResponse:
            """Manage browser profiles."""
            return await browser_profile_tool(
                self.manager,
                action,
                profile_name,
                description,
                source_profile,
                dest_profile,
            )

    def run(
        self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    ) -> None:
        """Run the server.

        Args:
            transport: Transport type (stdio, sse, or streamable-http)
        """
        self.mcp.run(transport=transport)
