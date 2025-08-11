class ChromeManagerError(Exception):
    """Base exception for Chrome Manager"""


class InstanceError(ChromeManagerError):
    """Browser instance related errors"""


class NavigationError(ChromeManagerError):
    """Navigation related errors"""


class InputError(ChromeManagerError):
    """Input event related errors"""


class MediaError(ChromeManagerError):
    """Media capture related errors"""


class ExtensionError(ChromeManagerError):
    """Extension related errors"""


class ConfigError(ChromeManagerError):
    """Configuration related errors"""


class MCPError(ChromeManagerError):
    """MCP protocol related errors"""


class ChromeTimeoutError(ChromeManagerError):
    """Operation timeout errors"""


class PoolError(ChromeManagerError):
    """Raised when pool operations fail."""


class ProfileError(ChromeManagerError):
    """Raised when profile operations fail."""
