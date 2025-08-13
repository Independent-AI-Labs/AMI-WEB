"""Unit tests for MCP authentication."""

import asyncio
import hashlib
import hmac
import time

import pytest

from backend.mcp.base.auth import (
    AuthenticationMiddleware,
    HMACAuthProvider,
    TokenAuthProvider,
    generate_token,
)


class TestTokenAuthProvider:
    """Test token-based authentication."""

    def test_valid_token(self):
        """Test authentication with valid token."""
        tokens = ["token1", "token2", "token3"]
        provider = TokenAuthProvider(tokens)

        # Test valid token
        assert asyncio.run(provider.authenticate({"token": "token1"}))
        assert asyncio.run(provider.authenticate({"token": "token2"}))
        assert asyncio.run(provider.authenticate({"token": "token3"}))

    def test_invalid_token(self):
        """Test authentication with invalid token."""
        tokens = ["token1", "token2"]
        provider = TokenAuthProvider(tokens)

        # Test invalid token
        assert not asyncio.run(provider.authenticate({"token": "invalid"}))
        assert not asyncio.run(provider.authenticate({"token": ""}))
        assert not asyncio.run(provider.authenticate({}))

    def test_empty_tokens(self):
        """Test with no valid tokens."""
        provider = TokenAuthProvider([])

        # Should reject everything
        assert not asyncio.run(provider.authenticate({"token": "any"}))


class TestHMACAuthProvider:
    """Test HMAC-based authentication."""

    def test_valid_signature(self):
        """Test authentication with valid HMAC signature."""
        secret = "test-secret"  # noqa: S105
        provider = HMACAuthProvider(secret)

        # Generate valid signature
        timestamp = str(time.time())
        message = "test-message"
        signature = hmac.new(secret.encode(), f"{message}{timestamp}".encode(), hashlib.sha256).hexdigest()

        credentials = {"signature": signature, "timestamp": timestamp, "message": message}

        assert asyncio.run(provider.authenticate(credentials))

    def test_invalid_signature(self):
        """Test authentication with invalid HMAC signature."""
        provider = HMACAuthProvider("test-secret")

        timestamp = str(time.time())
        credentials = {"signature": "invalid-signature", "timestamp": timestamp, "message": "test-message"}

        assert not asyncio.run(provider.authenticate(credentials))

    def test_expired_timestamp(self):
        """Test authentication with expired timestamp."""
        secret = "test-secret"  # noqa: S105
        provider = HMACAuthProvider(secret, max_age=5)  # 5 seconds

        # Generate signature with old timestamp
        old_timestamp = str(time.time() - 10)  # 10 seconds ago
        message = "test-message"
        signature = hmac.new(secret.encode(), f"{message}{old_timestamp}".encode(), hashlib.sha256).hexdigest()

        credentials = {"signature": signature, "timestamp": old_timestamp, "message": message}

        assert not asyncio.run(provider.authenticate(credentials))


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_blocked(self):
        """Test that unauthenticated requests are blocked."""
        middleware = AuthenticationMiddleware(["valid-token"])

        context = {"authenticated": False, "client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        result = await middleware.process(context, request)

        assert result is not None
        assert "error" in result
        auth_required_code = -32001
        assert result["error"]["code"] == auth_required_code

    @pytest.mark.asyncio
    async def test_authenticated_request_allowed(self):
        """Test that authenticated requests are allowed."""
        middleware = AuthenticationMiddleware(["valid-token"])

        context = {"authenticated": True, "client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        result = await middleware.process(context, request)

        assert result is None  # Request allowed to proceed

    @pytest.mark.asyncio
    async def test_authenticate_method(self):
        """Test authentication method."""
        middleware = AuthenticationMiddleware(["valid-token"])

        context = {"authenticated": False, "client_addr": ("127.0.0.1", 12345)}

        # Valid authentication
        request = {"jsonrpc": "2.0", "method": "authenticate", "params": {"credentials": {"token": "valid-token"}}, "id": 1}

        result = await middleware.process(context, request)

        # Should return None to let handler process it
        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_allowed_without_auth(self):
        """Test that initialize method is allowed without authentication."""
        middleware = AuthenticationMiddleware(["valid-token"])

        context = {"authenticated": False, "client_addr": ("127.0.0.1", 12345)}

        request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

        result = await middleware.process(context, request)

        assert result is None  # Allowed without auth


def test_generate_token():
    """Test token generation."""
    # Generate tokens
    token1 = generate_token()
    token2 = generate_token()

    # Should be different
    assert token1 != token2

    # Should be correct length (32 bytes = 64 hex chars)
    expected_length = 64
    assert len(token1) == expected_length
    assert len(token2) == expected_length

    # Should be hex strings
    try:
        int(token1, 16)
        int(token2, 16)
    except ValueError:
        pytest.fail("Tokens should be valid hex strings")
