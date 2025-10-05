"""Unit tests for browser_session_tool facade with session persistence."""

from unittest.mock import AsyncMock, Mock

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.facade.session import browser_session_tool


class TestSessionFacadePersistence:
    """Test browser_session_tool session persistence actions."""

    @pytest.mark.asyncio
    async def test_save_session_success(self) -> None:
        """Test saving a session successfully."""
        # Mock manager and instance
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-123"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(return_value="session-abc")
        manager.profile_manager = Mock()

        response = await browser_session_tool(
            manager=manager,
            action="save",
            instance_id="inst-123",
            session_name="my_session",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["session_id"] == "session-abc"
        assert "saved" in response.data["message"].lower()
        manager.get_instance.assert_called_once_with("inst-123")
        manager.session_manager.save_session.assert_called_once_with(instance, "my_session", profile_override=None)

    @pytest.mark.asyncio
    async def test_save_session_no_instance_id(self) -> None:
        """Test save action fails without instance_id."""
        manager = Mock(spec=ChromeManager)

        response = await browser_session_tool(
            manager=manager,
            action="save",
        )

        assert response.success is False
        assert response.error is not None
        assert "instance_id required" in response.error

    @pytest.mark.asyncio
    async def test_save_session_instance_not_found(self) -> None:
        """Test save action fails when instance not found."""
        manager = Mock(spec=ChromeManager)
        manager.get_instance = AsyncMock(return_value=None)

        response = await browser_session_tool(
            manager=manager,
            action="save",
            instance_id="nonexistent",
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_restore_session_success(self) -> None:
        """Test restoring a session successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        instance = Mock()
        instance.id = "inst-restored"

        manager.session_manager = Mock()
        manager.session_manager.restore_session = AsyncMock(return_value=instance)

        response = await browser_session_tool(
            manager=manager,
            action="restore",
            session_id="session-abc",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["instance_id"] == "inst-restored"
        assert response.data["session_id"] == "session-abc"
        assert "restored" in response.data["message"].lower()
        manager.session_manager.restore_session.assert_called_once_with("session-abc", manager, profile_override=None, headless=True, kill_orphaned=False)

    @pytest.mark.asyncio
    async def test_restore_session_no_session_id(self) -> None:
        """Test restore action fails without session_id."""
        manager = Mock(spec=ChromeManager)

        response = await browser_session_tool(
            manager=manager,
            action="restore",
        )

        assert response.success is False
        assert response.error is not None
        assert "session_id required" in response.error

    @pytest.mark.asyncio
    async def test_list_sessions_success(self) -> None:
        """Test listing sessions successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        sessions = [
            {"id": "session-1", "name": "Session 1", "created_at": "2024-01-01"},
            {"id": "session-2", "name": "Session 2", "created_at": "2024-01-02"},
        ]

        manager.session_manager = Mock()
        manager.session_manager.list_sessions = AsyncMock(return_value=sessions)

        response = await browser_session_tool(
            manager=manager,
            action="list_sessions",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["count"] == 2
        assert len(response.data["sessions"]) == 2
        assert response.data["sessions"][0]["id"] == "session-1"
        manager.session_manager.list_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self) -> None:
        """Test listing sessions when none exist."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.session_manager = Mock()
        manager.session_manager.list_sessions = AsyncMock(return_value=[])

        response = await browser_session_tool(
            manager=manager,
            action="list_sessions",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["count"] == 0
        assert response.data["sessions"] == []

    @pytest.mark.asyncio
    async def test_delete_session_success(self) -> None:
        """Test deleting a session successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.session_manager = Mock()
        manager.session_manager.delete_session = Mock(return_value=True)

        response = await browser_session_tool(
            manager=manager,
            action="delete_session",
            session_id="session-abc",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["session_id"] == "session-abc"
        assert "deleted" in response.data["message"].lower()
        manager.session_manager.delete_session.assert_called_once_with("session-abc")

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self) -> None:
        """Test deleting a non-existent session."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.session_manager = Mock()
        manager.session_manager.delete_session = Mock(return_value=False)

        response = await browser_session_tool(
            manager=manager,
            action="delete_session",
            session_id="nonexistent",
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_delete_session_no_session_id(self) -> None:
        """Test delete action fails without session_id."""
        manager = Mock(spec=ChromeManager)

        response = await browser_session_tool(
            manager=manager,
            action="delete_session",
        )

        assert response.success is False
        assert response.error is not None
        assert "session_id required" in response.error

    @pytest.mark.asyncio
    async def test_save_session_error_handling(self) -> None:
        """Test error handling when save_session fails."""
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-123"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(side_effect=Exception("Save failed"))
        manager.profile_manager = Mock()

        response = await browser_session_tool(
            manager=manager,
            action="save",
            instance_id="inst-123",
        )

        assert response.success is False
        assert response.error is not None
        assert "Save failed" in response.error

    @pytest.mark.asyncio
    async def test_restore_session_error_handling(self) -> None:
        """Test error handling when restore_session fails."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.session_manager = Mock()
        manager.session_manager.restore_session = AsyncMock(side_effect=Exception("Restore failed"))

        response = await browser_session_tool(
            manager=manager,
            action="restore",
            session_id="session-abc",
        )

        assert response.success is False
        assert response.error is not None
        assert "Restore failed" in response.error


class TestTerminateWithAutoSave:
    """Test terminate action with automatic session saving."""

    @pytest.mark.asyncio
    async def test_terminate_auto_saves_session(self) -> None:
        """Test that terminate automatically saves the session."""
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-123"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(return_value="session-autosaved")
        manager.profile_manager = Mock()
        manager.terminate_instance = AsyncMock()

        response = await browser_session_tool(
            manager=manager,
            action="terminate",
            instance_id="inst-123",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["session_id"] == "session-autosaved"
        assert "terminated and session saved" in response.data["message"].lower()
        manager.session_manager.save_session.assert_called_once()
        manager.terminate_instance.assert_called_once_with("inst-123")

    @pytest.mark.asyncio
    async def test_terminate_with_custom_session_name(self) -> None:
        """Test terminate with custom session name."""
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-123"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(return_value="session-custom")
        manager.profile_manager = Mock()
        manager.terminate_instance = AsyncMock()

        response = await browser_session_tool(
            manager=manager,
            action="terminate",
            instance_id="inst-123",
            session_name="my_custom_session",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["session_id"] == "session-custom"
        manager.session_manager.save_session.assert_called_once_with(instance, "my_custom_session")

    @pytest.mark.asyncio
    async def test_terminate_auto_generates_name(self) -> None:
        """Test that terminate auto-generates session name if not provided."""
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-abcd1234"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(return_value="session-xyz")
        manager.profile_manager = Mock()
        manager.terminate_instance = AsyncMock()

        response = await browser_session_tool(
            manager=manager,
            action="terminate",
            instance_id="inst-abcd1234",
        )

        # Verify auto-generated name was used
        call_args = manager.session_manager.save_session.call_args
        assert call_args[0][1].startswith("autosave_")
        assert response.success is True

    @pytest.mark.asyncio
    async def test_terminate_still_terminates_if_save_fails(self) -> None:
        """Test that instance is terminated even if session save fails."""
        manager = Mock(spec=ChromeManager)
        instance = Mock()
        instance.id = "inst-123"

        manager.get_instance = AsyncMock(return_value=instance)
        manager.session_manager = Mock()
        manager.session_manager.save_session = AsyncMock(side_effect=Exception("Save failed"))
        manager.terminate_instance = AsyncMock()

        response = await browser_session_tool(
            manager=manager,
            action="terminate",
            instance_id="inst-123",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["session_id"] is None
        assert "session save failed" in response.data["message"].lower()
        # Instance should still be terminated
        manager.terminate_instance.assert_called_once_with("inst-123")

    @pytest.mark.asyncio
    async def test_terminate_fails_if_instance_not_found(self) -> None:
        """Test terminate fails gracefully if instance not found."""
        manager = Mock(spec=ChromeManager)
        manager.get_instance = AsyncMock(return_value=None)

        response = await browser_session_tool(
            manager=manager,
            action="terminate",
            instance_id="nonexistent",
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()
