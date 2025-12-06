"""Tab management functionality for session handling."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


def restore_all_tabs(driver: WebDriver, tabs: list[dict[str, str]]) -> dict[str, str]:
    """Restore all tabs from session data."""
    restored_tabs = {}

    # Close all current tabs except the initial one
    current_handles = driver.window_handles
    for handle in current_handles[1:]:  # Keep first tab
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception as e:
            # Log the exception but continue with other tabs
            logger.debug(f"Could not close tab {handle}: {e}")
            continue

    # Switch back to the first tab
    if current_handles:
        with contextlib.suppress(Exception):
            driver.switch_to.window(current_handles[0])

    # Restore each tab from session
    for i, tab_data in enumerate(tabs):
        url = tab_data.get("url", "about:blank")

        if i == 0:
            # Use the existing first tab
            try:
                driver.get(url)
                restored_tabs[driver.current_window_handle] = url
            except Exception as e:
                # Log the exception but continue with other operations
                logger.debug(f"Could not restore first tab to URL {url}: {e}")
                continue
        else:
            # Open new tab (this works in most modern browsers)
            try:
                driver.execute_script("window.open('');")
                # Switch to the new tab
                all_handles = driver.window_handles
                if len(all_handles) > i:
                    new_handle = all_handles[i]
                    driver.switch_to.window(new_handle)
                    driver.get(url)
                    restored_tabs[new_handle] = url
            except Exception as e:
                # Log the exception but continue with other tabs
                logger.debug(f"Could not open new tab for URL {url}: {e}")
                continue

    return restored_tabs


def restore_all_cookies(
    driver: WebDriver,
    url_cookies_mapping: dict[str, list[dict[str, Any]]],
    active_tab_handle: str | None = None,
) -> dict[str, int]:
    """Restore all cookies organized by URL."""
    restore_stats = {}

    try:
        # If we know the active tab, prioritize it
        restore_stats.update(_restore_cookies_for_active_tab(driver, active_tab_handle, url_cookies_mapping))

        # Restore cookies for other tabs
        restore_stats.update(_restore_cookies_for_other_tabs(driver, url_cookies_mapping))

    except Exception as e:
        # Log the exception but return empty stats
        logger.warning(f"Could not restore cookies: {e}")
        return restore_stats

    return restore_stats


def _restore_cookies_for_active_tab(driver: WebDriver, active_tab_handle: str | None, url_cookies_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Restore cookies for the active tab."""
    restore_stats = {}

    if active_tab_handle:
        try:
            driver.switch_to.window(active_tab_handle)
            current_url = driver.current_url
            if current_url in url_cookies_mapping:
                cookies = url_cookies_mapping[current_url]
                _add_cookies_to_driver(driver, cookies, current_url)
                restore_stats[current_url] = len(cookies)
        except Exception as e:
            logger.debug(f"Could not restore cookies for active tab: {e}")

    return restore_stats


def _restore_cookies_for_other_tabs(driver: WebDriver, url_cookies_mapping: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Restore cookies for tabs other than the current one."""
    restore_stats = {}

    for url, cookies in url_cookies_mapping.items():
        if url != driver.current_url:  # Skip the one we just handled
            try:
                driver.get(url)
                _add_cookies_to_driver(driver, cookies, url)
                restore_stats[url] = len(cookies)
            except Exception as e:
                # Log the exception but continue with other URLs
                logger.debug(f"Could not restore cookies for {url}: {e}")
                continue

    return restore_stats


def _add_cookies_to_driver(driver: WebDriver, cookies: list[dict[str, Any]], url: str) -> None:
    """Add cookies to the current driver."""
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            # Log the exception but continue with other cookies
            logger.debug(f"Could not add cookie to {url}: {e}")
            continue
