"""Utility functions for session management."""

from typing import Any
from urllib.parse import urlparse


def is_real_page(url: str) -> bool:
    """Check if URL is a real page (not chrome:// or about:blank)."""
    return not ("chrome://" in url or "about:blank" in url or url == "data:,")


def is_error_page(current_url: str, page_source: str) -> bool:
    """Check if we're on an error page."""
    return (
        "data:text/html,chromewebdata" in current_url
        or "chrome-error:" in current_url
        or "net::err_cert" in page_source
        or "your connection is not private" in page_source
    )


def validate_url_for_cookies(url: str) -> tuple[bool, Any]:
    """Validate URL and return if it's valid for cookie operations."""
    if not url.startswith(("http://", "https://")):
        return False, None

    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        return False, None

    return True, parsed
