"""Utilities for MCP servers."""

import asyncio
import functools
import inspect
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class AsyncExecutor:
    """Utility for executing sync operations in async context safely."""

    def __init__(self, max_workers: int = 4):
        """Initialize async executor.

        Args:
            max_workers: Maximum thread pool workers
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Run a synchronous function in a thread pool.

        Args:
            func: Synchronous function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))

    def make_async(self, func: Callable) -> Callable:
        """Convert a synchronous function to async.

        Args:
            func: Synchronous function

        Returns:
            Async wrapper function
        """

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.run_sync(func, *args, **kwargs)

        return async_wrapper

    def smart_wrap(self, func: Callable) -> Callable:
        """Wrap a function to be async if it's sync, or return as-is if async.

        Args:
            func: Function to wrap

        Returns:
            Async-compatible function
        """
        if asyncio.iscoroutinefunction(func):
            return func
        return self.make_async(func)

    def __del__(self):
        """Cleanup executor on deletion."""
        self._executor.shutdown(wait=False)


def ensure_async(func: Callable) -> Callable:
    """Decorator to ensure a function is async-compatible.

    Args:
        func: Function to wrap

    Returns:
        Async-compatible function
    """
    if asyncio.iscoroutinefunction(func):
        return func

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    return async_wrapper


def run_async_in_sync(coro):
    """Run an async coroutine in a sync context.

    Args:
        coro: Coroutine to run

    Returns:
        Coroutine result
    """
    try:
        asyncio.get_running_loop()
        # We're already in an async context
        if inspect.iscoroutine(coro):
            return asyncio.create_task(coro)
        return coro
    except RuntimeError:
        # No running loop, create one
        return asyncio.run(coro)


class SyncAsyncBridge:
    """Bridge for calling between sync and async code."""

    def __init__(self):
        """Initialize the bridge."""
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._loop = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations.

        Args:
            loop: Event loop to use
        """
        self._loop = loop

    def call_async_from_sync(self, coro):
        """Call async code from sync context.

        Args:
            coro: Coroutine to run

        Returns:
            Result of coroutine
        """
        if self._loop and self._loop.is_running():
            # Submit to existing loop
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result()
        # Create new loop
        return asyncio.run(coro)

    async def call_sync_from_async(self, func: Callable, *args, **kwargs):
        """Call sync code from async context.

        Args:
            func: Synchronous function
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))


def format_error(code: int, message: str, data: Any = None) -> dict:
    """Format a standard error response.

    Args:
        code: Error code
        message: Error message
        data: Additional error data

    Returns:
        Error response dictionary
    """
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return error


def format_response(success: bool, data: Any = None, error: dict | None = None) -> dict:
    """Format a standard response.

    Args:
        success: Whether operation succeeded
        data: Response data
        error: Error information if failed

    Returns:
        Response dictionary
    """
    response: dict[str, Any] = {"success": success}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return response


class AsyncContextManager:
    """Async context manager for resource cleanup."""

    def __init__(self, acquire_func: Callable, release_func: Callable):
        """Initialize context manager.

        Args:
            acquire_func: Function to acquire resource
            release_func: Function to release resource
        """
        self.acquire_func = ensure_async(acquire_func)
        self.release_func = ensure_async(release_func)
        self.resource = None

    async def __aenter__(self):
        """Acquire resource."""
        self.resource = await self.acquire_func()
        return self.resource

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release resource."""
        if self.resource:
            await self.release_func(self.resource)
        return False


def batch_async_operations(operations: list[Callable], max_concurrent: int = 10):
    """Execute async operations in batches.

    Args:
        operations: List of async callables
        max_concurrent: Maximum concurrent operations

    Returns:
        Async generator yielding results
    """

    async def execute_batch():
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(operation):
            async with semaphore:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, operation)

        tasks = [execute_with_semaphore(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=True)

    return execute_batch()
