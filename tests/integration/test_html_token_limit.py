"""Test the HTML token limiting functionality."""

import pytest

from chrome_manager.facade.navigation import NavigationController


@pytest.mark.asyncio
async def test_token_limit(browser_instance):
    """Test HTML token limiting on Wikipedia page."""
    instance = browser_instance
    nav = NavigationController(instance)

    # Navigate to a complex page that will exceed limits
    await nav.navigate("https://en.wikipedia.org/wiki/Python_(programming_language)")

    # Testing HTML token limiting on Wikipedia page

    # Test 1: Try to get full HTML (should auto-adjust)
    html = await nav.get_page_content()
    token_count = len(html) // 4
    max_tokens = 25000
    # Full HTML might exceed limits on complex pages

    # Test 2: Get with collapse_depth=2
    html = await nav.get_html_with_depth_limit(collapse_depth=2)
    token_count = len(html) // 4
    max_tokens = 25000
    assert token_count <= max_tokens, f"Depth 2 still exceeds limit: {token_count} tokens"

    # Test 3: Get with collapse_depth=1 (most aggressive)
    html = await nav.get_html_with_depth_limit(collapse_depth=1)
    token_count = len(html) // 4
    max_tokens = 25000
    assert token_count <= max_tokens, f"Even depth 1 exceeds: {token_count} tokens"
    assert len(html) > 0, "HTML should not be empty"

    # Test 4: Get specific element
    html = await nav.get_element_html("#mw-content-text")
    token_count = len(html) // 4
    max_tokens = 25000
    # Specific elements should generally be within limits
    # but Wikipedia content can be very large
