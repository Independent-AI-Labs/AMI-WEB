"""Shared fixtures for session persistence tests."""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from loguru import logger

from browser.backend.core.management.manager import ChromeManager

# Test configuration
HEADLESS = os.environ.get("TEST_HEADLESS", "true").lower() == "true"


@pytest_asyncio.fixture(scope="module")
async def session_test_manager() -> AsyncIterator[ChromeManager]:
    """Manager configured for session tests with isolated directories."""
    manager = ChromeManager(
        config_file="config.test.yaml",
        config_overrides={
            "backend.storage.session_dir": "data/test_sessions_session_tests",
            "backend.storage.profiles_dir": "data/test_profiles_session_tests",
        },
    )
    await manager.initialize()
    logger.info("Created session test manager")

    yield manager

    await manager.shutdown()
    logger.info("Shutdown session test manager")
