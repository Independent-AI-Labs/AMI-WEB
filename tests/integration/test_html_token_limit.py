"""Test the HTML token limiting functionality."""

import asyncio

from chrome_manager.core.instance import BrowserInstance
from chrome_manager.facade.navigation import NavigationController
from chrome_manager.utils.config import Config


async def test_token_limit():
    config = Config()
    instance = BrowserInstance(config=config)

    try:
        # Launch browser
        await instance.launch(headless=False)
        nav = NavigationController(instance)

        # Navigate to a complex page that will exceed limits
        await nav.navigate("https://en.wikipedia.org/wiki/Python_(programming_language)")

        print("Testing HTML token limiting on Wikipedia page...\n")

        # Test 1: Try to get full HTML (should auto-adjust)
        print("Test 1: Getting full page (should auto-adjust depth)...")
        html = await nav.get_page_content()
        token_count = len(html) // 4
        print(f"Full HTML tokens: ~{token_count}")
        max_tokens = 25000
        if token_count > max_tokens:
            print("FAIL: Full HTML exceeds 25000 tokens!")
        else:
            print("Hmm, page might be small enough already")

        # Test 2: Get with collapse_depth=2
        print("\nTest 2: Testing collapse_depth=2...")
        html = await nav.get_html_with_depth_limit(collapse_depth=2)
        token_count = len(html) // 4
        print(f"Collapsed depth 2 tokens: ~{token_count}")
        max_tokens = 25000
        if token_count > max_tokens:
            print(f"FAIL: Still exceeds limit at {token_count} tokens")
        else:
            print(f"PASS: Within limit at {token_count} tokens")

        # Test 3: Get with collapse_depth=1 (most aggressive)
        print("\nTest 3: Testing collapse_depth=1...")
        html = await nav.get_html_with_depth_limit(collapse_depth=1)
        token_count = len(html) // 4
        print(f"Collapsed depth 1 tokens: ~{token_count}")
        max_tokens = 25000
        if token_count > max_tokens:
            print(f"FAIL: Even depth 1 exceeds at {token_count} tokens")
        else:
            print(f"PASS: Within limit at {token_count} tokens")
        print(f"Sample (first 500 chars):\n{html[:500]}")

        # Test 4: Get specific element
        print("\nTest 4: Getting specific element (#mw-content-text)...")
        try:
            html = await nav.get_element_html("#mw-content-text")
            token_count = len(html) // 4
            print(f"Content element tokens: ~{token_count}")
            max_tokens = 25000
            if token_count > max_tokens:
                print("WARNING: Even specific element exceeds limit!")
            else:
                print("Element within limit")
        except Exception as e:
            print(f"Error: {e}")

    finally:
        await instance.terminate()
        print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_token_limit())
