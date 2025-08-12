"""Browser core functionality."""

from .instance import BrowserInstance
from .lifecycle import BrowserLifecycle
from .options import BrowserOptionsBuilder
from .properties_manager import PropertiesManager
from .tab_manager import TabManager

__all__ = [
    "BrowserInstance",
    "BrowserLifecycle",
    "BrowserOptionsBuilder",
    "PropertiesManager",
    "TabManager",
]
