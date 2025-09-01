"""Enhanced exception hierarchy for Chrome Manager."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChromeManagerError(Exception):
    """
    Base exception for Chrome Manager with rich context.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code for programmatic handling
        context: Additional context data about the error
        retryable: Whether the operation can be retried
        user_message: User-friendly message (if different from message)
    """

    message: str
    error_code: str = "CHROME_ERROR"
    context: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    user_message: str = ""

    def __str__(self) -> str:
        """Return the error message."""
        return self.user_message or self.message

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r}, retryable={self.retryable})"


@dataclass
class InstanceError(ChromeManagerError):
    """Browser instance related errors."""

    error_code: str = "INSTANCE_ERROR"
    instance_id: str | None = None

    def __post_init__(self) -> None:
        """Add instance_id to context if provided."""
        if self.instance_id:
            self.context["instance_id"] = self.instance_id


@dataclass
class NavigationError(ChromeManagerError):
    """Navigation related errors."""

    error_code: str = "NAVIGATION_ERROR"
    url: str | None = None
    status_code: int | None = None

    def __post_init__(self) -> None:
        """Add navigation details to context."""
        if self.url:
            self.context["url"] = self.url
        if self.status_code:
            self.context["status_code"] = self.status_code


@dataclass
class InputError(ChromeManagerError):
    """Input event related errors."""

    error_code: str = "INPUT_ERROR"
    element: str | None = None
    action: str | None = None

    def __post_init__(self) -> None:
        """Add input details to context."""
        if self.element:
            self.context["element"] = self.element
        if self.action:
            self.context["action"] = self.action


@dataclass
class MediaError(ChromeManagerError):
    """Media capture related errors."""

    error_code: str = "MEDIA_ERROR"
    media_type: str | None = None  # "screenshot", "video", etc.

    def __post_init__(self) -> None:
        """Add media details to context."""
        if self.media_type:
            self.context["media_type"] = self.media_type


@dataclass
class ExtensionError(ChromeManagerError):
    """Extension related errors."""

    error_code: str = "EXTENSION_ERROR"
    extension_path: str | None = None

    def __post_init__(self) -> None:
        """Add extension details to context."""
        if self.extension_path:
            self.context["extension_path"] = self.extension_path


@dataclass
class ConfigError(ChromeManagerError):
    """Configuration related errors."""

    error_code: str = "CONFIG_ERROR"
    config_key: str | None = None
    config_file: str | None = None

    def __post_init__(self) -> None:
        """Add config details to context."""
        if self.config_key:
            self.context["config_key"] = self.config_key
        if self.config_file:
            self.context["config_file"] = self.config_file


@dataclass
class MCPError(ChromeManagerError):
    """MCP protocol related errors."""

    error_code: str = "MCP_ERROR"
    tool_name: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        """Add MCP details to context."""
        if self.tool_name:
            self.context["tool_name"] = self.tool_name
        if self.request_id:
            self.context["request_id"] = self.request_id


@dataclass
class ChromeTimeoutError(ChromeManagerError):
    """Operation timeout errors."""

    error_code: str = "TIMEOUT_ERROR"
    retryable: bool = True  # Timeouts are usually retryable
    timeout_seconds: float | None = None
    operation: str | None = None

    def __post_init__(self) -> None:
        """Add timeout details to context."""
        if self.timeout_seconds:
            self.context["timeout_seconds"] = self.timeout_seconds
        if self.operation:
            self.context["operation"] = self.operation


@dataclass
class PoolError(ChromeManagerError):
    """Browser pool related errors."""

    error_code: str = "POOL_ERROR"
    pool_size: int | None = None
    available_instances: int | None = None

    def __post_init__(self) -> None:
        """Add pool details to context."""
        if self.pool_size is not None:
            self.context["pool_size"] = self.pool_size
        if self.available_instances is not None:
            self.context["available_instances"] = self.available_instances


@dataclass
class ProfileError(ChromeManagerError):
    """Profile management related errors."""

    error_code: str = "PROFILE_ERROR"
    profile_name: str | None = None
    profile_path: str | None = None

    def __post_init__(self) -> None:
        """Add profile details to context."""
        if self.profile_name:
            self.context["profile_name"] = self.profile_name
        if self.profile_path:
            self.context["profile_path"] = self.profile_path


@dataclass
class SessionError(ChromeManagerError):
    """Session management related errors."""

    error_code: str = "SESSION_ERROR"
    session_id: str | None = None
    session_file: str | None = None

    def __post_init__(self) -> None:
        """Add session details to context."""
        if self.session_id:
            self.context["session_id"] = self.session_id
        if self.session_file:
            self.context["session_file"] = self.session_file


# Specific error codes for common scenarios
class ErrorCodes:
    """Common error codes for programmatic handling."""

    # Instance errors
    INSTANCE_NOT_FOUND = "INSTANCE_NOT_FOUND"
    INSTANCE_ALREADY_EXISTS = "INSTANCE_ALREADY_EXISTS"
    INSTANCE_LAUNCH_FAILED = "INSTANCE_LAUNCH_FAILED"
    INSTANCE_TERMINATED = "INSTANCE_TERMINATED"

    # Navigation errors
    PAGE_LOAD_FAILED = "PAGE_LOAD_FAILED"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    INVALID_URL = "INVALID_URL"

    # Pool errors
    POOL_EXHAUSTED = "POOL_EXHAUSTED"
    POOL_NOT_INITIALIZED = "POOL_NOT_INITIALIZED"

    # Config errors
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"

    # Timeout errors
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
