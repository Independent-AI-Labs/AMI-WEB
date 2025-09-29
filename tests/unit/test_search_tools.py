"""Unit tests for the web search MCP tool."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import cast

import pytest
from aiohttp import web

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.search_tools import browser_web_search_tool
from browser.backend.utils.config import Config


async def _start_test_server(
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]] | web.Application,
) -> tuple[web.AppRunner, int]:
    """Start an aiohttp test server and return the runner and bound port."""
    if isinstance(handler, web.Application):
        app = handler
    else:
        app = web.Application()
        app.router.add_get("/search", handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    sockets = getattr(getattr(site, "_server", None), "sockets", None)
    if not sockets:
        raise RuntimeError("Failed to start test server")
    port = int(sockets[0].getsockname()[1])
    return runner, port


@pytest.mark.asyncio
async def test_browser_web_search_tool_primary_success() -> None:
    async def searx_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "results": [
                    {"title": "<b>Example Result</b>", "url": "https://example.com", "content": "Snippet <i>content</i>"},
                    {"title": "Ignore Without URL"},
                ],
            },
        )

    runner, port = await _start_test_server(searx_handler)
    config = Config(
        {
            "backend": {
                "tools": {
                    "web_search": {
                        "primary_url": f"http://127.0.0.1:{port}/search?q={{query}}&format=json",
                        "fallback_url": None,
                        "timeout_seconds": 2,
                        "max_results": 3,
                    },
                },
            },
        },
    )
    manager = cast(ChromeManager, SimpleNamespace(config=config))

    try:
        response = await browser_web_search_tool(manager, "test query")
    finally:
        await runner.cleanup()

    assert response.success is True
    assert response.data == {"provider": "primary", "query": "test query", "request_url": f"http://127.0.0.1:{port}/search?q=test+query&format=json"}
    assert isinstance(response.result, dict)
    results = response.result.get("results")
    assert isinstance(results, list)
    assert results[0]["url"] == "https://example.com"
    assert response.text is not None and "Snippet" in response.text


@pytest.mark.asyncio
async def test_browser_web_search_tool_fallback_on_failure() -> None:
    async def fallback_handler(request: web.Request) -> web.Response:
        html_body = """
        <html>
            <body>
                <div class="result">
                    <a href="https://fallback.example.com">Fallback Title</a>
                    <p>Fallback snippet text</p>
                </div>
            </body>
        </html>
        """
        return web.Response(text=html_body, content_type="text/html")

    runner, port = await _start_test_server(fallback_handler)
    config = Config(
        {
            "backend": {
                "tools": {
                    "web_search": {
                        "primary_url": "http://127.0.0.1:9/search?q={query}&format=json",
                        "fallback_url": f"http://127.0.0.1:{port}/search?q={{query}}",
                        "timeout_seconds": 1,
                        "max_results": 2,
                    },
                },
            },
        },
    )
    manager = cast(ChromeManager, SimpleNamespace(config=config))

    try:
        response = await browser_web_search_tool(manager, "fallback query")
    finally:
        await runner.cleanup()

    assert response.success is True
    assert response.data is not None and response.data["provider"] == "fallback"
    assert isinstance(response.result, dict)
    results = response.result["results"]
    assert results[0]["title"] == "Fallback Title"
    assert results[0]["url"] == "https://fallback.example.com"


@pytest.mark.asyncio
async def test_browser_web_search_tool_empty_query_rejected() -> None:
    manager = cast(ChromeManager, SimpleNamespace(config=Config({})))
    response = await browser_web_search_tool(manager, "   ")
    assert response.success is False
    assert "empty" in (response.error or "").lower()


@pytest.mark.asyncio
async def test_browser_web_search_tool_all_providers_fail() -> None:
    config = Config(
        {
            "backend": {
                "tools": {
                    "web_search": {
                        "primary_url": "http://127.0.0.1:9/search?q={query}&format=json",
                        "fallback_url": "http://127.0.0.1:10/search?q={query}",
                        "timeout_seconds": 0.5,
                        "max_results": 1,
                    },
                },
            },
        },
    )
    manager = cast(ChromeManager, SimpleNamespace(config=config))

    response = await browser_web_search_tool(manager, "unreachable search", timeout=0.2)

    assert response.success is False
    assert response.error is not None
    assert "web search failed" in response.error.lower()
