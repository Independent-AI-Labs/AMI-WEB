"""Tool executor for MCP server."""

import base64
from typing import Any

from loguru import logger

from chrome_manager.core.management.manager import ChromeManager


class ToolExecutor:
    """Executes MCP tools."""

    def __init__(self, manager: ChromeManager):
        self.manager = manager
        self._active_instance_id: str | None = None

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

    async def _execute_browser_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:  # noqa: C901, PLR0911, PLR0912, PLR0915
        """Execute browser-related tools."""
        # Browser lifecycle tools
        if tool_name == "browser_launch":
            instance = await self.manager.get_or_create_instance(
                headless=arguments.get("headless", True),
                profile=arguments.get("profile"),
                anti_detect=arguments.get("anti_detect", False),
                use_pool=False,
            )
            self._active_instance_id = instance.id
            return {"instance_id": instance.id, "status": "launched"}

        if tool_name == "browser_terminate":
            instance_id = arguments.get("instance_id") or self._active_instance_id
            if not instance_id:
                raise ValueError("No instance_id provided")
            await self.manager.terminate_instance(instance_id)
            if instance_id == self._active_instance_id:
                self._active_instance_id = None
            return {"status": "terminated"}

        if tool_name == "browser_list":
            instances = self.manager.list_instances()
            return {"instances": instances}

        if tool_name == "browser_get_active":
            return {"instance_id": self._active_instance_id}

        # Get active instance for other browser operations
        instance = await self._get_active_instance(arguments.get("instance_id"))

        # Navigation tools
        if tool_name == "browser_navigate":
            from chrome_manager.facade.navigation.navigator import Navigator

            nav = Navigator(instance)
            # Don't pass wait_for as a string - Navigator expects None or a WaitCondition object
            await nav.navigate(
                arguments["url"],
                wait_for=None,  # Will default to waiting for load
                timeout=arguments.get("timeout", 30),
            )
            return {"status": "navigated", "url": arguments["url"]}

        if tool_name == "browser_back":
            from chrome_manager.facade.navigation.navigator import Navigator

            nav = Navigator(instance)
            await nav.back()
            return {"status": "navigated_back"}

        if tool_name == "browser_forward":
            from chrome_manager.facade.navigation.navigator import Navigator

            nav = Navigator(instance)
            await nav.forward()
            return {"status": "navigated_forward"}

        if tool_name == "browser_refresh":
            from chrome_manager.facade.navigation.navigator import Navigator

            nav = Navigator(instance)
            await nav.refresh()
            return {"status": "refreshed"}

        if tool_name == "browser_get_url":
            return {"url": instance.driver.current_url}

        # Input tools
        if tool_name == "browser_click":
            from chrome_manager.facade.input.mouse import MouseController

            mouse = MouseController(instance)
            # MouseController.click doesn't take button/click_count params
            # Just use the selector for now
            await mouse.click(arguments["selector"])
            return {"status": "clicked"}

        if tool_name == "browser_type":
            from chrome_manager.facade.input.keyboard import KeyboardController

            input_ctrl = KeyboardController(instance)
            await input_ctrl.type_text(
                arguments["selector"],
                arguments["text"],
                clear=arguments.get("clear", False),
            )
            return {"status": "typed"}

        if tool_name == "browser_select":
            from chrome_manager.facade.input.forms import FormsController

            forms = FormsController(instance)
            await forms.select_option(arguments["selector"], arguments["value"])
            return {"status": "selected"}

        if tool_name == "browser_scroll":
            from chrome_manager.facade.navigation.scroller import Scroller

            scroller = Scroller(instance)
            # Use the Scroller to handle scrolling
            direction = arguments.get("direction", "down")
            amount = arguments.get("amount", 300)

            # Map direction to x/y offsets
            x_offset = 0
            y_offset = 0
            if direction == "down":
                y_offset = amount
            elif direction == "up":
                y_offset = -amount
            elif direction == "left":
                x_offset = -amount
            elif direction == "right":
                x_offset = amount

            await scroller.scroll_by(x=x_offset, y=y_offset)
            return {"status": "scrolled"}

        if tool_name == "browser_execute_script":
            script = arguments["script"]
            args = arguments.get("args", [])
            result = instance.driver.execute_script(script, *args)
            return {"result": result}

        # Content extraction tools
        if tool_name == "browser_get_text":
            from chrome_manager.facade.navigation.extractor import ContentExtractor

            extractor = ContentExtractor(instance)
            text = await extractor.extract_text()
            return {"text": text}

        if tool_name == "browser_get_html":
            from chrome_manager.facade.navigation.extractor import ContentExtractor

            extractor = ContentExtractor(instance)
            if selector := arguments.get("selector"):
                html = await extractor.get_element_html(selector)
            else:
                html = await extractor.get_page_source()
            return {"html": html}

        if tool_name == "browser_extract_forms":
            from chrome_manager.facade.navigation.extractor import ContentExtractor

            extractor = ContentExtractor(instance)
            forms_data = await extractor.extract_forms()
            return {"forms": forms_data}

        if tool_name == "browser_extract_links":
            from chrome_manager.facade.navigation.extractor import ContentExtractor

            extractor = ContentExtractor(instance)
            links = await extractor.extract_links(absolute=arguments.get("absolute", True))
            return {"links": links}

        # Screenshot tools
        if tool_name == "browser_screenshot":
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

        # Storage tools
        if tool_name == "browser_get_cookies":
            # Get cookies directly from driver
            cookies = instance.driver.get_cookies()
            return {"cookies": cookies}

        if tool_name == "browser_set_cookies":
            # Set cookies directly without navigation
            cookies = arguments["cookies"]
            for cookie in cookies:
                # Ensure required fields
                cookie_dict = {"name": cookie["name"], "value": cookie["value"]}
                # Add optional fields if present
                if "domain" in cookie:
                    cookie_dict["domain"] = cookie["domain"]
                if "path" in cookie:
                    cookie_dict["path"] = cookie.get("path", "/")
                instance.driver.add_cookie(cookie_dict)
            return {"status": "set", "count": len(cookies)}

        if tool_name == "browser_clear_cookies":
            instance.driver.delete_all_cookies()
            return {"status": "cleared"}

        # Tab management tools
        if tool_name == "browser_get_tabs":
            # Get all window handles
            tabs = []
            current_handle = instance.driver.current_window_handle
            for handle in instance.driver.window_handles:
                instance.driver.switch_to.window(handle)
                tabs.append({"id": handle, "title": instance.driver.title, "url": instance.driver.current_url, "active": handle == current_handle})
            # Switch back to current tab
            instance.driver.switch_to.window(current_handle)
            return {"tabs": tabs}

        if tool_name == "browser_switch_tab":
            tab_id = arguments["tab_id"]
            instance.driver.switch_to.window(tab_id)
            return {"status": "switched"}

        # Logging tools
        if tool_name == "browser_get_console_logs":
            logs = await instance.get_console_logs()
            # Convert datetime to string for JSON serialization
            return {"logs": [log.model_dump(mode="json") for log in logs]}

        if tool_name == "browser_get_network_logs":
            logs = await instance._monitor.get_network_logs(instance.driver)
            # Convert datetime to string for JSON serialization
            return {"logs": [log.model_dump(mode="json") for log in logs]}

        raise ValueError(f"Unknown browser tool: {tool_name}")

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
            except Exception:
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
