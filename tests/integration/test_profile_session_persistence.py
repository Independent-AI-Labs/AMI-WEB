"""Integration tests for profile-based session persistence."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from browser.backend.core.browser.instance import BrowserInstance
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
async def test_session_save_and_restore_preserves_profile(manager: ChromeManager) -> None:
    """Test that saving and restoring a session preserves the profile."""
    await manager.initialize()

    with patch("browser.backend.core.management.manager.BrowserInstance") as mock_instance_cls:
        # Create mock instance with explicit default profile
        mock_instance = Mock(spec=BrowserInstance)
        mock_instance.id = "test-instance-123"
        mock_instance._profile_name = "default"
        mock_instance.driver = Mock()
        mock_instance.driver.current_url = "https://example.com/page"
        mock_instance.driver.title = "Example Page"
        mock_instance.driver.get_cookies = Mock(return_value=[{"name": "session", "value": "abc123", "secure": True, "domain": "example.com"}])
        mock_instance.driver.window_handles = ["handle1"]
        mock_instance.launch = AsyncMock()

        mock_instance_cls.return_value = mock_instance

        # Create instance with explicit default profile
        instance = await manager.get_or_create_instance(headless=True, profile="default", use_pool=False)
        assert instance._profile_name == "default"

        # Save session
        session_id = await manager.session_manager.save_session(instance, "test_session")

        # Verify session was saved with default profile
        session_dir = manager.config.get("backend.storage.session_dir", "./data/sessions")
        session_file = Path(session_dir) / session_id / "session.json"
        assert session_file.exists()

        import json

        with session_file.open() as f:
            session_data = json.load(f)

        assert session_data["profile"] == "default"
        assert session_data["url"] == "https://example.com/page"
        assert len(session_data["cookies"]) == 1

        # Terminate instance
        await manager.terminate_instance(instance.id)

        # Create new mock for restored instance
        restored_instance = Mock(spec=BrowserInstance)
        restored_instance.id = "restored-instance-456"
        restored_instance._profile_name = "default"
        restored_instance.driver = Mock()
        restored_instance.driver.current_url = "https://example.com/"
        restored_instance.driver.page_source = "<html><body>Normal page</body></html>"
        restored_instance.driver.add_cookie = Mock()
        restored_instance.driver.get = Mock()
        restored_instance.launch = AsyncMock()

        mock_instance_cls.return_value = restored_instance

        # Restore session
        restored = await manager.session_manager.restore_session(session_id, manager, profile_override=None)

        # Verify restored instance uses default profile
        assert restored._profile_name == "default"

        # Verify cookies were attempted to be restored
        assert restored.driver.add_cookie.call_count > 0  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_multiple_sessions_share_default_profile(manager: ChromeManager) -> None:
    """Test that multiple sessions can explicitly use the same default profile."""
    await manager.initialize()

    with patch("browser.backend.core.management.manager.BrowserInstance") as mock_instance_cls:
        # First instance
        instance1 = Mock(spec=BrowserInstance)
        instance1.id = "instance-1"
        instance1._profile_name = "default"
        instance1.driver = Mock()
        instance1.driver.current_url = "https://site1.com/"
        instance1.driver.title = "Site 1"
        instance1.driver.get_cookies = Mock(return_value=[])
        instance1.driver.window_handles = ["h1"]
        instance1.launch = AsyncMock()

        # Second instance
        instance2 = Mock(spec=BrowserInstance)
        instance2.id = "instance-2"
        instance2._profile_name = "default"
        instance2.driver = Mock()
        instance2.driver.current_url = "https://site2.com/"
        instance2.driver.title = "Site 2"
        instance2.driver.get_cookies = Mock(return_value=[])
        instance2.driver.window_handles = ["h2"]
        instance2.launch = AsyncMock()

        mock_instance_cls.side_effect = [instance1, instance2]

        # Create first session with explicit default profile
        inst1 = await manager.get_or_create_instance(headless=True, profile="default", use_pool=False)
        session1_id = await manager.session_manager.save_session(inst1, "session1")
        await manager.terminate_instance(inst1.id)

        # Create second session with explicit default profile
        inst2 = await manager.get_or_create_instance(headless=True, profile="default", use_pool=False)
        session2_id = await manager.session_manager.save_session(inst2, "session2")
        await manager.terminate_instance(inst2.id)

        # Both sessions should use default profile
        import json

        session_dir = manager.config.get("backend.storage.session_dir", "./data/sessions")
        with (Path(session_dir) / session1_id / "session.json").open() as f:
            s1_data = json.load(f)
        with (Path(session_dir) / session2_id / "session.json").open() as f:
            s2_data = json.load(f)

        assert s1_data["profile"] == "default"
        assert s2_data["profile"] == "default"


@pytest.mark.asyncio
async def test_custom_profile_persists_across_sessions(manager: ChromeManager) -> None:
    """Test that custom profile persists across save/restore."""
    await manager.initialize()

    with patch("browser.backend.core.management.manager.BrowserInstance") as mock_instance_cls:
        # Create instance with custom profile
        instance = Mock(spec=BrowserInstance)
        instance.id = "custom-instance"
        instance._profile_name = "my_custom_profile"
        instance.driver = Mock()
        instance.driver.current_url = "https://example.com/"
        instance.driver.title = "Example"
        instance.driver.get_cookies = Mock(return_value=[])
        instance.driver.window_handles = ["h1"]
        instance.launch = AsyncMock()

        mock_instance_cls.return_value = instance

        # Create instance with custom profile
        inst = await manager.get_or_create_instance(headless=True, profile="my_custom_profile", use_pool=False)

        # Save session
        session_id = await manager.session_manager.save_session(inst, "custom_session")

        # Verify session saved with custom profile
        import json

        session_dir = manager.config.get("backend.storage.session_dir", "./data/sessions")
        with (Path(session_dir) / session_id / "session.json").open() as f:
            session_data = json.load(f)

        assert session_data["profile"] == "my_custom_profile"
