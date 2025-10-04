"""Tests for session rename functionality."""

import json
from pathlib import Path

import pytest

from browser.backend.core.management.session_manager import SessionManager


@pytest.fixture
async def session_manager_with_session(tmp_path: Path) -> tuple[SessionManager, str, str]:
    """Create a session manager with a test session."""
    session_dir = tmp_path / "sessions"
    manager = SessionManager(session_dir=str(session_dir))
    await manager.initialize()

    # Create a test session manually
    session_id = "test-session-123"
    session_name = "original-name"
    session_path = session_dir / session_id
    session_path.mkdir(parents=True, exist_ok=True)

    session_data = {
        "id": session_id,
        "name": session_name,
        "created_at": "2025-10-04T10:00:00",
        "profile": "test-profile",
        "url": "https://example.com",
        "title": "Example",
        "cookies": [],
        "window_handles": 1,
    }

    # Save session file
    session_file = session_path / "session.json"
    with session_file.open("w") as f:
        json.dump(session_data, f, indent=2)

    # Update metadata
    manager.sessions[session_id] = {
        "name": session_name,
        "created_at": session_data["created_at"],
        "profile": session_data["profile"],
        "url": session_data["url"],
        "title": session_data["title"],
    }
    manager._save_metadata()

    return manager, session_id, session_name


@pytest.mark.asyncio
async def test_rename_session_success(session_manager_with_session: tuple[SessionManager, str, str]) -> None:
    """Test successful session rename."""
    manager, session_id, original_name = session_manager_with_session

    new_name = "new-session-name"
    renamed = manager.rename_session(session_id, new_name)

    assert renamed is True
    assert manager.sessions[session_id]["name"] == new_name

    # Verify metadata file updated
    with manager.metadata_file.open() as f:
        metadata = json.load(f)
    assert metadata[session_id]["name"] == new_name

    # Verify session file updated
    session_file = manager.session_dir / session_id / "session.json"
    with session_file.open() as f:
        session_data = json.load(f)
    assert session_data["name"] == new_name


@pytest.mark.asyncio
async def test_rename_session_not_found(session_manager_with_session: tuple[SessionManager, str, str]) -> None:
    """Test renaming non-existent session."""
    manager, _, _ = session_manager_with_session

    renamed = manager.rename_session("nonexistent-session", "new-name")

    assert renamed is False


@pytest.mark.asyncio
async def test_rename_session_persists(session_manager_with_session: tuple[SessionManager, str, str]) -> None:
    """Test renamed session persists across manager restarts."""
    manager, session_id, _ = session_manager_with_session

    new_name = "persisted-name"
    manager.rename_session(session_id, new_name)

    # Create new manager instance to load from disk
    new_manager = SessionManager(session_dir=str(manager.session_dir))
    await new_manager.initialize()

    assert new_manager.sessions[session_id]["name"] == new_name


@pytest.mark.asyncio
async def test_list_sessions_shows_renamed(session_manager_with_session: tuple[SessionManager, str, str]) -> None:
    """Test list_sessions reflects renamed session."""
    manager, session_id, _ = session_manager_with_session

    new_name = "renamed-session"
    manager.rename_session(session_id, new_name)

    sessions = await manager.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["name"] == new_name
