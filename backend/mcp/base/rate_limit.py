"""Rate limiting middleware for MCP servers."""

import time
from collections import defaultdict
from typing import Any

from loguru import logger


class RateLimiter:
    """Token bucket rate limiter implementation."""

    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request is allowed for a client.

        Args:
            client_id: Unique client identifier

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()

        # Clean old requests
        self.requests[client_id] = [req_time for req_time in self.requests[client_id] if current_time - req_time < self.window_seconds]

        # Check if under limit
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(current_time)
            return True

        return False

    def get_retry_after(self, client_id: str) -> int:
        """Get seconds until next request is allowed.

        Args:
            client_id: Unique client identifier

        Returns:
            Seconds to wait before retry
        """
        if not self.requests[client_id]:
            return 0

        oldest_request = min(self.requests[client_id])
        retry_after = self.window_seconds - (time.time() - oldest_request)
        return max(0, int(retry_after))


class LeakyBucketRateLimiter:
    """Leaky bucket rate limiter with smooth rate limiting."""

    def __init__(self, capacity: int, leak_rate: float):
        """Initialize leaky bucket rate limiter.

        Args:
            capacity: Maximum bucket capacity
            leak_rate: Requests leaked per second
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"level": 0.0, "last_leak": time.time()})

    def is_allowed(self, client_id: str, cost: float = 1.0) -> bool:
        """Check if a request is allowed for a client.

        Args:
            client_id: Unique client identifier
            cost: Cost of this request (default: 1.0)

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        bucket = self.buckets[client_id]

        # Calculate leak since last request
        time_passed = current_time - bucket["last_leak"]
        leaked = time_passed * self.leak_rate

        # Update bucket level
        bucket["level"] = max(0, bucket["level"] - leaked)
        bucket["last_leak"] = current_time

        # Check if request fits
        if bucket["level"] + cost <= self.capacity:
            bucket["level"] += cost
            return True

        return False


class RateLimitMiddleware:
    """Middleware for rate limiting requests."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60, use_leaky_bucket: bool = False):
        """Initialize rate limit middleware.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            use_leaky_bucket: Use leaky bucket instead of token bucket
        """
        if use_leaky_bucket:
            # Convert to leaky bucket parameters
            leak_rate = max_requests / window_seconds
            self.limiter: RateLimiter | LeakyBucketRateLimiter = LeakyBucketRateLimiter(max_requests, leak_rate)
        else:
            self.limiter = RateLimiter(max_requests, window_seconds)

        self.use_leaky_bucket = use_leaky_bucket
        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_seconds}s " f"({'leaky bucket' if use_leaky_bucket else 'token bucket'})")

    async def process(self, context: dict[str, Any], request: dict) -> dict | None:
        """Process rate limiting for a request.

        Args:
            context: Connection context
            request: The request data

        Returns:
            Error response if rate limited, None otherwise
        """
        # Get client identifier
        client_addr = context.get("client_addr")
        if not client_addr:
            return None

        # Use IP address as client ID
        client_id = str(client_addr[0]) if isinstance(client_addr, tuple) else str(client_addr)

        # Store limiter in context for other middlewares
        if "rate_limiter" not in context:
            context["rate_limiter"] = self.limiter

        # Check rate limit
        if self.limiter.is_allowed(client_id):
            return None

        # Rate limited - return error
        logger.warning(f"Rate limit exceeded for client {client_id}")

        retry_after = None
        if isinstance(self.limiter, RateLimiter):
            retry_after = self.limiter.get_retry_after(client_id)

        error_data = {
            "code": -32003,
            "message": "Rate limit exceeded",
        }

        if retry_after is not None:
            error_data["data"] = {"retry_after": retry_after}

        return {"jsonrpc": "2.0", "error": error_data, "id": request.get("id")}


class MethodRateLimiter:
    """Rate limiter that applies different limits per method."""

    def __init__(self, method_limits: dict[str, tuple[int, int]], default_limit: tuple[int, int] | None = None):
        """Initialize method-based rate limiter.

        Args:
            method_limits: Dict of method -> (max_requests, window_seconds)
            default_limit: Default limit for unlisted methods
        """
        self.limiters = {}
        for method, (max_requests, window) in method_limits.items():
            self.limiters[method] = RateLimiter(max_requests, window)

        if default_limit:
            self.default_limiter = RateLimiter(*default_limit)
        else:
            self.default_limiter = None

    def is_allowed(self, client_id: str, method: str) -> bool:
        """Check if a request is allowed for a client and method.

        Args:
            client_id: Unique client identifier
            method: Method name

        Returns:
            True if request is allowed, False if rate limited
        """
        limiter = self.limiters.get(method, self.default_limiter)
        if limiter:
            return limiter.is_allowed(client_id)
        return True  # No limit for this method
