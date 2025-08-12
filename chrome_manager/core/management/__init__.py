"""Browser instance management functionality."""

from .manager import ChromeManager
from .pool import BrowserPool
from .profile_manager import ProfileManager
from .session_manager import SessionManager

__all__ = [
    "ChromeManager",
    "BrowserPool",
    "ProfileManager",
    "SessionManager",
]
