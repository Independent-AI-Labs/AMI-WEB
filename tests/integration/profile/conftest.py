"""Shared fixtures for profile management tests."""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from loguru import logger

from browser.backend.core.management.manager import ChromeManager

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"


@pytest_asyncio.fixture(scope="module")
async def profile_test_manager() -> AsyncIterator[ChromeManager]:
    """Manager configured for profile tests with isolated directories."""
    manager = ChromeManager(
        config_file="config.test.yaml",
        config_overrides={
            "backend.storage.profiles_dir": "data/test_profiles_profile_tests",
            "backend.storage.session_dir": "data/test_sessions_profile_tests",
        },
    )
    await manager.initialize()
    logger.info("Created profile test manager")

    yield manager

    await manager.shutdown()
    logger.info("Shutdown profile test manager")
