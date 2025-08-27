"""Tool executor for MCP server."""

import base64
from collections.abc import Awaitable, Callable
from typing import Any

from browser.backend.core.management.manager import ChromeManager
from browser.backend.facade.input.forms import FormsController
from browser.backend.facade.input.keyboard import KeyboardController
from browser.backend.facade.input.mouse import MouseController
from browser.backend.facade.navigation.extractor import ContentExtractor
from browser.backend.facade.navigation.navigator import Navigator
from browser.backend.facade.navigation.scroller import Scroller
from loguru import logger


class ToolExecutor:
    """Executes MCP tools."""

    def __init__(self, manager: ChromeManager):
        self.manager = manager
        self._active_instance_id: str | None = None

        # Initialize tool dispatch maps
        self._browser_lifecycle_tools = self._init_lifecycle_tools()
        self._browser_navigation_tools = self._init_navigation_tools()
        self._browser_input_tools = self._init_input_tools()
        self._browser_content_tools = self._init_content_tools()
        self._browser_storage_tools = self._init_storage_tools()
        self._browser_tab_tools = self._init_tab_tools()
        self._browser_log_tools = self._init_log_tools()

    def _init_lifecycle_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize browser lifecycle tool handlers."""
        return {
            "browser_launch": self._handle_browser_launch,
            "browser_terminate": self._handle_browser_terminate,
            "browser_list": self._handle_browser_list,
            "browser_get_active": self._handle_browser_get_active,
        }

    def _init_navigation_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize navigation tool handlers."""
        return {
            "browser_navigate": self._handle_browser_navigate,
            "browser_back": self._handle_browser_back,
            "browser_forward": self._handle_browser_forward,
            "browser_refresh": self._handle_browser_refresh,
            "browser_get_url": self._handle_browser_get_url,
        }

    def _init_input_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize input tool handlers."""
        return {
            "browser_click": self._handle_browser_click,
            "browser_type": self._handle_browser_type,
            "browser_select": self._handle_browser_select,
            "browser_scroll": self._handle_browser_scroll,
            "browser_fill_form": self._handle_browser_fill_form,
        }

    def _init_content_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize content extraction tool handlers."""
        return {
            "browser_get_html": self._handle_browser_get_html,
            "browser_get_text": self._handle_browser_get_text,
            "browser_execute_script": self._handle_browser_execute_script,
            "browser_extract_forms": self._handle_browser_extract_forms,
            "browser_extract_links": self._handle_browser_extract_links,
            "browser_screenshot": self._handle_browser_screenshot,
        }

    def _init_storage_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize storage tool handlers."""
        return {
            "browser_get_cookies": self._handle_browser_get_cookies,
            "browser_set_cookies": self._handle_browser_set_cookies,
            "browser_clear_cookies": self._handle_browser_clear_cookies,
        }

    def _init_tab_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize tab management tool handlers."""
        return {
            "browser_get_tabs": self._handle_browser_get_tabs,
            "browser_switch_tab": self._handle_browser_switch_tab,
        }

    def _init_log_tools(self) -> dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]]:
        """Initialize logging tool handlers."""
        return {
            "browser_get_console_logs": self._handle_browser_get_console_logs,
            "browser_get_network_logs": self._handle_browser_get_network_logs,
        }

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return the result."""
        logger.debug(f"Executing tool: {tool_name} with arguments: {arguments}")

        # Route to appropriate handler based on tool category
        if tool_name.startswith("browser_"):
            return await self._execute_browser_tool(tool_name, arguments)
        if tool_name.startswith("profile_"):
            return await self._execute_profile_tool(tool_name, arguments)
        if tool_name.startswith("session_"):
            return await self._execute_session_tool(tool_name, arguments)
        raise ValueError(f"Unknown tool: {tool_name}")

    async def _execute_browser_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0911
        """Execute browser-related tools using dispatch maps."""
        # Check lifecycle tools
        if handler := self._browser_lifecycle_tools.get(tool_name):
            return await handler(arguments)

        # All other tools need an active instance
        instance = await self._get_active_instance(arguments.get("instance_id"))

        # Store instance for handlers that need it
        self._current_instance = instance

        # Check navigation tools
        if handler := self._browser_navigation_tools.get(tool_name):
            return await handler(arguments)

        # Check input tools
        if handler := self._browser_input_tools.get(tool_name):
            return await handler(arguments)

        # Check content tools
        if handler := self._browser_content_tools.get(tool_name):
            return await handler(arguments)

        # Check storage tools
        if handler := self._browser_storage_tools.get(tool_name):
            return await handler(arguments)

        # Check tab tools
        if handler := self._browser_tab_tools.get(tool_name):
            return await handler(arguments)

        # Check log tools
        if handler := self._browser_log_tools.get(tool_name):
            return await handler(arguments)

        raise ValueError(f"Unknown browser tool: {tool_name}")

    # Lifecycle handlers
    async def _handle_browser_launch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser launch."""
        instance = await self.manager.get_or_create_instance(
            headless=arguments.get("headless", True),
            profile=arguments.get("profile"),
            anti_detect=arguments.get("anti_detect", False),
            use_pool=False,
        )
        self._active_instance_id = instance.id
        return {"instance_id": instance.id, "status": "launched"}

    async def _handle_browser_terminate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser termination."""
        instance_id = arguments.get("instance_id") or self._active_instance_id
        if not instance_id:
            raise ValueError("No instance_id provided")
        await self.manager.terminate_instance(instance_id)
        if instance_id == self._active_instance_id:
            self._active_instance_id = None
        return {"status": "terminated"}

    async def _handle_browser_list(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser list."""
        instances = await self.manager.list_instances()
        # Convert InstanceInfo objects to dicts for JSON serialization
        # Use mode='json' to convert enums and datetimes properly
        return {"instances": [inst.model_dump(mode="json") for inst in instances]}

    async def _handle_browser_get_active(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get active browser."""
        return {"instance_id": self._active_instance_id}

    # Navigation handlers
    async def _handle_browser_navigate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser navigation."""

        nav = Navigator(self._current_instance)
        # Don't pass wait_for as a string - Navigator expects None or a WaitCondition object
        await nav.navigate(
            arguments["url"],
            wait_for=None,  # Will default to waiting for load
            timeout=arguments.get("timeout", 30),
        )
        return {"status": "navigated", "url": arguments["url"]}

    async def _handle_browser_back(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser back navigation."""

        nav = Navigator(self._current_instance)
        await nav.back()
        return {"status": "navigated_back"}

    async def _handle_browser_forward(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser forward navigation."""

        nav = Navigator(self._current_instance)
        await nav.forward()
        return {"status": "navigated_forward"}

    async def _handle_browser_refresh(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser refresh."""

        nav = Navigator(self._current_instance)
        await nav.refresh()
        return {"status": "refreshed"}

    async def _handle_browser_get_url(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get current URL."""
        return {"url": self._current_instance.driver.current_url}

    # Input handlers
    async def _handle_browser_click(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser click."""

        mouse = MouseController(self._current_instance)
        # MouseController.click doesn't take button/click_count params
        # Just use the selector for now
        await mouse.click(arguments["selector"])
        return {"status": "clicked"}

    async def _handle_browser_type(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser typing."""

        input_ctrl = KeyboardController(self._current_instance)
        await input_ctrl.type_text(
            arguments["selector"],
            arguments["text"],
            clear=arguments.get("clear", False),
        )
        return {"status": "typed"}

    async def _handle_browser_select(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser select."""

        forms = FormsController(self._current_instance)
        await forms.select_option(arguments["selector"], arguments["value"])
        return {"status": "selected"}

    async def _handle_browser_scroll(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser scroll."""
        scroller = Scroller(self._current_instance)
        if arguments.get("to") == "bottom":
            await scroller.scroll_to_bottom()
        elif arguments.get("to") == "top":
            await scroller.scroll_to_top()
        elif "x" in arguments or "y" in arguments:
            await scroller.scroll_to(arguments.get("x", 0), arguments.get("y", 0))
        else:
            # Default scroll down by some amount
            await scroller.scroll_by(0, 300)
        return {"status": "scrolled"}

    async def _handle_browser_fill_form(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle browser form filling."""

        forms = FormsController(self._current_instance)
        await forms.fill_form(arguments["data"], submit=arguments.get("submit", False))
        return {"status": "filled"}

    # Content extraction handlers
    async def _handle_browser_get_html(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get HTML."""

        extractor = ContentExtractor(self._current_instance)
        html = await extractor.get_parsed_html(max_tokens=arguments.get("max_tokens", 25000))
        return {"html": html}

    async def _handle_browser_get_text(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get text."""

        extractor = ContentExtractor(self._current_instance)
        text = await extractor.get_text()
        return {"text": text}

    async def _handle_browser_execute_script(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle script execution."""
        result = self._current_instance.driver.execute_script(arguments["script"])
        return {"result": result}

    async def _handle_browser_extract_forms(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle form extraction."""

        extractor = ContentExtractor(self._current_instance)
        forms = await extractor.extract_forms()
        return {"forms": forms}

    async def _handle_browser_extract_links(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle link extraction."""

        extractor = ContentExtractor(self._current_instance)
        links = await extractor.extract_links()
        return {"links": links}

    async def _handle_browser_screenshot(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle screenshot capture."""
        instance = self._current_instance
        # ScreenshotController doesn't exist, use driver directly
        if selector := arguments.get("selector"):
            element = instance.driver.find_element("css selector", selector)
            screenshot_data = element.screenshot_as_png
        elif arguments.get("full_page", False):
            # Save current position
            original_size = instance.driver.get_window_size()
            # Get full page dimensions
            width = instance.driver.execute_script("return document.body.scrollWidth")
            height = instance.driver.execute_script("return document.body.scrollHeight")
            instance.driver.set_window_size(width, height)
            screenshot_data = instance.driver.get_screenshot_as_png()
            # Restore original size
            instance.driver.set_window_size(original_size["width"], original_size["height"])
        else:
            screenshot_data = instance.driver.get_screenshot_as_png()
        # Convert bytes to base64 for JSON serialization
        screenshot_b64 = base64.b64encode(screenshot_data).decode("utf-8")
        return {"screenshot": screenshot_b64, "format": "base64"}

    # Storage handlers
    async def _handle_browser_get_cookies(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get cookies."""
        cookies = self._current_instance.driver.get_cookies()
        return {"cookies": cookies}

    async def _handle_browser_set_cookies(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle set cookies."""
        cookies = arguments["cookies"]
        for cookie in cookies:
            # Ensure required fields
            cookie_dict = {"name": cookie["name"], "value": cookie["value"]}
            # Add optional fields if present
            if "domain" in cookie:
                cookie_dict["domain"] = cookie["domain"]
            if "path" in cookie:
                cookie_dict["path"] = cookie.get("path", "/")
            self._current_instance.driver.add_cookie(cookie_dict)
        return {"status": "set", "count": len(cookies)}

    async def _handle_browser_clear_cookies(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle clear cookies."""
        self._current_instance.driver.delete_all_cookies()
        return {"status": "cleared"}

    # Tab management handlers
    async def _handle_browser_get_tabs(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get tabs."""
        instance = self._current_instance
        tabs = []
        current_handle = instance.driver.current_window_handle
        for handle in instance.driver.window_handles:
            instance.driver.switch_to.window(handle)
            tabs.append({"id": handle, "title": instance.driver.title, "url": instance.driver.current_url, "active": handle == current_handle})
        # Switch back to current tab
        instance.driver.switch_to.window(current_handle)
        return {"tabs": tabs}

    async def _handle_browser_switch_tab(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle switch tab."""
        tab_id = arguments["tab_id"]
        self._current_instance.driver.switch_to.window(tab_id)
        return {"status": "switched"}

    # Logging handlers
    async def _handle_browser_get_console_logs(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get console logs."""
        logs = await self._current_instance.get_console_logs()
        # Convert datetime to string for JSON serialization
        return {"logs": [log.model_dump(mode="json") for log in logs]}

    async def _handle_browser_get_network_logs(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get network logs."""
        logs = await self._current_instance._monitor.get_network_logs(self._current_instance.driver)
        # Convert datetime to string for JSON serialization
        return {"logs": [log.model_dump(mode="json") for log in logs]}

    async def _execute_profile_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute profile-related tools."""
        profile_manager = self.manager.profile_manager

        if tool_name == "profile_create":
            profile_dir = profile_manager.create_profile(
                arguments["name"],
                arguments.get("description", ""),
            )
            return {"status": "created", "path": str(profile_dir)}

        if tool_name == "profile_list":
            profiles = profile_manager.list_profiles()
            return {"profiles": profiles}

        if tool_name == "profile_delete":
            success = profile_manager.delete_profile(arguments["name"])
            return {"status": "deleted" if success else "not_found"}

        raise ValueError(f"Unknown profile tool: {tool_name}")

    async def _execute_session_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute session-related tools."""
        if tool_name == "session_save":
            # Get the active instance to save
            instance_id = arguments.get("instance_id") or self._active_instance_id
            if not instance_id:
                raise ValueError("No instance_id provided and no active instance")
            # Save using the manager with the provided name
            session_name = arguments.get("name")
            session_id = await self.manager.save_session(instance_id, session_name)
            return {"status": "saved", "session_id": session_id}

        if tool_name == "session_load":
            # Restore the session
            session_id = arguments["session_id"]
            try:
                instance = await self.manager.restore_session(session_id)
                self._active_instance_id = instance.id
                return {"status": "loaded", "instance_id": instance.id}
            except Exception as e:
                logger.warning(f"Failed to restore session {session_id}: {e}")
                return {"status": "not_found"}

        if tool_name == "session_list":
            sessions = await self.manager.session_manager.list_sessions()
            return {"sessions": sessions}

        raise ValueError(f"Unknown session tool: {tool_name}")

    async def _get_active_instance(self, instance_id: str | None = None):
        """Get the active browser instance."""
        if instance_id:
            self._active_instance_id = instance_id

        if not self._active_instance_id:
            # Try to get the first available instance
            instances = await self.manager.list_instances()
            if instances:
                self._active_instance_id = instances[0].id
            else:
                # Create a new instance
                instance = await self.manager.get_or_create_instance(headless=True, use_pool=False)
                self._active_instance_id = instance.id

        instance = await self.manager.get_instance(self._active_instance_id)
        if not instance:
            raise ValueError(f"Instance {self._active_instance_id} not found")
        return instance
