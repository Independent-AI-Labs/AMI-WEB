"""Test the MCP browser_get_html with token limits."""

import asyncio

from loguru import logger

from chrome_manager.core.manager import ChromeManager


async def get_html_with_selector(nav, selector, max_tokens):
    """Get HTML for a specific selector with token limit."""
    max_chars = max_tokens * 4
    html = await nav.get_element_html(selector)
    token_count = len(html) // 4
    if token_count > max_tokens:
        html = html[:max_chars] + f"\n<!-- Response limited to {max_tokens} tokens. Element too large - try a more specific selector or child elements. -->"
    return html


async def test_mcp_html_limit():
    manager = ChromeManager()

    try:
        # Launch a browser
        instance = await manager.get_or_create_instance(headless=False)
        instance_id = instance.id

        # Navigate to Wikipedia (large page)
        instance.driver.get("https://en.wikipedia.org/wiki/Python_(programming_language)")
        await asyncio.sleep(2)

        print("Testing MCP browser_get_html with token limits...\n")

        # Simulate the MCP tool execution directly
        from chrome_manager.facade.navigation import NavigationController

        nav = NavigationController(instance)

        print("Executing browser_get_html logic...")

        # Test without selector - should auto-adjust depth
        print("\n" + "=" * 60)
        print("Testing without selector (should auto-adjust depth)...")

        max_tokens = 25000
        max_chars = max_tokens * 4

        # Try different depths
        html = None
        for depth in [3, 2, 1]:
            try:
                html = await nav.get_page_content(max_depth=depth, collapse_depth=depth - 1 if depth > 1 else None)
                token_count = len(html) // 4
                if token_count <= max_tokens:
                    print(f"Succeeded with depth={depth}, tokens: ~{token_count}")
                    break
                print(f"Depth {depth}: {token_count} tokens (too large)")
            except Exception as e:
                print(f"Error at depth {depth}: {e}")

        if not html or len(html) // 4 > max_tokens:
            if not html:
                html = await nav.get_page_content(max_depth=1)
            if len(html) > max_chars:
                html = html[:max_chars]
            print("FAILED to fit naturally, had to truncate")

        print(f"\nFirst 500 chars of response:\n{html[:500]}")
        print(f"\nFinal response size: {len(html)} chars (~{len(html)//4} tokens)")

        # Test with specific selector
        print("\n" + "=" * 60)
        print("Testing with specific selector (#firstHeading)...")

        html = await get_html_with_selector(nav, "#firstHeading", max_tokens)
        print(f"Element HTML: {html}")
        print(f"Token count: ~{len(html)//4}")

        # Properly terminate
        await manager.return_to_pool(instance_id)
        await manager.shutdown()

        print("\nTest completed properly!")

    except Exception as e:
        print(f"Error: {e}")
        try:
            await manager.shutdown()
        except Exception:
            logger.debug("Shutdown failed, but test already failed")


if __name__ == "__main__":
    asyncio.run(test_mcp_html_limit())
