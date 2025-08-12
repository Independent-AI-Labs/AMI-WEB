"""Context submodule for tab and frame management.

This module provides context-related functionality split into focused components:
- TabController: Tab management and control
- FrameController: Frame and iframe management
"""

from .frames import FrameController
from .tabs import TabController

__all__ = ["TabController", "FrameController"]


# Backward compatibility - create a unified ContextManager
class ContextManager(TabController, FrameController):
    """Unified context manager combining tab and frame functionality.

    This class maintains backward compatibility while using the new
    modular structure underneath.
    """
