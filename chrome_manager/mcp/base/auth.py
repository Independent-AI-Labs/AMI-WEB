"""Authentication middleware for MCP servers."""

import hashlib
import hmac
import secrets
import time
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate with given credentials.

        Args:
            credentials: Authentication credentials

        Returns:
            True if authenticated, False otherwise
        """


class TokenAuthProvider(AuthProvider):
    """Token-based authentication provider."""

    def __init__(self, valid_tokens: list[str]):
        """Initialize with valid tokens.

        Args:
            valid_tokens: List of valid authentication tokens
        """
        self.valid_tokens = set(valid_tokens)

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate using token.

        Args:
            credentials: Should contain 'token' key

        Returns:
            True if token is valid
        """
        token = credentials.get("token")
        return token in self.valid_tokens


class HMACAuthProvider(AuthProvider):
    """HMAC-based authentication provider."""

    def __init__(self, secret_key: str, max_age: int = 300):
        """Initialize with secret key.

        Args:
            secret_key: Secret key for HMAC
            max_age: Maximum age of timestamp in seconds (default: 5 minutes)
        """
        self.secret_key = secret_key.encode()
        self.max_age = max_age

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate using HMAC signature.

        Args:
            credentials: Should contain 'signature', 'timestamp', and 'message'

        Returns:
            True if signature is valid and not expired
        """
        signature = credentials.get("signature")
        timestamp = credentials.get("timestamp")
        message = credentials.get("message", "")

        if not all([signature, timestamp]):
            return False

        try:
            # Check timestamp age
            current_time = time.time()
            if abs(current_time - float(timestamp)) > self.max_age:
                logger.warning("Authentication failed: timestamp too old")
                return False

            # Verify signature
            expected_signature = hmac.new(self.secret_key, f"{message}{timestamp}".encode(), hashlib.sha256).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, TypeError) as e:
            logger.error(f"Authentication error: {e}")
            return False


class AuthenticationMiddleware:
    """Middleware for handling authentication."""

    def __init__(self, tokens: list[str] | None = None, provider: AuthProvider | None = None):
        """Initialize authentication middleware.

        Args:
            tokens: List of valid tokens (creates TokenAuthProvider)
            provider: Custom auth provider (overrides tokens)
        """
        if provider:
            self.auth_provider = provider
        elif tokens:
            self.auth_provider = TokenAuthProvider(tokens)
        else:
            raise ValueError("Either tokens or provider must be specified")

    async def process(self, context: dict[str, Any], request: dict) -> dict | None:
        """Process authentication for a request.

        Args:
            context: Connection context
            request: The request data

        Returns:
            Error response if authentication fails, None otherwise
        """
        # Skip authentication for already authenticated connections
        if context.get("authenticated"):
            return None

        method = request.get("method")

        # Allow certain methods without authentication
        unauthenticated_methods = ["initialize", "authenticate"]
        if method in unauthenticated_methods:
            return None

        # Check for authentication method
        if method == "authenticate":
            return await self._handle_authenticate(context, request)

        # Require authentication for all other methods
        if not context.get("authenticated"):
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Authentication required"}, "id": request.get("id")}

        return None

    async def _handle_authenticate(self, context: dict[str, Any], request: dict) -> dict:
        """Handle authentication request.

        Args:
            context: Connection context
            request: Authentication request

        Returns:
            Response with authentication result
        """
        params = request.get("params", {})
        credentials = params.get("credentials", {})

        # Attempt authentication
        authenticated = await self.auth_provider.authenticate(credentials)

        if authenticated:
            context["authenticated"] = True
            logger.info(f"Client {context['client_addr']} authenticated successfully")
            return {"jsonrpc": "2.0", "result": {"status": "authenticated"}, "id": request.get("id")}

        logger.warning(f"Authentication failed for client {context['client_addr']}")
        return {"jsonrpc": "2.0", "error": {"code": -32002, "message": "Authentication failed"}, "id": request.get("id")}


def generate_token(length: int = 32) -> str:
    """Generate a secure random token.

    Args:
        length: Token length in bytes (default: 32)

    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(length)
