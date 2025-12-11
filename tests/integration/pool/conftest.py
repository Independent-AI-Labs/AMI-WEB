"""Shared fixtures for browser pool tests."""

import os


# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"

# Pool tests use shared session_manager fixture from tests/conftest.py
