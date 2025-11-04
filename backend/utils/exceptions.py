"""Enhanced exception hierarchy for Chrome Manager."""

from typing import Any


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

    def __init__(
        self,
        message: str,
        error_code: str = "CHROME_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.retryable = retryable
        self.user_message = user_message

    def __str__(self) -> str:
        """Return the error message."""
        return self.user_message or self.message

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r}, retryable={self.retryable})"


class InstanceError(ChromeManagerError):
    """Browser instance related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INSTANCE_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        instance_id: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.instance_id = instance_id
        if instance_id:
            self.context["instance_id"] = instance_id


class NavigationError(ChromeManagerError):
    """Navigation related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "NAVIGATION_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        url: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.url = url
        self.status_code = status_code
        if url:
            self.context["url"] = url
        if status_code:
            self.context["status_code"] = status_code


class InputError(ChromeManagerError):
    """Input event related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INPUT_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        element: str | None = None,
        action: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.element = element
        self.action = action
        if element:
            self.context["element"] = element
        if action:
            self.context["action"] = action


class MediaError(ChromeManagerError):
    """Media capture related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "MEDIA_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        media_type: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.media_type = media_type
        if media_type:
            self.context["media_type"] = media_type


class ExtensionError(ChromeManagerError):
    """Extension related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "EXTENSION_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        extension_path: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.extension_path = extension_path
        if extension_path:
            self.context["extension_path"] = extension_path


class ConfigError(ChromeManagerError):
    """Configuration related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIG_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        config_key: str | None = None,
        config_file: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.config_key = config_key
        self.config_file = config_file
        if config_key:
            self.context["config_key"] = config_key
        if config_file:
            self.context["config_file"] = config_file


class MCPError(ChromeManagerError):
    """MCP protocol related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "MCP_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        tool_name: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.tool_name = tool_name
        self.request_id = request_id
        if tool_name:
            self.context["tool_name"] = tool_name
        if request_id:
            self.context["request_id"] = request_id


class ChromeTimeoutError(ChromeManagerError):
    """Operation timeout errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "TIMEOUT_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = True,  # Timeouts are usually retryable
        user_message: str = "",
        timeout_seconds: float | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        if timeout_seconds:
            self.context["timeout_seconds"] = timeout_seconds
        if operation:
            self.context["operation"] = operation


class PoolError(ChromeManagerError):
    """Browser pool related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "POOL_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        pool_size: int | None = None,
        available_instances: int | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.pool_size = pool_size
        self.available_instances = available_instances
        if pool_size is not None:
            self.context["pool_size"] = pool_size
        if available_instances is not None:
            self.context["available_instances"] = available_instances


class ProfileError(ChromeManagerError):
    """Profile management related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "PROFILE_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        profile_name: str | None = None,
        profile_path: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.profile_name = profile_name
        self.profile_path = profile_path
        if profile_name:
            self.context["profile_name"] = profile_name
        if profile_path:
            self.context["profile_path"] = profile_path


class SessionError(ChromeManagerError):
    """Session management related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "SESSION_ERROR",
        context: dict[str, Any] | None = None,
        retryable: bool = False,
        user_message: str = "",
        session_id: str | None = None,
        session_file: str | None = None,
    ) -> None:
        super().__init__(message, error_code, context, retryable, user_message)
        self.session_id = session_id
        self.session_file = session_file
        if session_id:
            self.context["session_id"] = session_id
        if session_file:
            self.context["session_file"] = session_file


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
