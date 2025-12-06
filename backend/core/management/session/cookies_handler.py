"""Cookie handling functions for session management."""

import os
from typing import Any
from urllib.parse import urlparse

from loguru import logger
from selenium.common.exceptions import TimeoutException, WebDriverException

from browser.backend.core.management.session.session_utils import is_error_page


def restore_cookies_to_tab(driver: Any, tab_url: str, parsed_url: Any, cookies: list[dict[str, Any]]) -> int:
    """Restore cookies to a single tab. Returns count of cookies restored."""
    # Navigate to domain root for cookie setting
    domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    driver.get(domain_url)

    # Check if we're on an error page
    current_url = driver.current_url
    page_source = driver.page_source.lower() if driver.page_source else ""

    if is_error_page(current_url, page_source):
        return 0

    # Try to restore cookies that match this domain
    count = 0
    for cookie in cookies:
        cookie_domain = cookie.get("domain", "")
        if cookie_domain and (
            parsed_url.netloc == cookie_domain.lstrip(".") or parsed_url.netloc.endswith(cookie_domain) or cookie_domain.lstrip(".") in parsed_url.netloc
        ):
            try:
                driver.add_cookie(cookie)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to restore cookie {cookie.get('name', 'unknown')}: {e}")

    # Navigate back to the actual tab URL
    driver.get(tab_url)
    return count


def restore_all_cookies(
    driver: Any,
    tabs: list[dict[str, str]],
    handle_mapping: dict[str, str],
    cookies: list[dict[str, Any]],
) -> int:
    """Restore cookies to all tabs. Returns total count of cookies restored."""
    total = 0
    for tab in tabs:
        tab_url = tab["url"]

        if not tab_url.startswith(("http://", "https://")):
            continue

        parsed = urlparse(tab_url)
        if not (parsed.scheme and parsed.netloc):
            continue

        tab_handle = handle_mapping.get(tab["handle"])
        if not tab_handle:
            continue

        driver.switch_to.window(tab_handle)
        count = restore_cookies_to_tab(driver, tab_url, parsed, cookies)
        total += count

    return total


def restore_all_tabs(driver: Any, tabs: list[dict[str, str]]) -> dict[str, str]:
    """Restore all tabs from session data with timeout protection.

    Returns mapping of old handles to new handles.
    Logs warnings for failed tabs but continues restoration to prevent total failure.
    """

    handle_mapping = {}
    failed_tabs = []

    # Store original timeout and set timeout for restoration
    # In testing environments, use longer timeout to handle system load
    original_timeout = 30  # Default page load timeout

    restore_timeout = 30 if os.environ.get("PYTEST_CURRENT_TEST") else 15  # 30s in tests, 15s in prod

    try:
        driver.set_page_load_timeout(restore_timeout)

        # First tab: use existing tab and navigate
        first_tab = tabs[0]
        try:
            logger.info(f"Restoring first tab: {first_tab['url']}")
            driver.get(first_tab["url"])
            first_handle = driver.current_window_handle
            handle_mapping[tabs[0]["handle"]] = first_handle
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Failed to restore first tab {first_tab['url']}: {e}")
            # Keep first tab even if navigation failed - just leave it on error page
            first_handle = driver.current_window_handle
            handle_mapping[tabs[0]["handle"]] = first_handle
            failed_tabs.append((0, first_tab["url"], str(e)))

        # Restore remaining tabs (if any)
        for idx, tab in enumerate(tabs[1:], start=1):
            try:
                logger.info(f"Restoring tab {idx}: {tab['url']}")
                driver.execute_script("window.open('');")
                new_handle = driver.window_handles[-1]
                handle_mapping[tab["handle"]] = new_handle
                driver.switch_to.window(new_handle)

                try:
                    driver.get(tab["url"])
                except (TimeoutException, WebDriverException) as e:
                    logger.warning(f"Failed to navigate tab {idx} to {tab['url']}: {e}")
                    # Tab was created but navigation failed - keep the tab
                    failed_tabs.append((idx, tab["url"], str(e)))

            except Exception as e:
                logger.error(f"Failed to create tab {idx}: {e}")
                failed_tabs.append((idx, tab["url"], str(e)))
                # Don't add to handle_mapping if tab creation failed

        if failed_tabs:
            logger.warning(f"Session restore completed with {len(failed_tabs)} failed tabs: {failed_tabs}")

    finally:
        # Restore original timeout
        driver.set_page_load_timeout(original_timeout)

    return handle_mapping
