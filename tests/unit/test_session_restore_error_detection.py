"""Unit tests for session restore error detection (certificate warnings, etc.)."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.core.management.session_manager import SessionManager


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Create a temporary session directory."""
    return tmp_path / "sessions"


@pytest.fixture
def session_manager(session_dir: Path) -> SessionManager:
    """Create a SessionManager instance."""
    manager = SessionManager(session_dir=str(session_dir))
    manager.session_dir.mkdir(parents=True, exist_ok=True)
    return manager


@pytest.fixture
def mock_chrome_manager() -> Mock:
    """Create a mock ChromeManager."""
    manager = Mock(spec=ChromeManager)
    manager.get_or_create_instance = AsyncMock()
    return manager


def create_test_session(
    session_dir: Path, session_id: str, url: str, cookies: list[Any]
) -> None:
    """Helper to create a test session file."""
    session_path = session_dir / session_id
    session_path.mkdir(parents=True, exist_ok=True)

    session_data = {
        "id": session_id,
        "name": "test_session",
        "created_at": "2025-01-01T00:00:00",
        "profile": None,
        "url": url,
        "title": "Test Page",
        "cookies": cookies,
        "window_handles": 1,
    }

    with (session_path / "session.json").open("w") as f:
        json.dump(session_data, f)


@pytest.mark.asyncio
async def test_restore_detects_certificate_error_page(
    session_manager: SessionManager,
    session_dir: Path,
    mock_chrome_manager: Mock,
) -> None:
    """Test that restore detects certificate error page and skips cookie restoration."""

    # Create session with HTTPS URL and cookies
    session_id = "test-session-123"
    create_test_session(
        session_dir,
        session_id,
        "https://example.com/page",
        [{"name": "session", "value": "abc", "secure": True}],
    )

    # Load metadata
    session_manager.sessions = {
        session_id: {
            "name": "test_session",
            "created_at": "2025-01-01T00:00:00",
            "profile": None,
            "url": "https://example.com/page",
            "title": "Test Page",
        }
    }

    # Mock instance with certificate error page
    mock_instance = Mock()
    mock_instance.driver = Mock()
    mock_instance.driver.current_url = (
        "data:text/html,chromewebdata"  # Error page indicator
    )
    mock_instance.driver.page_source = "<html><body>Your connection is not private NET::ERR_CERT_AUTHORITY_INVALID</body></html>"

    mock_chrome_manager.get_or_create_instance = AsyncMock(return_value=mock_instance)

    # Restore session
    await session_manager.restore_session(session_id, mock_chrome_manager)

    # add_cookie should NOT have been called (warning logged separately)
    mock_instance.driver.add_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_restore_detects_chrome_error_url(
    session_manager: SessionManager,
    session_dir: Path,
    mock_chrome_manager: Mock,
) -> None:
    """Test that restore detects chrome-error:// URLs."""

    session_id = "test-session-456"
    create_test_session(
        session_dir,
        session_id,
        "https://example.com/page",
        [{"name": "auth", "value": "xyz", "secure": True}],
    )

    session_manager.sessions = {
        session_id: {
            "name": "test_session",
            "created_at": "2025-01-01T00:00:00",
            "profile": None,
            "url": "https://example.com/page",
            "title": "Test Page",
        }
    }

    # Mock instance on chrome-error page
    mock_instance = Mock()
    mock_instance.driver = Mock()
    mock_instance.driver.current_url = "chrome-error://chromewebdata/"
    mock_instance.driver.page_source = "<html></html>"

    mock_chrome_manager.get_or_create_instance = AsyncMock(return_value=mock_instance)

    await session_manager.restore_session(session_id, mock_chrome_manager)

    # Cookies should not be added on error page
    mock_instance.driver.add_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_restore_succeeds_on_normal_page(
    session_manager: SessionManager,
    session_dir: Path,
    mock_chrome_manager: Mock,
) -> None:
    """Test that restore works normally when page loads successfully."""

    session_id = "test-session-789"
    cookies = [
        {"name": "session", "value": "abc123", "domain": "example.com"},
        {"name": "pref", "value": "dark_mode", "domain": "example.com"},
    ]
    create_test_session(
        session_dir,
        session_id,
        "https://example.com/page",
        cookies,
    )

    session_manager.sessions = {
        session_id: {
            "name": "test_session",
            "created_at": "2025-01-01T00:00:00",
            "profile": None,
            "url": "https://example.com/page",
            "title": "Test Page",
        }
    }

    # Mock instance on successful page load
    mock_instance = Mock()
    mock_instance.driver = Mock()
    mock_instance.driver.current_url = (
        "https://example.com/"  # Successfully loaded domain root
    )
    mock_instance.driver.page_source = (
        "<html><body><h1>Example Domain</h1></body></html>"
    )

    mock_chrome_manager.get_or_create_instance = AsyncMock(return_value=mock_instance)

    await session_manager.restore_session(session_id, mock_chrome_manager)

    # Check cookies were restored
    assert mock_instance.driver.add_cookie.call_count == 2
    mock_instance.driver.add_cookie.assert_any_call(cookies[0])
    mock_instance.driver.add_cookie.assert_any_call(cookies[1])


@pytest.mark.asyncio
async def test_restore_handles_partial_cookie_failure(
    session_manager: SessionManager,
    session_dir: Path,
    mock_chrome_manager: Mock,
) -> None:
    """Test that restore handles when some cookies fail to add."""

    session_id = "test-session-partial"
    cookies = [
        {"name": "cookie1", "value": "val1"},
        {"name": "cookie2", "value": "val2"},
        {"name": "cookie3", "value": "val3"},
    ]
    create_test_session(
        session_dir,
        session_id,
        "https://example.com/page",
        cookies,
    )

    session_manager.sessions = {
        session_id: {
            "name": "test_session",
            "created_at": "2025-01-01T00:00:00",
            "profile": None,
            "url": "https://example.com/page",
            "title": "Test Page",
        }
    }

    # Mock instance where second cookie fails
    mock_instance = Mock()
    mock_instance.driver = Mock()
    mock_instance.driver.current_url = "https://example.com/"
    mock_instance.driver.page_source = "<html><body>Normal page</body></html>"

    def add_cookie_side_effect(cookie: dict[str, Any]) -> None:
        if cookie["name"] == "cookie2":
            raise Exception("Cookie domain mismatch")

    mock_instance.driver.add_cookie = Mock(side_effect=add_cookie_side_effect)

    mock_chrome_manager.get_or_create_instance = AsyncMock(return_value=mock_instance)

    await session_manager.restore_session(session_id, mock_chrome_manager)

    # Check that add_cookie was called 3 times but one failed
    assert mock_instance.driver.add_cookie.call_count == 3


@pytest.mark.asyncio
async def test_restore_error_detection_case_insensitive(
    session_manager: SessionManager,
    session_dir: Path,
    mock_chrome_manager: Mock,
) -> None:
    """Test that error detection is case-insensitive."""
    session_id = "test-case"
    create_test_session(
        session_dir,
        session_id,
        "https://example.com/page",
        [{"name": "test", "value": "val"}],
    )

    session_manager.sessions = {
        session_id: {
            "name": "test",
            "created_at": "2025-01-01",
            "profile": None,
            "url": "https://example.com",
            "title": "Test",
        }
    }

    # Mock instance with uppercase error text
    mock_instance = Mock()
    mock_instance.driver = Mock()
    mock_instance.driver.current_url = "https://example.com/"
    mock_instance.driver.page_source = (
        "<html>YOUR CONNECTION IS NOT PRIVATE</html>"  # Uppercase
    )

    mock_chrome_manager.get_or_create_instance = AsyncMock(return_value=mock_instance)

    await session_manager.restore_session(session_id, mock_chrome_manager)

    # Should still detect error (case-insensitive check)
    mock_instance.driver.add_cookie.assert_not_called()
