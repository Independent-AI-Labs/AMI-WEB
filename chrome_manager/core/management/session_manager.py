"""Browser session management for saving and restoring browser state."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from ...utils.exceptions import SessionError

if TYPE_CHECKING:
    from ..browser.instance import BrowserInstance


class SessionManager:
    """Manages browser sessions for save and restore functionality."""

    def __init__(self, session_dir: str = "./sessions"):
        self.session_dir = Path(session_dir).resolve()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.session_dir / "sessions.json"
        self.sessions: dict[str, dict[str, Any]] = self._load_metadata()

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """Load session metadata."""
        if self.metadata_file.exists():
            with self.metadata_file.open() as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        """Save session metadata."""
        with self.metadata_file.open("w") as f:
            json.dump(self.sessions, f, indent=2, default=str)

    async def initialize(self) -> None:
        """Initialize session manager."""
        logger.info(f"Session manager initialized with directory: {self.session_dir}")

    async def shutdown(self) -> None:
        """Shutdown session manager."""
        self._save_metadata()
        logger.info("Session manager shutdown complete")

    async def save_session(self, instance: "BrowserInstance") -> str:
        """Save a browser session.

        Args:
            instance: The browser instance to save

        Returns:
            The session ID
        """
        session_id = str(uuid.uuid4())
        session_dir = self.session_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Save session data
        session_data = {
            "id": session_id,
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
            "created_at": session_data["created_at"],
            "profile": session_data["profile"],
            "url": session_data["url"],
            "title": session_data["title"],
        }
        self._save_metadata()

        logger.info(f"Saved session {session_id}")
        return session_id

    async def restore_session(self, session_id: str) -> "BrowserInstance":
        """Restore a browser session.

        Args:
            session_id: The session ID to restore

        Returns:
            A new browser instance with the restored session
        """
        if session_id not in self.sessions:
            raise SessionError(f"Session {session_id} not found")

        session_dir = self.session_dir / session_id
        session_file = session_dir / "session.json"

        if not session_file.exists():
            raise SessionError(f"Session file not found for {session_id}")

        # Load session data (will be used when proper restoration is implemented)
        with session_file.open() as f:
            _ = json.load(f)  # session_data will be used in full implementation

        # Create new instance with the same profile
        from .instance import BrowserInstance

        # Note: This is a simplified implementation
        # In a real scenario, we'd need access to the ChromeManager instance
        # to properly create and configure the browser instance
        instance = BrowserInstance()

        # The actual restoration would happen in ChromeManager.restore_session
        # which would:
        # 1. Create instance with the saved profile
        # 2. Navigate to the saved URL
        # 3. Restore cookies
        # For now, we return a placeholder instance
        # The ChromeManager will handle the actual restoration

        logger.info(f"Restored session {session_id} metadata")
        return instance

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        result = []
        for session_id, metadata in self.sessions.items():
            session_dir = self.session_dir / session_id
            result.append(
                {
                    "id": session_id,
                    "created_at": metadata.get("created_at"),
                    "profile": metadata.get("profile"),
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "exists": session_dir.exists(),
                }
            )
        return sorted(result, key=lambda x: x["created_at"] or "", reverse=True)

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
            import shutil

            shutil.rmtree(session_dir)

        # Remove from metadata
        del self.sessions[session_id]
        self._save_metadata()

        logger.info(f"Deleted session {session_id}")
        return True
