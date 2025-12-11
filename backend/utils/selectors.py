"""Selector parsing utilities."""

import logging


logger = logging.getLogger(__name__)


def parse_selector(selector: str) -> tuple[str, str]:
    """Parse selector string to Selenium By locator.

    Supports:
    - CSS selectors (default)
    - XPath (starts with // or /)
    - ID (starts with #)
    - Class name (starts with .)
    - Name attribute (starts with @)
    - Tag name (simple word)

    Args:
        selector: Selector string

    Returns:
        Tuple of (By type as string, selector value)

    Examples:
        >>> parse_selector("#my-id")
        ("id", "my-id")
        >>> parse_selector(".my-class")
        ("class name", "my-class")
        >>> parse_selector("//div[@id='test']")
        ("xpath", "//div[@id='test']")
        >>> parse_selector("div.content > p")
        ("css selector", "div.content > p")
    """
    selector = selector.strip()

    # XPath
    if selector.startswith(("//", "/")):
        return "xpath", selector

    # ID shorthand
    if selector.startswith("#") and " " not in selector and "," not in selector:
        return "id", selector[1:]

    # Class name shorthand
    if selector.startswith(".") and " " not in selector and "," not in selector:
        return "class name", selector[1:]

    # Name attribute
    if selector.startswith("@"):
        return "name", selector[1:]

    # Simple tag name (no special chars)
    if selector.isalpha():
        return "tag name", selector

    # Default to CSS selector
    return "css selector", selector


def is_valid_selector(selector: str) -> bool:
    """Check if a selector string is valid.

    Args:
        selector: Selector string to validate

    Returns:
        True if valid, False otherwise
    """
    if not selector or not selector.strip():
        return False

    try:
        parse_selector(selector)
        return True
    except (ValueError, SyntaxError) as e:
        logger.debug(f"Invalid selector '{selector}': {e}")
        return False
