"""Transport implementations for MCP servers."""

import asyncio
import json
import sys
from abc import ABC, abstractmethod

import websockets
from loguru import logger


class Transport(ABC):
    """Base transport interface."""

    @abstractmethod
    async def send(self, message: dict) -> None:
        """Send a message."""

    @abstractmethod
    async def receive(self) -> dict | None:
        """Receive a message."""

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""


class StdioTransport(Transport):
    """Stdio transport for MCP servers."""

    def __init__(self):
        """Initialize stdio transport."""
        self._closed = False

    async def send(self, message: dict) -> None:
        """Send a JSON-RPC message to stdout."""
        if not self._closed:
            try:
                json_str = json.dumps(message)
                print(json_str, flush=True)
                logger.debug(f"Sent via stdio: {json_str[:200]}")
            except Exception as e:
                logger.error(f"Error sending message: {e}")

    async def receive(self) -> dict | None:
        """Read a JSON-RPC message from stdin."""
        if self._closed:
            return None

        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                return None

            message = json.loads(line.strip())
            logger.debug(f"Received via stdio: {json.dumps(message)[:200]}")
            return message
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None

    async def close(self) -> None:
        """Close the transport."""
        self._closed = True


class WebSocketTransport(Transport):
    """WebSocket transport for MCP servers."""

    def __init__(self, websocket):
        """Initialize WebSocket transport.

        Args:
            websocket: WebSocket connection
        """
        self.websocket = websocket
        self._closed = False

    async def send(self, message: dict) -> None:
        """Send a JSON-RPC message via WebSocket."""
        if not self._closed:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"Sent via WebSocket: {json.dumps(message)[:200]}")
            except websockets.ConnectionClosed:
                self._closed = True
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error sending message: {e}")

    async def receive(self) -> dict | None:
        """Receive a JSON-RPC message via WebSocket."""
        if self._closed:
            return None

        try:
            message = await self.websocket.recv()
            data = json.loads(message)
            logger.debug(f"Received via WebSocket: {json.dumps(data)[:200]}")
            return data
        except websockets.ConnectionClosed:
            self._closed = True
            logger.info("WebSocket connection closed")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            # Return a special marker for parse errors
            return {"__parse_error__": str(e)}
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if not self._closed:
            self._closed = True
            await self.websocket.close()
