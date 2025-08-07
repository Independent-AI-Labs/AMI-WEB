import asyncio
import base64
import json
import uuid
from typing import Any

import websockets
from loguru import logger
from websockets.server import WebSocketServerProtocol

from ..core.instance import BrowserInstance
from ..core.manager import ChromeManager
from ..facade.input import InputController
from ..facade.media import ScreenshotController
from ..facade.navigation import NavigationController
from ..models.browser import ClickOptions, WaitCondition
from ..models.mcp import MCPEvent, MCPTool
from ..utils.exceptions import MCPError


class MCPServer:
    def __init__(self, manager: ChromeManager, config: dict[str, Any]):
        self.manager = manager
        self.config = config
        self.clients: dict[str, WebSocketServerProtocol] = {}
        self.tools = self._register_tools()
        self.server = None

    def _register_tools(self) -> dict[str, MCPTool]:
        return {
            "browser_launch": MCPTool(
                name="browser_launch",
                description="Launch a new browser instance",
                parameters={
                    "type": "object",
                    "properties": {
                        "headless": {"type": "boolean", "default": True},
                        "profile": {"type": "string"},
                        "extensions": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            "browser_navigate": MCPTool(
                name="browser_navigate",
                description="Navigate to a URL",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "url": {"type": "string"},
                        "wait_for": {"type": "string", "enum": ["load", "networkidle", "element"]},
                    },
                    "required": ["instance_id", "url"],
                },
            ),
            "browser_click": MCPTool(
                name="browser_click",
                description="Click an element",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "selector": {"type": "string"},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                    },
                    "required": ["instance_id", "selector"],
                },
            ),
            "browser_type": MCPTool(
                name="browser_type",
                description="Type text into an element",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "selector": {"type": "string"},
                        "text": {"type": "string"},
                        "clear": {"type": "boolean", "default": True},
                    },
                    "required": ["instance_id", "selector", "text"],
                },
            ),
            "browser_screenshot": MCPTool(
                name="browser_screenshot",
                description="Take a screenshot",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "type": {"type": "string", "enum": ["full", "viewport", "element"], "default": "viewport"},
                        "selector": {"type": "string"},
                        "format": {"type": "string", "enum": ["png", "jpeg"], "default": "png"},
                    },
                    "required": ["instance_id"],
                },
            ),
            "browser_execute_script": MCPTool(
                name="browser_execute_script",
                description="Execute JavaScript in the browser",
                parameters={
                    "type": "object",
                    "properties": {"instance_id": {"type": "string"}, "script": {"type": "string"}, "args": {"type": "array"}},
                    "required": ["instance_id", "script"],
                },
            ),
            "browser_get_cookies": MCPTool(
                name="browser_get_cookies",
                description="Get browser cookies",
                parameters={"type": "object", "properties": {"instance_id": {"type": "string"}, "domain": {"type": "string"}}, "required": ["instance_id"]},
            ),
            "browser_set_cookies": MCPTool(
                name="browser_set_cookies",
                description="Set browser cookies",
                parameters={
                    "type": "object",
                    "properties": {"instance_id": {"type": "string"}, "cookies": {"type": "array", "items": {"type": "object"}}},
                    "required": ["instance_id", "cookies"],
                },
            ),
            "browser_wait_for_element": MCPTool(
                name="browser_wait_for_element",
                description="Wait for an element to appear",
                parameters={
                    "type": "object",
                    "properties": {"instance_id": {"type": "string"}, "selector": {"type": "string"}, "timeout": {"type": "number", "default": 30}},
                    "required": ["instance_id", "selector"],
                },
            ),
            "browser_close": MCPTool(
                name="browser_close",
                description="Close a browser instance",
                parameters={"type": "object", "properties": {"instance_id": {"type": "string"}}, "required": ["instance_id"]},
            ),
            "browser_list": MCPTool(name="browser_list", description="List active browser instances", parameters={"type": "object", "properties": {}}),
            "browser_get_tabs": MCPTool(
                name="browser_get_tabs",
                description="Get browser tabs",
                parameters={"type": "object", "properties": {"instance_id": {"type": "string"}}, "required": ["instance_id"]},
            ),
            "browser_switch_tab": MCPTool(
                name="browser_switch_tab",
                description="Switch to a different tab",
                parameters={
                    "type": "object",
                    "properties": {"instance_id": {"type": "string"}, "tab_id": {"type": "string"}},
                    "required": ["instance_id", "tab_id"],
                },
            ),
            "browser_scroll": MCPTool(
                name="browser_scroll",
                description="Scroll the page",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "element": {"type": "string"},
                        "smooth": {"type": "boolean", "default": True},
                    },
                    "required": ["instance_id"],
                },
            ),
            "browser_extract_text": MCPTool(
                name="browser_extract_text",
                description="Extract human-readable text from the current page",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "preserve_structure": {"type": "boolean", "default": True},
                        "remove_scripts": {"type": "boolean", "default": True},
                        "remove_styles": {"type": "boolean", "default": True},
                    },
                    "required": ["instance_id"],
                },
            ),
            "browser_extract_links": MCPTool(
                name="browser_extract_links",
                description="Extract all links from the current page",
                parameters={
                    "type": "object",
                    "properties": {
                        "instance_id": {"type": "string"},
                        "absolute": {"type": "boolean", "default": True},
                    },
                    "required": ["instance_id"],
                },
            ),
        }

    async def start(self):
        host = self.config.get("server_host", "localhost")
        port = self.config.get("server_port", 8765)

        logger.info(f"Starting MCP server on {host}:{port}")

        # Create a wrapper that works with the new websockets API
        async def handler_wrapper(websocket):
            logger.debug(f"Handler wrapper called for {websocket.remote_address}")
            try:
                await self.handle_client(websocket)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                raise

        # Start the server
        self.server = await websockets.serve(
            handler_wrapper,
            host,  # Use the configured host
            port,
            ping_interval=30,
            ping_timeout=10
        )

        logger.info(f"MCP server started successfully on {host}:{port}")

    async def stop(self):
        if self.server:
            logger.info("Stopping MCP server")
            self.server.close()
            await self.server.wait_closed()

            for client in self.clients.values():
                await client.close()

            self.clients.clear()
            logger.info("MCP server stopped")

    async def handle_client(self, websocket: WebSocketServerProtocol):
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket

        logger.info(f"Client {client_id} connected from {websocket.remote_address}")

        try:
            await self._send_capabilities(websocket)

            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self._handle_request(data)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError as e:
                    error_response = {"error": "Invalid JSON", "details": str(e)}
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    error_response = {"error": "Internal server error", "details": str(e)}
                    await websocket.send(json.dumps(error_response))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error with client {client_id}: {e}")
        finally:
            del self.clients[client_id]

    async def _send_capabilities(self, websocket: WebSocketServerProtocol):
        capabilities = {
            "type": "capabilities",
            "tools": [{"name": tool.name, "description": tool.description, "parameters": tool.parameters} for tool in self.tools.values()],
            "version": "1.0.0",
        }
        await websocket.send(json.dumps(capabilities))

    async def _handle_request(self, data: dict[str, Any]) -> dict[str, Any]:
        request_type = data.get("type")

        if request_type == "tool":
            return await self._handle_tool_request(data)
        if request_type == "list_tools":
            return {"type": "tools", "tools": list(self.tools.keys())}
        if request_type == "ping":
            return {"type": "pong"}
        return {"error": "Unknown request type", "type": request_type}

    async def _handle_tool_request(self, data: dict[str, Any]) -> dict[str, Any]:
        tool_name = data.get("tool")
        parameters = data.get("parameters", {})
        request_id = data.get("request_id", str(uuid.uuid4()))

        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}", "request_id": request_id}

        start_time = asyncio.get_event_loop().time()

        try:
            result = await self._execute_tool(tool_name, parameters)
            execution_time = asyncio.get_event_loop().time() - start_time

            return {"success": True, "result": result, "request_id": request_id, "execution_time": execution_time}
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            execution_time = asyncio.get_event_loop().time() - start_time

            return {"success": False, "error": str(e), "request_id": request_id, "execution_time": execution_time}

    async def _get_instance_or_error(self, instance_id: str) -> BrowserInstance:
        instance = await self.manager.get_instance(instance_id)
        if not instance:
            raise MCPError(f"Instance {instance_id} not found")
        return instance

    async def _execute_launch(self, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self.manager.get_or_create_instance(
            headless=parameters.get("headless", True), profile=parameters.get("profile"), extensions=parameters.get("extensions", [])
        )
        return {"instance_id": instance.id}

    async def _execute_navigate(self, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self._get_instance_or_error(parameters["instance_id"])
        nav = NavigationController(instance)
        wait_for = parameters.get("wait_for")
        wait_condition = WaitCondition(type=wait_for) if wait_for else None
        result = await nav.navigate(parameters["url"], wait_for=wait_condition)
        return {"url": result.url, "title": result.title, "load_time": result.load_time}

    async def _execute_screenshot(self, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self._get_instance_or_error(parameters["instance_id"])
        screenshot_ctrl = ScreenshotController(instance)
        screenshot_type = parameters.get("type", "viewport")

        if screenshot_type == "full":
            image_data = await screenshot_ctrl.capture_full_page()
        elif screenshot_type == "element":
            if not parameters.get("selector"):
                raise MCPError("Selector required for element screenshot")
            image_data = await screenshot_ctrl.capture_element(parameters["selector"])
        else:
            image_data = await screenshot_ctrl.capture_viewport()

        return {"image": base64.b64encode(image_data).decode("utf-8"), "format": parameters.get("format", "png")}

    async def _execute_input(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self._get_instance_or_error(parameters["instance_id"])
        input_ctrl = InputController(instance)

        if tool_name == "browser_click":
            options = ClickOptions(button=parameters.get("button", "left"))
            await input_ctrl.click(parameters["selector"], options=options)
        elif tool_name == "browser_type":
            await input_ctrl.type_text(parameters["selector"], parameters["text"], clear=parameters.get("clear", True))

        return {"success": True}

    async def _execute_cookies(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self._get_instance_or_error(parameters["instance_id"])

        if tool_name == "browser_get_cookies":
            domain = parameters.get("domain")
            cookies = [c for c in instance.driver.get_cookies() if c.get("domain") == domain] if domain else instance.driver.get_cookies()
            return {"cookies": cookies}
        # browser_set_cookies
        for cookie in parameters["cookies"]:
            instance.driver.add_cookie(cookie)
        return {"success": True}

    async def _execute_tabs(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        instance = await self._get_instance_or_error(parameters["instance_id"])
        if tool_name == "browser_get_tabs":
            tabs = await instance.get_tabs()
            return {"tabs": [{"id": tab.id, "title": tab.title, "url": tab.url, "active": tab.active} for tab in tabs]}
        # browser_switch_tab
        instance.driver.switch_to.window(parameters["tab_id"])
        return {"success": True}

    async def _execute_navigation(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "browser_navigate":
            return await self._execute_navigate(parameters)

        instance = await self._get_instance_or_error(parameters["instance_id"])
        nav = NavigationController(instance)

        if tool_name == "browser_scroll":
            await nav.scroll_to(x=parameters.get("x"), y=parameters.get("y"), element=parameters.get("element"), smooth=parameters.get("smooth", True))
            return {"success": True}
        if tool_name == "browser_wait_for_element":
            found = await nav.wait_for_element(parameters["selector"], timeout=parameters.get("timeout", 30))
            return {"found": found}
        if tool_name == "browser_extract_text":
            text = await nav.extract_text(
                preserve_structure=parameters.get("preserve_structure", True),
                remove_scripts=parameters.get("remove_scripts", True),
                remove_styles=parameters.get("remove_styles", True),
            )
            return {"text": text}
        if tool_name == "browser_extract_links":
            links = await nav.extract_links(absolute=parameters.get("absolute", True))
            return {"links": links}
        # browser_execute_script
        result = await nav.execute_script(parameters["script"], *parameters.get("args", []))
        return {"result": result}

    async def _execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        # Lifecycle operations
        if tool_name == "browser_launch":
            result = await self._execute_launch(parameters)
        elif tool_name == "browser_close":
            result = {"success": await self.manager.terminate_instance(parameters["instance_id"])}
        elif tool_name == "browser_list":
            instances = await self.manager.list_instances()
            result = {
                "instances": [
                    {"id": inst.id, "status": inst.status.value, "created_at": inst.created_at.isoformat(), "active_tabs": inst.active_tabs}
                    for inst in instances
                ]
            }
        # Delegate to specific handlers
        elif tool_name in [
            "browser_navigate",
            "browser_scroll",
            "browser_wait_for_element",
            "browser_execute_script",
            "browser_extract_text",
            "browser_extract_links",
        ]:
            result = await self._execute_navigation(tool_name, parameters)
        elif tool_name in ["browser_click", "browser_type"]:
            result = await self._execute_input(tool_name, parameters)
        elif tool_name == "browser_screenshot":
            result = await self._execute_screenshot(parameters)
        elif tool_name in ["browser_get_cookies", "browser_set_cookies"]:
            result = await self._execute_cookies(tool_name, parameters)
        elif tool_name in ["browser_get_tabs", "browser_switch_tab"]:
            result = await self._execute_tabs(tool_name, parameters)
        else:
            raise MCPError(f"Tool {tool_name} not implemented")

        return result

    async def broadcast_event(self, event: MCPEvent):
        event_data = {
            "type": "event",
            "event_type": event.event_type,
            "instance_id": event.instance_id,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        }

        message = json.dumps(event_data)

        if self.clients:
            await asyncio.gather(*[client.send(message) for client in self.clients.values()], return_exceptions=True)
