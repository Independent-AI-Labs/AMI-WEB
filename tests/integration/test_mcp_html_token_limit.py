"""Test the MCP browser_get_html with token limits."""

import asyncio

from chrome_manager.core.manager import ChromeManager


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

        # Test the actual MCP logic
        parameters = {"instance_id": instance_id}

        print("Executing browser_get_html logic...")

        # This is the actual code from server.py
        selector = parameters.get("selector")
        max_depth = parameters.get("max_depth")
        collapse_depth = parameters.get("collapse_depth")

        # Token limit is 25000 (roughly 4 chars per token)
        max_tokens = 25000
        max_chars = max_tokens * 4  # Rough approximation

        # Try to get HTML with progressively more aggressive limits
        html = None
        tried_approaches = []

        if selector:
            # Specific element requested
            html = await nav.get_element_html(selector)
            token_count = len(html) // 4  # Rough token estimate
            if token_count > max_tokens:
                # Even the specific element is too large
                html = (
                    html[:max_chars]
                    + f"\n<!-- Response limited to {max_tokens} tokens. Element too large - try a more specific selector or child elements. -->"
                )
        else:
            # Try different depth limits to fit within token limit
            depths_to_try = []

            if collapse_depth:
                depths_to_try.append((max_depth, collapse_depth, "user-specified collapse_depth"))
            if max_depth:
                depths_to_try.append((max_depth, None, "user-specified max_depth"))

            # Auto-adjust depths if needed
            depths_to_try.extend(
                [
                    (None, 3, "collapse_depth=3"),
                    (None, 2, "collapse_depth=2"),
                    (None, 1, "collapse_depth=1"),
                    (3, None, "max_depth=3"),
                    (2, None, "max_depth=2"),
                    (1, None, "max_depth=1"),
                ]
            )

            for md, cd, description in depths_to_try:
                if md or cd:
                    html = await nav.get_html_with_depth_limit(md, cd)
                else:
                    html = await nav.get_page_content()

                token_count = len(html) // 4
                tried_approaches.append(f"{description}: ~{token_count} tokens")

                if token_count <= max_tokens:
                    if len(tried_approaches) > 1:
                        html = f"<!-- Auto-adjusted to {description} to fit within {max_tokens} token limit -->\n" + html
                    print(f"SUCCESS: Auto-adjusted to {description}")
                    print(f"  Final token count: ~{token_count} (within {max_tokens} limit)")
                    break
            else:
                # Nothing worked, return most collapsed version with message
                html = await nav.get_html_with_depth_limit(max_depth=1, collapse_depth=1)
                token_count = len(html) // 4
                if token_count > max_tokens:
                    html = html[:max_chars]
                html = (
                    f"<!-- WARNING: Response limited to {max_tokens} tokens. Page too large even at minimum depth. \n"
                    f"Tried approaches: {', '.join(tried_approaches)}\n"
                    f"Please use a specific selector to target the content you need. -->\n" + html
                )
                print("FAILED to fit naturally, had to truncate")

        result = {"html": html}

        print(f"\nTried approaches: {', '.join(tried_approaches)}")
        print(f"\nFirst 500 chars of response:\n{html[:500]}")
        print(f"\nFinal response size: {len(html)} chars (~{len(html)//4} tokens)")

        # Test with specific selector
        print("\n" + "=" * 60)
        print("Testing with specific selector (#firstHeading)...")

        parameters = {"instance_id": instance_id, "selector": "#firstHeading"}
        selector = parameters.get("selector")

        html = await nav.get_element_html(selector)
        token_count = len(html) // 4
        print(f"Element HTML: {html}")
        print(f"Token count: ~{token_count}")

        # Properly terminate
        await manager.return_to_pool(instance_id)
        await manager.shutdown()

        print("\nTest completed properly!")

    except Exception as e:
        print(f"Error: {e}")
        try:
            await manager.shutdown()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_mcp_html_limit())
