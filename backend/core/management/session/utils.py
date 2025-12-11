"""Session management utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger


if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


def is_real_page(url: str) -> bool:
    """Check if URL represents a real page vs internal browser page."""
    if not url or url == "about:blank":
        return False
    if url.startswith(("chrome://", "chrome-extension://")):
        return False
    if url.startswith("data:"):
        return False
    # Check for internal browser URLs
    internal_indicators = ["chrome://", "view-source:", "about:", "blob:"]
    return not any(indicator in url for indicator in internal_indicators)


def collect_tab_cookies(driver: WebDriver, tab_url: str, all_cookies: list[dict[str, Any]]) -> None:
    """Collect cookies for a specific tab."""
    try:
        driver.get(tab_url)
        for cookie in all_cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                # Log and skip cookies that cannot be added to this domain
                logger.debug(f"Could not add cookie: {e}")
                continue
    except Exception as e:
        # Tab may be inaccessible, skip cookie collection
        logger.debug(f"Could not collect cookies for tab: {e}")


def determine_active_tab(tabs: list[dict[str, str]], current_handle: str | None) -> str | None:
    """Determine which tab was likely the active one."""
    if current_handle and current_handle in [tab["handle"] for tab in tabs]:
        return current_handle
    # If we can't determine, take the first one as default
    if tabs:
        return tabs[0]["handle"]
    return None


def get_active_tab_data(tabs: list[dict[str, str]], actual_active_tab: str | None) -> dict[str, str] | None:
    """Get the data for the active tab."""
    if actual_active_tab:
        for tab in tabs:
            if tab["handle"] == actual_active_tab:
                return tab
    # If no specific active tab identified, return first tab
    return tabs[0] if tabs else None


def is_error_page(current_url: str, page_source: str) -> bool:
    """Check if the current page is an error page."""
    error_indicators = [
        "error",
        "not found",
        "404",
        "403",
        "500",
        "connection refused",
        "connection timed out",
        "<title>error</title>",
    ]
    lower_source = page_source.lower()
    lower_url = current_url.lower()

    return any(indicator in lower_source or indicator in lower_url for indicator in error_indicators)


def restore_cookies_to_tab(driver: WebDriver, tab_url: str, parsed_url: Any, cookies: list[dict[str, Any]]) -> int:
    """Restore cookies to a specific tab, returning number of cookies restored."""
    restored_count = 0

    try:
        # Verify tab_url matches parsed_url
        if tab_url != parsed_url.geturl() if hasattr(parsed_url, "geturl") else str(parsed_url):
            logger.debug(f"Mismatch between tab_url and parsed_url: {tab_url} vs {parsed_url}")

        # Check if cookie domain matches current tab
        current_domain = parsed_url.netloc
        applicable_cookies = []

        for cookie in cookies:
            cookie_domain = cookie.get("domain", "")
            # Cookie is applicable if domain matches or cookie has no specific domain
            if not cookie_domain or current_domain.endswith(cookie_domain.lstrip(".")):
                applicable_cookies.append(cookie)

        for cookie in applicable_cookies:
            try:
                driver.add_cookie(cookie)
                restored_count += 1
            except Exception as e:
                # Log and continue with other cookies
                logger.debug(f"Could not add cookie: {e}")
                continue
    except Exception as e:
        # Log the exception but return the count of cookies added so far
        logger.warning(f"Error while restoring cookies: {e}")

    return restored_count
