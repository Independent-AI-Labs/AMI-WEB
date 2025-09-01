"""Timing constants and utilities."""

import platform
import signal
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any


class TimingConstants:
    """Centralized timing constants for consistent behavior."""

    # Default wait times
    DEFAULT_WAIT = 0.1
    POLL_INTERVAL = 0.5
    SHORT_WAIT = 0.5
    MEDIUM_WAIT = 1.0
    LONG_WAIT = 3.0

    # Timeout values
    PAGE_LOAD_TIMEOUT = 30
    SCRIPT_TIMEOUT = 10
    ELEMENT_WAIT_TIMEOUT = 10
    NETWORK_TIMEOUT = 60

    # Retry settings
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1.0

    # Animation and rendering
    ANIMATION_WAIT = 0.3
    RENDER_WAIT = 0.5


def wait_with_retry(
    func: Callable[[], Any],
    timeout: float = TimingConstants.ELEMENT_WAIT_TIMEOUT,
    poll_interval: float = TimingConstants.POLL_INTERVAL,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Any:
    """Wait for a function to return successfully.

    Args:
        func: Function to execute
        timeout: Maximum time to wait in seconds
        poll_interval: Time between retries in seconds
        exceptions: Exceptions to catch and retry on

    Returns:
        Function result

    Raises:
        TimeoutError: If function doesn't succeed within timeout
    """
    end_time = time.time() + timeout
    last_exception = None

    while time.time() < end_time:
        try:
            return func()
        except exceptions as e:
            last_exception = e
            time.sleep(poll_interval)

    raise TimeoutError(f"Timed out after {timeout}s waiting for {func.__name__}. Last error: {last_exception}")


def with_timeout(timeout: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to add timeout to a function.

    Note: On Windows, this uses threading instead of signals.

    Args:
        timeout: Maximum execution time in seconds

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use threading on Windows since SIGALRM is not available
            if platform.system() == "Windows":
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        return future.result(timeout=timeout)
                    except FutureTimeoutError as e:
                        raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s") from e
            else:
                # Unix-based systems can use signal

                def timeout_handler(_signum: Any, _frame: Any) -> None:
                    raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")

                # Set timeout alarm
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)  # type: ignore[attr-defined]
                signal.alarm(int(timeout))  # type: ignore[attr-defined]

                try:
                    result = func(*args, **kwargs)
                finally:
                    # Reset alarm
                    signal.alarm(0)  # type: ignore[attr-defined]
                    signal.signal(signal.SIGALRM, old_handler)  # type: ignore[attr-defined]

                return result

        return wrapper

    return decorator
