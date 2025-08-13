"""Configuration for MCP server."""

import os
from pathlib import Path

from chrome_manager.mcp.base.auth import generate_token


class MCPConfig:
    """MCP server configuration."""

    # Server settings
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 8765
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB

    # Authentication settings
    AUTH_ENABLED = os.environ.get("MCP_AUTH_ENABLED", "false").lower() == "true"
    AUTH_TOKENS_FILE = Path.home() / ".chrome_manager" / "mcp_tokens.txt"

    # Rate limiting settings
    RATE_LIMIT_ENABLED = os.environ.get("MCP_RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.environ.get("MCP_RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.environ.get("MCP_RATE_LIMIT_WINDOW", "60"))

    # Method-specific rate limits
    METHOD_RATE_LIMITS = {
        "browser_launch": (10, 60),  # 10 launches per minute
        "browser_screenshot": (30, 60),  # 30 screenshots per minute
        "tools/call": (100, 60),  # 100 tool calls per minute
    }

    @classmethod
    def get_config(cls) -> dict:
        """Get MCP server configuration.

        Returns:
            Configuration dictionary
        """
        config = {
            "server_host": os.environ.get("MCP_HOST", cls.DEFAULT_HOST),
            "server_port": int(os.environ.get("MCP_PORT", str(cls.DEFAULT_PORT))),
            "max_message_size": cls.MAX_MESSAGE_SIZE,
            "auth_enabled": cls.AUTH_ENABLED,
            "rate_limit_enabled": cls.RATE_LIMIT_ENABLED,
            "rate_limit_requests": cls.RATE_LIMIT_REQUESTS,
            "rate_limit_window": cls.RATE_LIMIT_WINDOW,
        }

        # Load auth tokens if authentication is enabled
        if cls.AUTH_ENABLED:
            config["auth_tokens"] = cls._load_auth_tokens()

        return config

    @classmethod
    def _load_auth_tokens(cls) -> list[str]:
        """Load authentication tokens from file.

        Returns:
            List of valid tokens
        """
        if not cls.AUTH_TOKENS_FILE.exists():
            # Create default token file
            cls._create_default_tokens()

        with cls.AUTH_TOKENS_FILE.open() as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    @classmethod
    def _create_default_tokens(cls):
        """Create default authentication tokens file."""
        cls.AUTH_TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Generate some default tokens
        tokens = [
            "# MCP Authentication Tokens",
            "# One token per line, lines starting with # are ignored",
            "",
            generate_token(),  # Generate a random token
            generate_token(),  # Generate another random token
        ]

        with cls.AUTH_TOKENS_FILE.open("w") as f:
            f.write("\n".join(tokens))

        # Set appropriate permissions (Unix-like systems)
        if hasattr(os, "chmod"):
            cls.AUTH_TOKENS_FILE.chmod(0o600)

    @classmethod
    def add_token(cls, token: str | None = None) -> str:
        """Add a new authentication token.

        Args:
            token: Token to add (generates one if not provided)

        Returns:
            The added token
        """
        if token is None:
            token = generate_token()

        # Ensure file exists
        if not cls.AUTH_TOKENS_FILE.exists():
            cls._create_default_tokens()

        # Append token
        with cls.AUTH_TOKENS_FILE.open("a") as f:
            f.write(f"\n{token}")

        return token

    @classmethod
    def remove_token(cls, token: str) -> bool:
        """Remove an authentication token.

        Args:
            token: Token to remove

        Returns:
            True if token was removed
        """
        if not cls.AUTH_TOKENS_FILE.exists():
            return False

        # Read all tokens
        with cls.AUTH_TOKENS_FILE.open() as f:
            lines = f.readlines()

        # Filter out the token
        new_lines = [line for line in lines if line.strip() != token]

        if len(new_lines) == len(lines):
            return False  # Token not found

        # Write back
        with cls.AUTH_TOKENS_FILE.open("w") as f:
            f.writelines(new_lines)

        return True
