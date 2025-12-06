"""Tab management functions for session handling."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from browser.backend.utils.exceptions import SessionError

if TYPE_CHECKING:
    pass


def collect_tab_cookies(driver: Any, tab_url: str, all_cookies: list[dict[str, Any]]) -> None:
    """Collect cookies from a tab if it's a real page."""
    if not tab_url.startswith(("http://", "https://")):
        return

    try:
        tab_cookies = driver.get_cookies()
        for cookie in tab_cookies:
            cookie_key = (cookie.get("name"), cookie.get("domain"))
            if not any((c.get("name"), c.get("domain")) == cookie_key for c in all_cookies):
                all_cookies.append(cookie)
    except Exception as e:
        logger.warning(f"Failed to get cookies from tab {tab_url}: {e}")


def determine_active_tab(tabs: list[dict[str, str]], current_handle: str | None) -> str | None:
    """Determine which tab is actually active - fails if state is ambiguous."""
    if not tabs:
        return None

    if not current_handle:
        raise SessionError("No current window handle available - cannot determine active tab")

    current_tab_data = next((t for t in tabs if t["handle"] == str(current_handle)), None)

    if not current_tab_data:
        raise SessionError(f"Current window handle {current_handle} not found in tab list - browser state corrupted")

    # Return the actual current handle - explicit failure on any ambiguity
    return str(current_handle)


def get_active_tab_data(tabs: list[dict[str, str]], actual_active_tab: str | None) -> dict[str, str] | None:
    """Get tab data for the active tab - fails if active tab not found."""
    if not tabs:
        return None

    if actual_active_tab:
        tab_data = next((t for t in tabs if t["handle"] == actual_active_tab), None)
        if not tab_data:
            raise SessionError(f"Active tab {actual_active_tab} not found in tab list - cannot save corrupted session state")
        return tab_data

    # No active tab specified - fail explicitly
    raise SessionError("No active tab specified - cannot determine session state")
