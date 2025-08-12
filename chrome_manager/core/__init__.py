"""Chrome manager core functionality."""

from .browser import BrowserInstance, BrowserLifecycle, BrowserOptionsBuilder, PropertiesManager, TabManager
from .management import BrowserPool, ChromeManager, ProfileManager, SessionManager
from .monitoring import BrowserMonitor
from .security import ChromeDriverPatcher, SimpleTabInjector, execute_anti_detection_scripts
from .storage import BrowserStorage

# Legacy aliases for backward compatibility
InstancePool = BrowserPool

__all__ = [
    # Browser
    "BrowserInstance",
    "BrowserLifecycle",
    "BrowserOptionsBuilder",
    "PropertiesManager",
    "TabManager",
    # Management
    "ChromeManager",
    "BrowserPool",
    "InstancePool",  # Legacy alias
    "ProfileManager",
    "SessionManager",
    # Monitoring
    "BrowserMonitor",
    # Security
    "ChromeDriverPatcher",
    "SimpleTabInjector",
    "execute_anti_detection_scripts",
    # Storage
    "BrowserStorage",
]
