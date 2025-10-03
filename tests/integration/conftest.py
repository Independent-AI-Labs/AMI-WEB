"""Shared fixtures for browser integration tests."""

import asyncio
import os
from pathlib import Path

from loguru import logger

from browser.backend.core.management.manager import ChromeManager

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"


class MCPTestServer:
    """Test MCP server that runs properly for testing."""

    def __init__(self, port: int = 8766) -> None:
        self.port = port
        self.server: object | None = None
        self.manager: ChromeManager | None = None
        self._server_task = None

    async def start(self) -> None:
        """Start the server asynchronously."""
        # Import here to avoid import issues

        # Use config.yaml if it exists, otherwise config.test.yaml, otherwise defaults
        config_file: str | None = "config.test.yaml"
        if Path("config.yaml").exists():
            config_file = "config.yaml"
        elif not Path("config.test.yaml").exists():
            # Will use defaults if neither exists
            config_file = None

        self.manager = ChromeManager(config_file=config_file)
        await self.manager.initialize()

        # TODO: Update this to use ChromeFastMCPServer when websocket support is added
        # For now, we'll skip the server initialization
        logger.warning("MCPTestServer needs update for FastMCP - server not started")

        logger.info(f"Test MCP server started on port {self.port}")

        # Give the server time to fully initialize
        await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the server."""
        # No server started currently
        if self.manager is not None:
            # Force shutdown of all browser instances and pool
            await self.manager.shutdown()
