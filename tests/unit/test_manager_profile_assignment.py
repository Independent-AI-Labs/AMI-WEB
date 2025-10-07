"""Unit tests for ChromeManager profile assignment behavior."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from browser.backend.core.management.manager import ChromeManager


@pytest.fixture
def manager(tmp_path: Path) -> ChromeManager:
    """Create a ChromeManager with temp directories."""
    config_overrides = {
        "backend.storage.profiles_dir": str(tmp_path / "profiles"),
        "backend.storage.session_dir": str(tmp_path / "sessions"),
        "backend.storage.screenshot_dir": str(tmp_path / "screenshots"),
        "backend.storage.download_dir": str(tmp_path / "downloads"),
    }

    return ChromeManager(config_file=None, config_overrides=config_overrides)


@pytest.mark.asyncio
async def test_no_profile_uses_temp_profile(manager: ChromeManager) -> None:
    """Test that browser creation without profile uses temp profile (no persistence)."""
    await manager.initialize()

    # Mock BrowserInstance to avoid actual browser launch
    with patch(
        "browser.backend.core.management.manager.BrowserInstance"
    ) as mock_instance_cls:
        mock_instance = Mock()
        mock_instance.id = "test-instance"
        mock_instance._profile_name = None  # No profile (temp)
        mock_instance.driver = Mock()
        mock_instance_cls.return_value = mock_instance
        mock_instance.launch = AsyncMock()

        # Create instance without profile
        await manager.get_or_create_instance(
            headless=True,
            profile=None,  # No profile specified
            use_pool=False,
        )

        # Check that launch was called with None (temp profile)
        mock_instance.launch.assert_called_once()
        call_kwargs = mock_instance.launch.call_args.kwargs
        assert call_kwargs["profile"] is None


@pytest.mark.asyncio
async def test_explicit_profile_uses_that_profile(manager: ChromeManager) -> None:
    """Test that explicitly specified profile is used."""
    await manager.initialize()

    with patch(
        "browser.backend.core.management.manager.BrowserInstance"
    ) as mock_instance_cls:
        mock_instance = Mock()
        mock_instance.id = "test-instance"
        mock_instance._profile_name = "custom"
        mock_instance.driver = Mock()
        mock_instance_cls.return_value = mock_instance
        mock_instance.launch = AsyncMock()

        # Create instance with explicit profile
        await manager.get_or_create_instance(
            headless=True,
            profile="custom",
            use_pool=False,
        )

        # Check that launch was called with custom profile
        mock_instance.launch.assert_called_once()
        call_kwargs = mock_instance.launch.call_args.kwargs
        assert call_kwargs["profile"] == "custom"


@pytest.mark.asyncio
async def test_profile_disables_pooling(manager: ChromeManager) -> None:
    """Test that specifying a profile disables pool usage."""
    await manager.initialize()

    with patch(
        "browser.backend.core.management.manager.BrowserInstance"
    ) as mock_instance_cls:
        mock_instance = Mock()
        mock_instance.id = "test-instance"
        mock_instance._profile_name = "test-profile"
        mock_instance.driver = Mock()
        mock_instance_cls.return_value = mock_instance
        mock_instance.launch = AsyncMock()

        # Create instance with profile AND use_pool=True
        # Should ignore use_pool and create standalone
        instance = await manager.get_or_create_instance(
            headless=True,
            profile="test-profile",
            use_pool=True,  # Requested pool but has profile
        )

        # Should have created standalone instance
        assert instance.id in manager._standalone_instances
        mock_instance.launch.assert_called_once()


@pytest.mark.asyncio
async def test_no_profile_with_pool_uses_pool(manager: ChromeManager) -> None:
    """Test that no profile + pool request → uses pool normally."""
    await manager.initialize()

    # Mock the pool to return an instance
    with patch.object(manager.pool, "acquire_browser") as mock_acquire:
        mock_instance = Mock()
        mock_instance.id = "pooled-instance"
        mock_instance._profile_name = None
        mock_instance.driver = Mock()
        mock_instance.driver.session_id = "valid-session"
        mock_acquire.return_value = mock_instance

        # Create instance with pool requested and no profile
        instance = await manager.get_or_create_instance(
            headless=True,
            profile=None,
            use_pool=True,
        )

        # Should use pool (no profile means pool is allowed)
        mock_acquire.assert_called_once()
        assert instance.id == "pooled-instance"
