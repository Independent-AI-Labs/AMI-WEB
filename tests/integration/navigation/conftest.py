"""Shared fixtures for browser navigation tests."""

import os


# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"

# Navigation tests use shared session_manager fixture from tests/conftest.py
# and browser_instance fixture for actual navigation tests
