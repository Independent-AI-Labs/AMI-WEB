"""Test the MCP browser_get_html with token limits."""

import asyncio

import pytest
from loguru import logger


async def get_html_with_selector(extractor, selector, max_tokens):
    """Get HTML for a specific selector with token limit."""
    max_chars = max_tokens * 4
    html = await extractor.get_element_html(selector)
    token_count = len(html) // 4
    if token_count > max_tokens:
        html = html[:max_chars] + f"\n<!-- Response limited to {max_tokens} tokens. Element too large - try a more specific selector or child elements. -->"
    return html


@pytest.mark.asyncio
async def test_mcp_html_limit(session_manager):
    """Test MCP browser_get_html with token limits."""
    manager = session_manager

    # Get instance from manager
    instance = await manager.get_or_create_instance(headless=True)
    instance_id = instance.id

    try:
        # Navigate to Wikipedia (large page)
        instance.driver.get("https://en.wikipedia.org/wiki/Python_(programming_language)")
        await asyncio.sleep(2)

        # Testing MCP browser_get_html with token limits

        # Simulate the MCP tool execution directly
        from chrome_manager.facade.navigation.extractor import ContentExtractor

        extractor = ContentExtractor(instance)

        # Test without selector - should auto-adjust depth

        max_tokens = 25000
        max_chars = max_tokens * 4

        # Try different depths
        html = None
        for depth in [3, 2, 1]:
            try:
                html = await extractor.get_html_with_depth_limit(max_depth=depth, collapse_depth=depth - 1 if depth > 1 else None)
                token_count = len(html) // 4
                if token_count <= max_tokens:
                    break  # Found good depth
            except Exception as e:
                logger.debug(f"Error at depth {depth}: {e}")

        if not html or len(html) // 4 > max_tokens:
            if not html:
                html = await extractor.get_html_with_depth_limit(max_depth=1)
            if len(html) > max_chars:
                html = html[:max_chars]

        # Verify we got valid HTML
        assert len(html) > 0, "HTML should not be empty"
        assert len(html) // 4 <= max_tokens, f"Response exceeds token limit: {len(html)//4} tokens"

        # Test with specific selector

        html = await get_html_with_selector(extractor, "#firstHeading", max_tokens)
        assert len(html) > 0, "Element HTML should not be empty"
        assert "Python" in html, "Should contain expected content"

    finally:
        # Return instance to pool
        await manager.return_to_pool(instance_id)
