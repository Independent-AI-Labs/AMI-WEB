"""Navigation submodule for browser control.

This module provides navigation-related functionality split into focused components:
- Navigator: Core navigation (back, forward, refresh, navigate)
- Waiter: Wait conditions and element waiting
- Scroller: Scrolling and viewport control
- ContentExtractor: Page content extraction and HTML processing
- StorageController: Browser storage (localStorage/sessionStorage) management
"""

from .extractor import ContentExtractor
from .navigator import Navigator
from .scroller import Scroller
from .storage import StorageController
from .waiter import Waiter

__all__ = ["Navigator", "Waiter", "Scroller", "ContentExtractor", "StorageController"]


# Backward compatibility - create a unified NavigationController
class NavigationController(Navigator, Waiter, Scroller, ContentExtractor, StorageController):
    """Unified navigation controller combining all navigation functionality.

    This class maintains backward compatibility while using the new
    modular structure underneath.
    """
