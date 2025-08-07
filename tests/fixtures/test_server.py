"""Simple HTTP server for serving test HTML files."""

import asyncio
import logging
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)


class HTMLTestServer:
    """HTTP server for serving test HTML files."""

    def __init__(self, port: int = 8888):
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.base_path = Path(__file__).parent / "html"

    async def start(self):
        """Start the test server."""
        # Add routes
        self.app.router.add_static("/", self.base_path, show_index=True)

        # Add API endpoints for testing
        self.app.router.add_post("/login", self.handle_login)
        self.app.router.add_get("/api/data", self.handle_api_data)
        self.app.router.add_post("/api/submit", self.handle_submit)

        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        # Use 127.0.0.1 instead of localhost to avoid threading issues
        self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
        await self.site.start()

        logger.info(f"Test server started on http://127.0.0.1:{self.port}")
        return f"http://127.0.0.1:{self.port}"

    async def stop(self):
        """Stop the test server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Test server stopped")

    async def handle_login(self, request):
        """Handle login POST requests."""
        data = await request.post()
        username = data.get("username")
        password = data.get("password")

        # Simulate authentication
        test_password = "password123"  # noqa: S105
        if username == "testuser" and password == test_password:
            return web.json_response({"success": True, "message": "Login successful", "token": "test-token-123"})
        return web.json_response({"success": False, "message": "Invalid credentials"}, status=401)

    async def handle_api_data(self, request):  # noqa: ARG002
        """Handle API data requests."""
        # Simulate delayed response
        await asyncio.sleep(0.5)

        return web.json_response(
            {
                "data": [{"id": 1, "name": "Item 1", "value": 100}, {"id": 2, "name": "Item 2", "value": 200}, {"id": 3, "name": "Item 3", "value": 300}],
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    async def handle_submit(self, request):
        """Handle form submissions."""
        data = await request.json()

        return web.json_response({"success": True, "received": data, "processed_at": asyncio.get_event_loop().time()})


async def run_server():
    """Run the server standalone."""
    server = HTMLTestServer()
    url = await server.start()
    print(f"Server running at {url}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(run_server())
