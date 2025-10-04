"""Browser session management for saving and restoring browser state."""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

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

    async def save_session(self, instance: "BrowserInstance", name: str | None = None) -> str:
        """Save a browser session.

        Args:
            instance: The browser instance to save
            name: Optional name for the session

        Returns:
            The session ID
        """
        session_id = str(uuid.uuid4())
        session_dir = self.session_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Save session data
        session_data = {
            "id": session_id,
            "name": name or f"session_{session_id[:8]}",
            "created_at": datetime.now().isoformat(),
            "profile": instance._profile_name,
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

    async def restore_session(self, session_id: str, manager: "ChromeManager") -> "BrowserInstance":
        """Restore a browser session.

        Args:
            session_id: The session ID to restore
            manager: The ChromeManager instance to create the browser with

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

        # Create new instance with the saved profile
        profile_name = session_data.get("profile")
        instance = await manager.get_or_create_instance(
            profile=profile_name,
            headless=False,  # Sessions are typically for interactive use
        )

        # Restore the session state
        if instance.driver:
            # Navigate to the saved URL
            if session_data.get("url"):
                instance.driver.get(session_data["url"])

            # Restore cookies
            if session_data.get("cookies"):
                for cookie in session_data["cookies"]:
                    try:
                        instance.driver.add_cookie(cookie)
                    except Exception as e:
                        logger.warning(f"Failed to restore cookie: {e}")

            # Refresh to apply cookies
            if session_data.get("url"):
                instance.driver.refresh()

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
