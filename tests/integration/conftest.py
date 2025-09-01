"""Shared fixtures for browser integration tests."""

import asyncio
import os
from pathlib import Path

from browser.backend.core.management.manager import ChromeManager
from loguru import logger

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"


class MCPTestServer:
    """Test MCP server that runs properly for testing."""

    def __init__(self, port=8766):
        self.port = port
        self.server = None
        self.manager = None
        self._server_task = None

    async def start(self):
        """Start the server asynchronously."""
        # Import here to avoid import issues

        # Use config.yaml if it exists, otherwise config.test.yaml, otherwise defaults
        config_file = "config.test.yaml"
        if Path("config.yaml").exists():
            config_file = "config.yaml"
        elif not Path("config.test.yaml").exists():
            # Will use defaults if neither exists
            config_file = None

        self.manager = ChromeManager(config_file=config_file)
        # Override pool settings for efficient test reuse
        self.manager.pool.min_instances = 2  # Keep 2 instances ready
        self.manager.pool.warm_instances = 2  # Keep 2 warm for reuse
        self.manager.pool.max_instances = 5  # Allow more for concurrent tests
        await self.manager.start()

        # TODO: Update this to use ChromeFastMCPServer when websocket support is added
        # For now, we'll skip the server initialization
        logger.warning("MCPTestServer needs update for FastMCP - server not started")

        logger.info(f"Test MCP server started on port {self.port}")

        # Give the server time to fully initialize
        await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the server."""
        if self.server:
            await self.server.stop()
        if self.manager:
            # Force shutdown of all browser instances and pool
            await self.manager.shutdown()
