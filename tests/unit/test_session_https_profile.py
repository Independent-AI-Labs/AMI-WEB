"""Unit tests for HTTPS session persistence with default profile."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from browser.backend.core.browser.instance import BrowserInstance
from browser.backend.core.management.profile_manager import ProfileManager
from browser.backend.core.management.session_manager import SessionManager


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Create a temporary session directory."""
    return tmp_path / "sessions"


@pytest.fixture
def profile_dir(tmp_path: Path) -> Path:
    """Create a temporary profile directory."""
    return tmp_path / "profiles"


@pytest.fixture
def session_manager(session_dir: Path) -> SessionManager:
    """Create a SessionManager instance."""
    manager = SessionManager(session_dir=str(session_dir))
    manager.session_dir.mkdir(parents=True, exist_ok=True)
    manager.sessions = {}
    return manager


@pytest.fixture
def profile_manager(profile_dir: Path) -> ProfileManager:
    """Create a ProfileManager instance."""
    return ProfileManager(base_dir=str(profile_dir))


@pytest.fixture
def mock_instance() -> Mock:
    """Create a mock browser instance."""
    instance = Mock(spec=BrowserInstance)
    instance._profile_name = None
    instance.driver = Mock()
    instance.driver.current_url = "https://example.com/test"
    instance.driver.title = "Test Page"
    instance.driver.get_cookies = Mock(
        return_value=[
            {
                "name": "session",
                "value": "abc123",
                "secure": True,
                "domain": "example.com",
            }
        ]
    )
    instance.driver.window_handles = ["handle1"]
    instance.driver.current_window_handle = "handle1"
    return instance


@pytest.mark.asyncio
async def test_save_https_session_with_default_profile(
    session_manager: SessionManager,
    _profile_manager: ProfileManager,
    mock_instance: Mock,
    _profile_dir: Path,
) -> None:
    """Test that saving HTTPS session with default profile persists correctly."""
    # Simulate browser instance created with default profile (new behavior)
    mock_instance._profile_name = "default"
    assert "https://" in mock_instance.driver.current_url

    # Save session
    session_id = await session_manager.save_session(
        mock_instance,
        name="test_https_session",
    )

    # Check session was saved with default profile
    session_file = session_manager.session_dir / session_id / "session.json"
    assert session_file.exists()

    with session_file.open() as f:
        session_data = json.load(f)

    assert session_data["profile"] == "default"
    assert session_data["url"] == "https://example.com/test"


@pytest.mark.asyncio
async def test_save_session_no_profile(
    session_manager: SessionManager,
    mock_instance: Mock,
) -> None:
    """Test that saving session without profile saves None."""
    # Instance has no profile
    mock_instance._profile_name = None
    mock_instance.driver.current_url = "http://example.com/test"

    # Save session
    session_id = await session_manager.save_session(
        mock_instance,
        name="test_http_session",
    )

    # Check session was saved without profile
    session_file = session_manager.session_dir / session_id / "session.json"
    with session_file.open() as f:
        session_data = json.load(f)

    assert session_data["profile"] is None


@pytest.mark.asyncio
async def test_save_session_with_custom_profile(
    session_manager: SessionManager,
    mock_instance: Mock,
) -> None:
    """Test that session saves the instance's profile."""
    # Set custom profile
    mock_instance._profile_name = "my_profile"

    # Save session
    session_id = await session_manager.save_session(
        mock_instance,
        name="test_session",
    )

    # Check session uses the instance's profile
    session_file = session_manager.session_dir / session_id / "session.json"
    with session_file.open() as f:
        session_data = json.load(f)

    assert session_data["profile"] == "my_profile"


@pytest.mark.asyncio
async def test_save_session_preserves_instance_profile(
    session_manager: SessionManager,
    mock_instance: Mock,
) -> None:
    """Test that save_session preserves whatever profile the instance has."""
    # Instance has no profile
    mock_instance._profile_name = None

    # Save session
    session_id = await session_manager.save_session(
        mock_instance,
        name="test_session",
    )

    # Session should save None profile (profile assignment happens at browser creation)
    session_file = session_manager.session_dir / session_id / "session.json"
    with session_file.open() as f:
        session_data = json.load(f)

    assert session_data["profile"] is None


@pytest.mark.asyncio
async def test_save_session_preserves_cookies(
    session_manager: SessionManager,
    mock_instance: Mock,
) -> None:
    """Test that session saves secure cookies correctly."""
    # Add secure cookie
    mock_instance.driver.get_cookies = Mock(
        return_value=[
            {
                "name": "__Secure-session",
                "value": "encrypted_token",
                "secure": True,
                "httpOnly": True,
                "domain": "example.com",
                "path": "/",
            }
        ]
    )

    session_id = await session_manager.save_session(
        mock_instance,
        name="secure_session",
    )

    # Check cookies were saved
    session_file = session_manager.session_dir / session_id / "session.json"
    with session_file.open() as f:
        session_data = json.load(f)

    assert len(session_data["cookies"]) == 1
    assert session_data["cookies"][0]["name"] == "__Secure-session"
    assert session_data["cookies"][0]["secure"] is True
    assert session_data["cookies"][0]["httpOnly"] is True


@pytest.mark.asyncio
async def test_multiple_sessions_with_default_profile(
    session_manager: SessionManager,
    mock_instance: Mock,
) -> None:
    """Test that multiple sessions can use the default profile."""
    # Both instances have default profile set
    mock_instance._profile_name = "default"

    # Save first session
    session_id_1 = await session_manager.save_session(
        mock_instance,
        name="session1",
    )

    # Save second session (different instance but same profile)
    mock_instance2 = Mock(spec=BrowserInstance)
    mock_instance2._profile_name = "default"
    mock_instance2.driver = Mock()
    mock_instance2.driver.current_url = "https://another.com/page"
    mock_instance2.driver.title = "Another Page"
    mock_instance2.driver.get_cookies = Mock(return_value=[])
    mock_instance2.driver.window_handles = ["handle1"]
    mock_instance2.driver.current_window_handle = "handle1"

    session_id_2 = await session_manager.save_session(
        mock_instance2,
        name="session2",
    )

    # Both sessions should have default profile
    with (session_manager.session_dir / session_id_1 / "session.json").open() as f:
        session1_data = json.load(f)
    with (session_manager.session_dir / session_id_2 / "session.json").open() as f:
        session2_data = json.load(f)

    assert session1_data["profile"] == "default"
    assert session2_data["profile"] == "default"
