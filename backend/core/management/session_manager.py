"""Browser session management for saving and restoring browser state."""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from loguru import logger

from browser.backend.core.browser.instance import BrowserInstance
from browser.backend.utils.exceptions import SessionError

if TYPE_CHECKING:
    from .manager import ChromeManager


class SessionManager:
    """Manages browser sessions for save and restore functionality."""

    def __init__(self, session_dir: str = "./data/sessions"):
        self.session_dir = Path(session_dir)
        # Don't create directory in __init__, create it when actually needed
        self.metadata_file = self.session_dir / "sessions.json"
        self.sessions: dict[str, dict[str, Any]] = {}

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """Load session metadata."""
        logger.debug(f"Current working directory: {Path.cwd()}")
        logger.debug(f"Absolute metadata file path: {self.metadata_file.absolute()}")
        logger.debug(f"Checking if metadata file exists: {self.metadata_file}")
        if self.metadata_file.exists():
            logger.debug(f"Loading metadata from {self.metadata_file}")
            file_size = self.metadata_file.stat().st_size
            logger.debug(f"File size: {file_size} bytes")
            with self.metadata_file.open() as f:
                content = f.read()
                logger.debug(f"File content: {repr(content)}")
                logger.debug("Parsing JSON...")
                data: dict[str, dict[str, Any]] = json.loads(content)
                logger.debug(f"Loaded {len(data)} sessions")
                return data
        logger.debug("No metadata file found, returning empty dict")
        return {}

    def _save_metadata(self) -> None:
        """Save session metadata."""
        with self.metadata_file.open("w") as f:
            json.dump(self.sessions, f, indent=2, default=str)

    async def initialize(self) -> None:
        """Initialize session manager."""
        # Create directory when actually initializing
        logger.debug(f"Creating session directory: {self.session_dir}")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Loading metadata...")
        # Load metadata after directory is created
        self.sessions = self._load_metadata()
        logger.info(f"Session manager initialized with directory: {self.session_dir}")

    async def shutdown(self) -> None:
        """Shutdown session manager."""
        self._save_metadata()
        logger.info("Session manager shutdown complete")

    async def save_session(  # noqa: C901, PLR0912
        self, instance: "BrowserInstance", name: str | None = None, profile_override: str | None = None
    ) -> str:
        """Save a browser session.

        Args:
            instance: The browser instance to save
            name: Optional name for the session
            profile_override: Optional profile to associate with the session (overrides instance profile)

        Returns:
            The session ID
        """
        session_id = str(uuid.uuid4())
        session_dir = self.session_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Use profile_override if provided, otherwise use instance profile
        session_profile = profile_override if profile_override is not None else instance._profile_name

        # Capture all tabs
        tabs = []
        current_handle = None
        actual_active_tab = None  # The tab user is actually viewing
        last_real_tab = None  # Fallback: last real page we saw
        all_cookies: list[dict[str, Any]] = []  # Collect cookies from ALL tabs
        if instance.driver:
            try:
                current_handle = instance.driver.current_window_handle

                # Iterate through all tabs and capture their state
                for handle in instance.driver.window_handles:
                    instance.driver.switch_to.window(handle)
                    tab_url = instance.driver.current_url
                    tab_title = instance.driver.title

                    tabs.append(
                        {
                            "handle": str(handle),
                            "url": tab_url,
                            "title": tab_title,
                        }
                    )

                    # Collect cookies from this tab (only from http/https pages)
                    if tab_url.startswith(("http://", "https://")):
                        try:
                            tab_cookies = instance.driver.get_cookies()
                            # Add cookies we don't already have (avoid duplicates)
                            for cookie in tab_cookies:
                                cookie_key = (cookie.get("name"), cookie.get("domain"))
                                if not any((c.get("name"), c.get("domain")) == cookie_key for c in all_cookies):
                                    all_cookies.append(cookie)
                        except Exception as e:
                            logger.warning(f"Failed to get cookies from tab {tab_url}: {e}")

                    # Track the last real page we see (for fallback)
                    is_real_page = not ("chrome://" in tab_url or "about:blank" in tab_url or tab_url == "data:,")
                    if is_real_page:
                        last_real_tab = str(handle)

                # Now determine which tab is actually active
                # First, check if current_handle points to a real page
                current_tab_data = next((t for t in tabs if t["handle"] == str(current_handle)), None) if current_handle else None
                if current_tab_data:
                    current_is_real = not (
                        "chrome://" in current_tab_data["url"] or "about:blank" in current_tab_data["url"] or current_tab_data["url"] == "data:,"
                    )

                    if current_is_real:
                        # Current handle points to a real page - use it
                        actual_active_tab = str(current_handle)
                    elif last_real_tab:
                        # Current handle points to chrome://new-tab-page, use last real tab instead
                        actual_active_tab = last_real_tab
                    else:
                        # No real tabs found, use current_handle anyway
                        actual_active_tab = str(current_handle)
                else:
                    # No current_handle (shouldn't happen), use last real tab or first tab
                    actual_active_tab = last_real_tab if last_real_tab else (tabs[0]["handle"] if tabs else None)

                # Switch back to the actual active tab we identified
                if actual_active_tab and actual_active_tab in [str(h) for h in instance.driver.window_handles]:
                    instance.driver.switch_to.window(actual_active_tab)
                elif current_handle:
                    instance.driver.switch_to.window(current_handle)

            except Exception as e:
                logger.warning(f"Failed to capture all tabs: {e}. Falling back to single tab capture.")
                # If something goes wrong, use current handle
                actual_active_tab = str(current_handle) if current_handle else None

        # Determine URL and title from the actual active tab
        active_tab_data = None
        if actual_active_tab and tabs:
            active_tab_data = next((t for t in tabs if t["handle"] == actual_active_tab), None)

        # Fallback: if no active tab identified, use first non-chrome tab, or first tab
        if not active_tab_data and tabs:
            real_tabs = [t for t in tabs if not ("chrome://" in t["url"] or "about:blank" in t["url"])]
            active_tab_data = real_tabs[0] if real_tabs else tabs[0]
            actual_active_tab = active_tab_data["handle"]

        # Save session data
        session_data = {
            "id": session_id,
            "name": name or f"session_{session_id[:8]}",
            "created_at": datetime.now().isoformat(),
            "profile": session_profile,
            "url": active_tab_data["url"] if active_tab_data else (instance.driver.current_url if instance.driver else None),
            "title": active_tab_data["title"] if active_tab_data else (instance.driver.title if instance.driver else None),
            "cookies": all_cookies,  # All cookies from all tabs
            "window_handles": len(instance.driver.window_handles) if instance.driver else 0,
            "tabs": tabs,
            "active_tab_handle": actual_active_tab,
        }

        # Save to file
        session_file = session_dir / "session.json"
        with session_file.open("w") as f:
            json.dump(session_data, f, indent=2)

        # Update metadata
        self.sessions[session_id] = {
            "name": session_data["name"],
            "created_at": session_data["created_at"],
            "profile": session_data["profile"],
            "url": session_data["url"],
            "title": session_data["title"],
        }
        self._save_metadata()

        logger.info(f"Saved session {session_id}")
        return session_id

    async def restore_session(  # noqa: C901, PLR0912
        self,
        session_id: str,
        manager: "ChromeManager",
        profile_override: str | None = None,
        headless: bool | None = None,
        kill_orphaned: bool = False,
    ) -> "BrowserInstance":
        """Restore a browser session.

        Args:
            session_id: The session ID to restore
            manager: The ChromeManager instance to create the browser with
            profile_override: Optional profile to use instead of saved profile
            headless: Optional headless mode override (defaults to False for interactive use)
            kill_orphaned: Kill orphaned Chrome processes holding profile locks

        Returns:
            A new browser instance with the restored session
        """
        if session_id not in self.sessions:
            raise SessionError(f"Session {session_id} not found")

        session_dir = self.session_dir / session_id
        session_file = session_dir / "session.json"

        if not session_file.exists():
            raise SessionError(f"Session file not found for {session_id}")

        # Load session data
        with session_file.open() as f:
            session_data = json.load(f)

        # Use override profile if provided, otherwise use saved profile
        profile_name = profile_override if profile_override is not None else session_data.get("profile")
        if profile_override is not None:
            logger.info(f"Overriding saved profile with '{profile_override}' for session {session_id}")

        # Use headless override if provided, otherwise default to False (interactive)
        use_headless = headless if headless is not None else False

        instance = await manager.get_or_create_instance(
            profile=profile_name,
            headless=use_headless,
            kill_orphaned=kill_orphaned,
        )

        # Restore the session state
        if instance.driver:
            # Restore all tabs
            tabs = session_data.get("tabs", [])
            active_tab_handle = session_data.get("active_tab_handle")

            if tabs:
                # Restore all tabs first, then set cookies on each
                handle_mapping = {}

                # First tab: use existing tab and navigate
                first_tab = tabs[0]
                instance.driver.get(first_tab["url"])
                first_handle = instance.driver.current_window_handle
                handle_mapping[tabs[0]["handle"]] = first_handle

                # Restore remaining tabs (if any)
                for tab in tabs[1:]:
                    instance.driver.execute_script("window.open('');")
                    new_handle = instance.driver.window_handles[-1]
                    handle_mapping[tab["handle"]] = new_handle
                    instance.driver.switch_to.window(new_handle)
                    instance.driver.get(tab["url"])

                # Now restore cookies to ALL tabs that can accept them
                if session_data.get("cookies"):
                    cookies_restored_total = 0

                    for tab in tabs:
                        tab_url = tab["url"]

                        # Skip chrome:// and other non-http(s) URLs
                        if not tab_url.startswith(("http://", "https://")):
                            continue

                        parsed = urlparse(tab_url)
                        if not (parsed.scheme and parsed.netloc):
                            continue

                        # Switch to this tab
                        tab_handle = handle_mapping.get(tab["handle"])
                        if not tab_handle:
                            continue

                        instance.driver.switch_to.window(tab_handle)

                        # Navigate to domain root for cookie setting
                        domain_url = f"{parsed.scheme}://{parsed.netloc}/"
                        instance.driver.get(domain_url)

                        # Check if we're on an error page
                        current_url = instance.driver.current_url
                        page_source = instance.driver.page_source.lower() if instance.driver.page_source else ""

                        is_error_page = (
                            "data:text/html,chromewebdata" in current_url
                            or "chrome-error:" in current_url
                            or "net::err_cert" in page_source
                            or "your connection is not private" in page_source
                        )

                        if not is_error_page:
                            # Try to restore cookies that match this domain
                            for cookie in session_data["cookies"]:
                                cookie_domain = cookie.get("domain", "")
                                # Check if cookie domain matches this tab's domain
                                if cookie_domain and (
                                    parsed.netloc == cookie_domain.lstrip(".")
                                    or parsed.netloc.endswith(cookie_domain)
                                    or cookie_domain.lstrip(".") in parsed.netloc
                                ):
                                    try:
                                        instance.driver.add_cookie(cookie)
                                        cookies_restored_total += 1
                                    except Exception as e:
                                        logger.warning(f"Failed to restore cookie {cookie.get('name', 'unknown')}: {e}")

                            # Navigate back to the actual tab URL after setting cookies
                            instance.driver.get(tab_url)

                    logger.info(f"Restored {cookies_restored_total}/{len(session_data['cookies'])} cookies")

                # Switch to the originally active tab
                if active_tab_handle and active_tab_handle in handle_mapping:
                    instance.driver.switch_to.window(handle_mapping[active_tab_handle])
                    logger.info(f"Restored {len(tabs)} tabs and switched to original active tab")
                else:
                    logger.info(f"Restored {len(tabs)} tabs")
            else:
                # Old format: single URL
                saved_url = session_data.get("url")
                if session_data.get("cookies") and saved_url:
                    parsed = urlparse(saved_url)
                    domain_url = f"{parsed.scheme}://{parsed.netloc}/"
                    instance.driver.get(domain_url)

                    current_url = instance.driver.current_url
                    page_source = instance.driver.page_source.lower() if instance.driver.page_source else ""

                    is_error_page = (
                        "data:text/html,chromewebdata" in current_url
                        or "chrome-error:" in current_url
                        or "net::err_cert" in page_source
                        or "your connection is not private" in page_source
                    )

                    if not is_error_page:
                        cookies_restored = 0
                        for cookie in session_data["cookies"]:
                            try:
                                instance.driver.add_cookie(cookie)
                                cookies_restored += 1
                            except Exception as e:
                                logger.warning(f"Failed to restore cookie {cookie.get('name', 'unknown')}: {e}")
                        logger.info(f"Restored {cookies_restored}/{len(session_data['cookies'])} cookies")

                if saved_url:
                    instance.driver.get(saved_url)

        logger.info(f"Restored session {session_id} with profile {profile_name}")
        return instance

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        result = []
        for session_id, metadata in self.sessions.items():
            session_dir = self.session_dir / session_id
            result.append(
                {
                    "id": session_id,
                    "name": metadata.get("name", f"session_{session_id[:8]}"),
                    "created_at": metadata.get("created_at"),
                    "profile": metadata.get("profile"),
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "exists": session_dir.exists(),
                },
            )
        return sorted(result, key=lambda x: x["created_at"] or "", reverse=True)

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a saved session.

        Args:
            session_id: The session ID to rename
            new_name: The new name for the session

        Returns:
            True if renamed, False if not found
        """
        if session_id not in self.sessions:
            return False

        # Update metadata
        self.sessions[session_id]["name"] = new_name
        self._save_metadata()

        # Update session file
        session_dir = self.session_dir / session_id
        session_file = session_dir / "session.json"
        if session_file.exists():
            with session_file.open() as f:
                session_data = json.load(f)
            session_data["name"] = new_name
            with session_file.open("w") as f:
                json.dump(session_data, f, indent=2)

        logger.info(f"Renamed session {session_id} to '{new_name}'")
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a saved session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if session_id not in self.sessions:
            return False

        # Delete session directory
        session_dir = self.session_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)

        # Remove from metadata
        del self.sessions[session_id]
        self._save_metadata()

        logger.info(f"Deleted session {session_id}")
        return True
