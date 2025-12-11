"""Browser session management for saving and restoring browser state."""

from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any

from loguru import logger

from base.backend.utils.uuid_utils import uuid7
from browser.backend.core.browser.instance import BrowserInstance
from browser.backend.core.management.session.cookies_handler import restore_all_cookies, restore_all_tabs
from browser.backend.core.management.session.tab_utils import (
    collect_tab_cookies,
    determine_active_tab,
    get_active_tab_data,
)
from browser.backend.utils.exceptions import SessionError


if TYPE_CHECKING:
    from browser.backend.core.management.manager import ChromeManager


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
        # Skip if directory was deleted (happens during test cleanup)
        if not self.session_dir.exists():
            logger.debug(f"Session directory {self.session_dir} doesn't exist, skipping metadata save")
            return

        # Ensure directory exists (defensive)
        self.session_dir.mkdir(parents=True, exist_ok=True)

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

    async def save_session(
        self,
        instance: "BrowserInstance",
        name: str | None = None,
        profile_override: str | None = None,
    ) -> str:
        """Save a browser session.

        Args:
            instance: The browser instance to save
            name: Optional name for the session
            profile_override: Optional profile to associate with the session (overrides instance profile)

        Returns:
            The session ID
        """
        session_id = uuid7()
        session_dir = self.session_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Use profile_override if provided, otherwise use instance profile
        session_profile = profile_override if profile_override is not None else instance._profile_name

        # Capture all tabs
        tabs = []
        current_handle = None
        actual_active_tab = None  # The tab user is actually viewing
        all_cookies: list[dict[str, Any]] = []  # Collect cookies from ALL tabs
        if instance.driver:
            try:
                # Store the original current handle BEFORE switching tabs
                current_handle = instance.driver.current_window_handle
                original_handle = current_handle

                # Build a mapping of handles to their state BEFORE switching
                # This prevents tab state corruption during iteration
                handle_states: dict[str, tuple[str, str]] = {}  # handle -> (url, title)

                # First pass: just get the handles
                all_handles = list(instance.driver.window_handles)

                # Second pass: collect state from each tab
                for handle in all_handles:
                    try:
                        instance.driver.switch_to.window(handle)
                        tab_url = instance.driver.current_url
                        tab_title = instance.driver.title
                        handle_states[handle] = (tab_url, tab_title)

                        # Collect cookies from this tab
                        collect_tab_cookies(instance.driver, tab_url, all_cookies)

                    except Exception as e:
                        raise SessionError(f"Failed to capture tab {handle}: {e} - cannot save incomplete session") from e

                # Build tabs list from captured state
                for handle in all_handles:
                    url, title = handle_states.get(handle, ("about:blank", ""))
                    tabs.append({"handle": str(handle), "url": url, "title": title})

                # Determine which tab is actually active
                actual_active_tab = determine_active_tab(tabs, original_handle)

                # Switch back to the original active tab
                if original_handle and original_handle in all_handles:
                    instance.driver.switch_to.window(original_handle)
                elif actual_active_tab and actual_active_tab in [str(h) for h in all_handles]:
                    instance.driver.switch_to.window(actual_active_tab)

            except Exception as e:
                logger.warning(f"Failed to capture all tabs: {e}. Using single tab capture instead.")
                # If something goes wrong, use current handle
                actual_active_tab = str(current_handle) if current_handle else None

        # Get active tab data
        active_tab_data = get_active_tab_data(tabs, actual_active_tab)
        if active_tab_data:
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

    def _load_session_data(self, session_id: str) -> dict[str, Any]:
        """Load and validate session data from disk."""
        if session_id not in self.sessions:
            raise SessionError(f"Session {session_id} not found")

        session_file = self.session_dir / session_id / "session.json"
        if not session_file.exists():
            raise SessionError(f"Session file not found for {session_id}")

        with session_file.open() as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _restore_tabs_format(
        self,
        driver: Any,
        session_data: dict[str, Any],
    ) -> None:
        """Restore session using new multi-tab format."""

        tabs = session_data.get("tabs", [])
        active_tab_handle = session_data.get("active_tab_handle")

        if not tabs:
            return

        # Restore all tabs first
        handle_mapping = restore_all_tabs(driver, tabs)

        # Restore cookies to ALL tabs that can accept them
        if session_data.get("cookies"):
            cookies_restored = restore_all_cookies(driver, tabs, handle_mapping, session_data["cookies"])
            logger.info(f"Restored {cookies_restored}/{len(session_data['cookies'])} cookies")

        # Switch to the originally active tab
        if active_tab_handle and active_tab_handle in handle_mapping:
            driver.switch_to.window(handle_mapping[active_tab_handle])
            logger.info(f"Restored {len(tabs)} tabs and switched to original active tab")
        else:
            logger.info(f"Restored {len(tabs)} tabs")

    async def restore_session(
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
        # Load session data
        session_data = self._load_session_data(session_id)

        # Determine profile to use
        profile_name = profile_override if profile_override is not None else session_data.get("profile")
        if profile_override is not None:
            logger.info(f"Overriding saved profile with '{profile_override}' for session {session_id}")

        # Create browser instance
        use_headless = headless if headless is not None else False
        instance = await manager.get_or_create_instance(
            profile=profile_name,
            headless=use_headless,
            kill_orphaned=kill_orphaned,
        )

        # Restore session state
        if instance.driver:
            self._restore_tabs_format(instance.driver, session_data)

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
