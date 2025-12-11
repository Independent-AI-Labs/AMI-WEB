"""Shared fixtures for MCP server and tool tests."""

import os


# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"

# MCP tests use shared session_manager fixture from tests/conftest.py
# and browser_instance fixture for MCP tool testing
