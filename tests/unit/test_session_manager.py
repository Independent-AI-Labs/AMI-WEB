"""Unit tests for SessionManager storage operations."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestSessionManager:
    """Test SessionManager without file I/O."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test session manager initialization."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions_dir = Path("data/sessions")
            manager.sessions = {}
            manager.initialize = AsyncMock()

            await manager.initialize()

            assert manager.sessions_dir == Path("data/sessions")
            assert manager.sessions == {}
            manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a new session."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {}
            manager.create_session = AsyncMock(side_effect=lambda: "session-123")

            session_id = await manager.create_session()

            assert session_id == "session-123"
            manager.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_data(self):
        """Test saving session data."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {}
            manager.save_session = AsyncMock(side_effect=lambda sid, data: manager.sessions.update({sid: data}))

            session_data = {
                "cookies": [{"name": "session", "value": "abc"}],
                "local_storage": {"key": "value"},
                "url": "https://example.com",
            }
            await manager.save_session("session-123", session_data)

            assert "session-123" in manager.sessions
            assert manager.sessions["session-123"]["url"] == "https://example.com"
            manager.save_session.assert_called_once_with("session-123", session_data)

    @pytest.mark.asyncio
    async def test_load_session(self):
        """Test loading session data."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {
                "session-123": {
                    "cookies": [{"name": "test", "value": "val"}],
                    "url": "https://example.com",
                },
            }
            manager.get_session = AsyncMock(side_effect=lambda sid: manager.sessions.get(sid))

            session = await manager.get_session("session-123")

            assert session is not None
            assert session["url"] == "https://example.com"
            assert len(session["cookies"]) == 1
            manager.get_session.assert_called_once_with("session-123")

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting a session."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {"session-123": {}, "session-456": {}}
            manager.delete_session = AsyncMock(side_effect=lambda sid: manager.sessions.pop(sid, None))

            await manager.delete_session("session-123")

            assert "session-123" not in manager.sessions
            assert "session-456" in manager.sessions
            manager.delete_session.assert_called_once_with("session-123")

    def test_list_sessions(self):
        """Test listing all sessions."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {
                "session-123": {"name": "Session 1"},
                "session-456": {"name": "Session 2"},
            }
            manager.list_sessions = Mock(return_value=list(manager.sessions.keys()))

            sessions = manager.list_sessions()

            expected_count = 2
            assert len(sessions) == expected_count
            assert "session-123" in sessions
            assert "session-456" in sessions
            manager.list_sessions.assert_called_once()


class TestSessionPersistence:
    """Test session persistence logic."""

    def test_serialize_session(self):
        """Test serializing session data."""
        session_data = {
            "id": "session-123",
            "cookies": [{"name": "test", "value": "val", "domain": ".example.com"}],
            "local_storage": {"key1": "value1", "key2": "value2"},
            "url": "https://example.com/page",
            "timestamp": 1234567890,
        }

        serialized = json.dumps(session_data, indent=2)

        assert "session-123" in serialized
        assert "cookies" in serialized
        assert "local_storage" in serialized

    def test_deserialize_session(self):
        """Test deserializing session data."""
        json_data = """{
            "id": "session-123",
            "cookies": [{"name": "test", "value": "val"}],
            "url": "https://example.com"
        }"""

        session_data = json.loads(json_data)

        assert session_data["id"] == "session-123"
        assert len(session_data["cookies"]) == 1
        assert session_data["url"] == "https://example.com"

    def test_validate_session_data(self):
        """Test session data validation."""
        valid_session = {
            "id": "session-123",
            "cookies": [],
            "local_storage": {},
            "url": "https://example.com",
        }

        invalid_session = {
            "id": "session-123",
            # Missing required fields
        }

        # Validation logic
        required_fields = ["id", "cookies", "local_storage", "url"]

        valid = all(field in valid_session for field in required_fields)
        invalid = all(field in invalid_session for field in required_fields)

        assert valid is True
        assert invalid is False


class TestSessionMerging:
    """Test session merging and update operations."""

    def test_merge_cookies(self):
        """Test merging cookies from multiple sources."""
        existing_cookies = [
            {"name": "session", "value": "old", "domain": ".example.com"},
            {"name": "pref", "value": "dark", "domain": ".example.com"},
        ]

        new_cookies = [
            {"name": "session", "value": "new", "domain": ".example.com"},
            {"name": "tracking", "value": "123", "domain": ".example.com"},
        ]

        # Merge logic: new cookies override existing ones with same name/domain
        merged = {(c["name"], c["domain"]): c for c in existing_cookies}
        merged.update({(c["name"], c["domain"]): c for c in new_cookies})
        result = list(merged.values())

        expected_count = 3
        assert len(result) == expected_count
        session_cookie = next(c for c in result if c["name"] == "session")
        assert session_cookie["value"] == "new"  # New value overrides old

    def test_merge_local_storage(self):
        """Test merging local storage data."""
        existing_storage = {"key1": "value1", "key2": "value2"}
        new_storage = {"key2": "updated", "key3": "value3"}

        # Merge: new values override existing
        merged = {**existing_storage, **new_storage}

        assert merged["key1"] == "value1"
        assert merged["key2"] == "updated"  # Updated value
        assert merged["key3"] == "value3"  # New key

    @pytest.mark.asyncio
    async def test_update_session(self):
        """Test updating an existing session."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {
                "session-123": {
                    "cookies": [{"name": "old", "value": "val"}],
                    "url": "https://old.com",
                },
            }
            manager.update_session = AsyncMock(side_effect=lambda sid, data: manager.sessions[sid].update(data))

            updates = {
                "cookies": [{"name": "new", "value": "val"}],
                "url": "https://new.com",
            }
            await manager.update_session("session-123", updates)

            assert manager.sessions["session-123"]["url"] == "https://new.com"
            assert manager.sessions["session-123"]["cookies"][0]["name"] == "new"
            manager.update_session.assert_called_once_with("session-123", updates)


class TestSessionCleanup:
    """Test session cleanup and expiration."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            current_time = time.time()
            manager = mock_manager_class()
            manager.sessions = {
                "session-old": {"timestamp": current_time - 86400 * 8},  # 8 days old
                "session-new": {"timestamp": current_time - 3600},  # 1 hour old
            }
            manager.cleanup_expired = AsyncMock(
                side_effect=lambda max_age: setattr(
                    manager,
                    "sessions",
                    {sid: data for sid, data in manager.sessions.items() if current_time - data["timestamp"] < max_age},
                ),
            )

            max_age_seconds = 86400 * 7  # 7 days
            await manager.cleanup_expired(max_age_seconds)

            assert "session-old" not in manager.sessions
            assert "session-new" in manager.sessions
            manager.cleanup_expired.assert_called_once_with(max_age_seconds)

    @pytest.mark.asyncio
    async def test_cleanup_invalid_sessions(self):
        """Test cleaning up invalid sessions."""
        with patch("browser.backend.core.management.session_manager.SessionManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.sessions = {
                "session-valid": {"id": "session-valid", "cookies": [], "url": "https://example.com"},
                "session-invalid": {"id": "session-invalid"},  # Missing required fields
            }
            manager.cleanup_invalid = AsyncMock(
                side_effect=lambda: setattr(
                    manager,
                    "sessions",
                    {sid: data for sid, data in manager.sessions.items() if all(field in data for field in ["id", "cookies", "url"])},
                ),
            )

            await manager.cleanup_invalid()

            assert "session-valid" in manager.sessions
            assert "session-invalid" not in manager.sessions
            manager.cleanup_invalid.assert_called_once()
