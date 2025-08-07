"""Threaded HTML test server to avoid event loop blocking."""

import asyncio
import logging
import threading
import time
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)


class ThreadedHTMLServer:
    """HTML server that runs in its own thread to avoid blocking."""

    def __init__(self, port: int = 8889):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.thread = None
        self.loop = None
        self.runner = None
        self.site = None
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.base_path = Path(__file__).parent / "html"

    def _run_server(self):
        """Run server in thread with its own event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._start_server())
            self.ready.set()

            # Keep running until stop is requested
            while not self.stop_event.is_set():
                self.loop.run_until_complete(asyncio.sleep(0.1))

        except Exception as e:
            logger.error(f"Server error: {e}")
            self.ready.set()  # Signal ready even on error
        finally:
            self.loop.run_until_complete(self._stop_server())
            self.loop.close()

    async def _start_server(self):
        """Start the aiohttp server."""
        app = web.Application()

        # Add static file serving
        app.router.add_static("/", self.base_path, show_index=True)

        # Add API endpoints
        app.router.add_post("/login", self._handle_login)
        app.router.add_get("/api/data", self._handle_api_data)
        app.router.add_post("/api/submit", self._handle_submit)

        # Start server
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        # Use 127.0.0.1 to avoid localhost issues
        self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
        await self.site.start()

        logger.info(f"Threaded test server started on {self.base_url}")

    async def _stop_server(self):
        """Stop the aiohttp server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Threaded test server stopped")

    def start(self):
        """Start the server in a thread."""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        # Wait for server to be ready
        if not self.ready.wait(timeout=5):
            raise RuntimeError("Server failed to start in 5 seconds")

        # Give it a moment to fully initialize
        time.sleep(0.1)
        return self.base_url

    def stop(self):
        """Stop the server thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                logger.warning("Server thread did not stop gracefully")
        # Force cleanup the event loop if it exists
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.stop()
                self.loop.close()
            except Exception as e:
                logger.error(f"Error closing loop: {e}")
        logger.info("Server thread stopped")

    async def _handle_login(self, request):
        """Handle login POST requests."""
        data = await request.post()
        username = data.get("username")
        password = data.get("password")

        if username == "testuser" and password == "password123":
            return web.json_response({"success": True, "message": "Login successful", "token": "test-token-123"})
        return web.json_response({"success": False, "message": "Invalid credentials"}, status=401)

    async def _handle_api_data(self, request):
        """Handle API data requests."""
        await asyncio.sleep(0.1)  # Simulate delay

        return web.json_response(
            {
                "data": [{"id": 1, "name": "Item 1", "value": 100}, {"id": 2, "name": "Item 2", "value": 200}, {"id": 3, "name": "Item 3", "value": 300}],
                "timestamp": time.time(),
            }
        )

    async def _handle_submit(self, request):
        """Handle form submissions."""
        data = await request.json()

        return web.json_response({"success": True, "received": data, "processed_at": time.time()})
