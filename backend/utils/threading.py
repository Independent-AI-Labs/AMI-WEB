"""Threading and async context utilities."""

import asyncio
import threading
from typing import Any

from loguru import logger


def is_in_thread_context() -> bool:
    """Check if running in a thread with an event loop.

    Returns:
        True if in thread with event loop, False otherwise
    """
    try:
        # Check if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            return False

        # Check if there's a running event loop
        try:
            loop = asyncio.get_running_loop()
            return loop is not None
        except RuntimeError:
            # No running loop
            return False
    except Exception as e:
        logger.debug(f"Error checking thread context: {e}")
        return False


def run_in_thread_safe(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a function in a thread-safe manner.

    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    if is_in_thread_context():
        # Already in thread context, run directly
        return func(*args, **kwargs)

    # Run in new thread if needed
    result = None
    exception = None

    def wrapper() -> None:
        nonlocal result, exception
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            exception = e

    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create an event loop for the current thread.

    Returns:
        Event loop instance
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop
