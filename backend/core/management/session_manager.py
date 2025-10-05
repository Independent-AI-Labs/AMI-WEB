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

    async def save_session(self, instance: "BrowserInstance", name: str | None = None, profile_override: str | None = None) -> str:
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

        # Save session data
        session_data = {
            "id": session_id,
            "name": name or f"session_{session_id[:8]}",
            "created_at": datetime.now().isoformat(),
            "profile": session_profile,
            "url": instance.driver.current_url if instance.driver else None,
            "title": instance.driver.title if instance.driver else None,
            "cookies": instance.driver.get_cookies() if instance.driver else [],
            "window_handles": len(instance.driver.window_handles) if instance.driver else 0,
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
            saved_url = session_data.get("url")

            # If we have cookies, navigate to domain root first to set them
            if session_data.get("cookies") and saved_url:
                parsed = urlparse(saved_url)
                domain_url = f"{parsed.scheme}://{parsed.netloc}/"
                instance.driver.get(domain_url)

                # Check if we're on an error page (certificate warning, etc.)
                current_url = instance.driver.current_url
                page_source = instance.driver.page_source.lower() if instance.driver.page_source else ""

                is_error_page = (
                    "data:text/html,chromewebdata" in current_url
                    or "chrome-error:" in current_url
                    or "net::err_cert" in page_source
                    or "your connection is not private" in page_source
                )

                if is_error_page:
                    profile_msg = f"Profile '{profile_name}'" if profile_name else "Temp profile"
                    logger.warning(
                        f"Cannot restore cookies - browser is on error page. "
                        f"{profile_msg} doesn't have certificate exception. "
                        f"Cookies will not be restored."
                    )
                else:
                    # Add cookies to the domain
                    cookies_restored = 0
                    for cookie in session_data["cookies"]:
                        try:
                            instance.driver.add_cookie(cookie)
                            cookies_restored += 1
                        except Exception as e:
                            logger.warning(f"Failed to restore cookie {cookie.get('name', 'unknown')}: {e}")
                    logger.info(f"Restored {cookies_restored}/{len(session_data['cookies'])} cookies")

            # Now navigate to the saved URL with cookies present
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
