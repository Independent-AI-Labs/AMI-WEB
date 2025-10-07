"""Unit tests for browser_profile_tool facade."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from browser.backend.core.management.manager import ChromeManager
from browser.backend.mcp.chrome.tools.facade.profile import browser_profile_tool
from browser.backend.utils.exceptions import ProfileError


class TestProfileFacade:
    """Test browser_profile_tool facade."""

    @pytest.mark.asyncio
    async def test_create_profile_success(self) -> None:
        """Test creating a profile successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.create_profile = Mock(return_value=Path("/path/to/profile"))

        response = await browser_profile_tool(
            manager=manager,
            action="create",
            profile_name="test_profile",
            description="Test description",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["name"] == "test_profile"
        assert response.data["path"] == "/path/to/profile"
        assert response.data["description"] == "Test description"
        manager.profile_manager.create_profile.assert_called_once_with("test_profile", "Test description")

    @pytest.mark.asyncio
    async def test_create_profile_no_name(self) -> None:
        """Test create action fails without profile_name."""
        manager = Mock(spec=ChromeManager)

        response = await browser_profile_tool(
            manager=manager,
            action="create",
        )

        assert response.success is False
        assert response.error is not None
        assert "profile_name required" in response.error

    @pytest.mark.asyncio
    async def test_create_profile_already_exists(self) -> None:
        """Test create action fails when profile already exists."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.create_profile = Mock(side_effect=ProfileError("Profile test_profile already exists"))

        response = await browser_profile_tool(
            manager=manager,
            action="create",
            profile_name="test_profile",
        )

        assert response.success is False
        assert response.error is not None
        assert "already exists" in response.error

    @pytest.mark.asyncio
    async def test_create_profile_initializes_manager(self) -> None:
        """Test create action initializes manager if needed."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = False
        manager.initialize = AsyncMock()
        manager.profile_manager = Mock()
        manager.profile_manager.create_profile = Mock(return_value=Path("/path/to/profile"))

        response = await browser_profile_tool(
            manager=manager,
            action="create",
            profile_name="test_profile",
        )

        assert response.success is True
        manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_profile_success(self) -> None:
        """Test deleting a profile successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.delete_profile = Mock(return_value=True)

        response = await browser_profile_tool(
            manager=manager,
            action="delete",
            profile_name="test_profile",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["name"] == "test_profile"
        assert "deleted" in response.data["message"].lower()
        manager.profile_manager.delete_profile.assert_called_once_with("test_profile")

    @pytest.mark.asyncio
    async def test_delete_profile_no_name(self) -> None:
        """Test delete action fails without profile_name."""
        manager = Mock(spec=ChromeManager)

        response = await browser_profile_tool(
            manager=manager,
            action="delete",
        )

        assert response.success is False
        assert response.error is not None
        assert "profile_name required" in response.error

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self) -> None:
        """Test delete action fails when profile not found."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.delete_profile = Mock(return_value=False)

        response = await browser_profile_tool(
            manager=manager,
            action="delete",
            profile_name="nonexistent",
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_list_profiles_success(self) -> None:
        """Test listing profiles successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.list_profiles = Mock(
            return_value=[
                {
                    "name": "profile1",
                    "description": "First",
                    "created_at": "2025-01-01",
                    "exists": True,
                },
                {
                    "name": "profile2",
                    "description": "Second",
                    "created_at": "2025-01-02",
                    "exists": True,
                },
            ]
        )

        response = await browser_profile_tool(
            manager=manager,
            action="list",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["count"] == 2
        assert len(response.data["profiles"]) == 2
        assert response.data["profiles"][0]["name"] == "profile1"

    @pytest.mark.asyncio
    async def test_list_profiles_empty(self) -> None:
        """Test listing profiles when none exist."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.list_profiles = Mock(return_value=[])

        response = await browser_profile_tool(
            manager=manager,
            action="list",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["count"] == 0
        assert response.data["profiles"] == []

    @pytest.mark.asyncio
    async def test_copy_profile_success(self) -> None:
        """Test copying a profile successfully."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.copy_profile = Mock(return_value=Path("/path/to/dest"))

        response = await browser_profile_tool(
            manager=manager,
            action="copy",
            source_profile="source",
            dest_profile="dest",
        )

        assert response.success is True
        assert response.data is not None
        assert response.data["source"] == "source"
        assert response.data["dest"] == "dest"
        assert response.data["path"] == "/path/to/dest"
        manager.profile_manager.copy_profile.assert_called_once_with("source", "dest")

    @pytest.mark.asyncio
    async def test_copy_profile_no_source(self) -> None:
        """Test copy action fails without source_profile."""
        manager = Mock(spec=ChromeManager)

        response = await browser_profile_tool(
            manager=manager,
            action="copy",
            dest_profile="dest",
        )

        assert response.success is False
        assert response.error is not None
        assert "source_profile required" in response.error

    @pytest.mark.asyncio
    async def test_copy_profile_no_dest(self) -> None:
        """Test copy action fails without dest_profile."""
        manager = Mock(spec=ChromeManager)

        response = await browser_profile_tool(
            manager=manager,
            action="copy",
            source_profile="source",
        )

        assert response.success is False
        assert response.error is not None
        assert "dest_profile required" in response.error

    @pytest.mark.asyncio
    async def test_copy_profile_source_not_found(self) -> None:
        """Test copy action fails when source not found."""
        manager = Mock(spec=ChromeManager)
        manager._initialized = True
        manager.profile_manager = Mock()
        manager.profile_manager.copy_profile = Mock(side_effect=ProfileError("Source profile source not found"))

        response = await browser_profile_tool(
            manager=manager,
            action="copy",
            source_profile="source",
            dest_profile="dest",
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_unknown_action(self) -> None:
        """Test unknown action returns error."""
        manager = Mock(spec=ChromeManager)

        response = await browser_profile_tool(
            manager=manager,
            action="invalid",  # type: ignore
        )

        assert response.success is False
        assert response.error is not None
        assert "Unknown action" in response.error
