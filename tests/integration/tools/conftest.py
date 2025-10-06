"""Shared fixtures for MCP tool tests."""
import os

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"

# Tool tests use shared session_manager and browser_instance fixtures
