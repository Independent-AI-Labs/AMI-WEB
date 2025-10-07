"""Integration tests for the web_search MCP tool."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from aiohttp import web

from browser.backend.mcp.chrome.chrome_server import ChromeFastMCPServer


async def _start_test_server(
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> tuple[web.AppRunner, int]:
    app = web.Application()
    app.router.add_get("/search", handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = getattr(getattr(site, "_server", None), "sockets", None)
    if not sockets:
        raise RuntimeError("Failed to get bound port for test server")
    port = int(sockets[0].getsockname()[1])
    return runner, port


@pytest.mark.asyncio
async def test_web_search_tool_via_fastmcp() -> None:
    async def searx_handler(_request: web.Request) -> web.Response:
        return web.json_response(
            {
                "results": [
                    {
                        "title": "Integration Result",
                        "url": "https://integration.example",
                        "content": "Integration snippet",
                    },
                ],
            },
        )

    runner, port = await _start_test_server(searx_handler)

    server = ChromeFastMCPServer()

    try:
        raw_content, raw_response = await server.mcp.call_tool(
            "web_search",
            arguments={
                "query": "integration query",
                "search_engine_url": f"http://127.0.0.1:{port}/search?q={{query}}&format=json",
                "max_results": 1,
            },
        )
    finally:
        await runner.cleanup()

    content = cast(list[Any], raw_content)
    response = cast(dict[str, Any], raw_response)

    assert response["success"] is True
    assert response["data"]["provider"] == "primary"
    assert response["result"]["results"][0]["url"] == "https://integration.example"
    assert any("Integration Result" in item.text for item in content)
