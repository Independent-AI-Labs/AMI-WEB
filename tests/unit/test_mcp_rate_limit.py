"""Unit tests for MCP rate limiting."""

import time

import pytest
from base.backend.mcp.rate_limit import (
    LeakyBucketRateLimiter,
    MethodRateLimiter,
    RateLimiter,
    RateLimitMiddleware,
)


class TestRateLimiter:
    """Test token bucket rate limiter."""

    def test_allow_under_limit(self):
        """Test requests are allowed under limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=10)
        client_id = "test-client"

        # Should allow 5 requests
        for _ in range(5):
            assert limiter.is_allowed(client_id)

        # 6th request should be blocked
        assert not limiter.is_allowed(client_id)

    def test_window_reset(self):
        """Test that window resets after time passes."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        client_id = "test-client"

        # Use up the limit
        assert limiter.is_allowed(client_id)
        assert limiter.is_allowed(client_id)
        assert not limiter.is_allowed(client_id)

        # Wait for window to reset
        time.sleep(1.1)

        # Should allow again
        assert limiter.is_allowed(client_id)

    def test_multiple_clients(self):
        """Test rate limiting per client."""
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        # Client 1 uses limit
        assert limiter.is_allowed("client1")
        assert limiter.is_allowed("client1")
        assert not limiter.is_allowed("client1")

        # Client 2 should still be allowed
        assert limiter.is_allowed("client2")
        assert limiter.is_allowed("client2")
        assert not limiter.is_allowed("client2")

    def test_get_retry_after(self):
        """Test retry after calculation."""
        limiter = RateLimiter(max_requests=1, window_seconds=5)
        client_id = "test-client"

        # Use up limit
        assert limiter.is_allowed(client_id)

        # Check retry after
        retry_after = limiter.get_retry_after(client_id)
        min_retry = 4
        max_retry = 5
        assert min_retry <= retry_after <= max_retry


class TestLeakyBucketRateLimiter:
    """Test leaky bucket rate limiter."""

    def test_bucket_capacity(self):
        """Test bucket capacity limits."""
        limiter = LeakyBucketRateLimiter(capacity=5, leak_rate=1.0)
        client_id = "test-client"

        # Should allow up to capacity
        for _ in range(5):
            assert limiter.is_allowed(client_id)

        # Should block when full
        assert not limiter.is_allowed(client_id)

    def test_bucket_leak(self):
        """Test bucket leaking over time."""
        limiter = LeakyBucketRateLimiter(capacity=3, leak_rate=2.0)  # 2 per second
        client_id = "test-client"

        # Fill bucket
        assert limiter.is_allowed(client_id, cost=3.0)
        assert not limiter.is_allowed(client_id)

        # Wait for leak
        time.sleep(1.1)  # Should leak 2.2

        # Should allow 2 more
        assert limiter.is_allowed(client_id, cost=2.0)

    def test_variable_cost(self):
        """Test requests with variable costs."""
        limiter = LeakyBucketRateLimiter(capacity=10, leak_rate=1.0)
        client_id = "test-client"

        # High cost request
        assert limiter.is_allowed(client_id, cost=8.0)

        # Low cost request should still fit
        assert limiter.is_allowed(client_id, cost=2.0)

        # No more room
        assert not limiter.is_allowed(client_id, cost=1.0)


class TestRateLimitMiddleware:
    """Test rate limit middleware."""

    @pytest.mark.asyncio
    async def test_request_allowed_under_limit(self):
        """Test requests are allowed under limit."""
        middleware = RateLimitMiddleware(max_requests=5, window_seconds=10)

        context = {"client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        # Should allow 5 requests
        for _ in range(5):
            result = await middleware.process(context, request)
            assert result is None

    @pytest.mark.asyncio
    async def test_request_blocked_over_limit(self):
        """Test requests are blocked over limit."""
        middleware = RateLimitMiddleware(max_requests=2, window_seconds=10)

        context = {"client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        # Use up limit
        assert await middleware.process(context, request) is None
        assert await middleware.process(context, request) is None

        # Should block
        result = await middleware.process(context, request)
        assert result is not None
        assert "error" in result
        rate_limit_code = -32003
        assert result["error"]["code"] == rate_limit_code

    @pytest.mark.asyncio
    async def test_retry_after_in_error(self):
        """Test retry after is included in error."""
        middleware = RateLimitMiddleware(max_requests=1, window_seconds=5)

        context = {"client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        # Use up limit
        await middleware.process(context, request)

        # Get error with retry after
        result = await middleware.process(context, request)
        assert result is not None
        assert "error" in result
        assert "data" in result["error"]
        assert "retry_after" in result["error"]["data"]
        assert result["error"]["data"]["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_leaky_bucket_mode(self):
        """Test middleware with leaky bucket."""
        middleware = RateLimitMiddleware(max_requests=3, window_seconds=1, use_leaky_bucket=True)

        context = {"client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        # Should allow up to capacity
        for _ in range(3):
            result = await middleware.process(context, request)
            assert result is None

        # Should block when full
        result = await middleware.process(context, request)
        assert result is not None
        assert "error" in result


class TestMethodRateLimiter:
    """Test method-specific rate limiting."""

    def test_method_specific_limits(self):
        """Test different limits per method."""
        method_limits = {
            "expensive": (1, 10),  # 1 per 10 seconds
            "normal": (5, 10),  # 5 per 10 seconds
        }

        limiter = MethodRateLimiter(method_limits)
        client_id = "test-client"

        # Expensive method - only 1 allowed
        assert limiter.is_allowed(client_id, "expensive")
        assert not limiter.is_allowed(client_id, "expensive")

        # Normal method - 5 allowed
        for _ in range(5):
            assert limiter.is_allowed(client_id, "normal")
        assert not limiter.is_allowed(client_id, "normal")

    def test_default_limit(self):
        """Test default limit for unlisted methods."""
        method_limits = {
            "limited": (1, 10),
        }
        default_limit = (3, 10)

        limiter = MethodRateLimiter(method_limits, default_limit)
        client_id = "test-client"

        # Limited method
        assert limiter.is_allowed(client_id, "limited")
        assert not limiter.is_allowed(client_id, "limited")

        # Unknown method uses default
        for _ in range(3):
            assert limiter.is_allowed(client_id, "unknown")
        assert not limiter.is_allowed(client_id, "unknown")

    def test_no_limit_for_unlisted(self):
        """Test no limit for unlisted methods without default."""
        method_limits = {
            "limited": (1, 10),
        }

        limiter = MethodRateLimiter(method_limits)
        client_id = "test-client"

        # Limited method
        assert limiter.is_allowed(client_id, "limited")
        assert not limiter.is_allowed(client_id, "limited")

        # Unknown method has no limit
        for _ in range(100):
            assert limiter.is_allowed(client_id, "unknown")
