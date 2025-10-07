"""Shared fixtures for browser integration tests."""

import os

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"
