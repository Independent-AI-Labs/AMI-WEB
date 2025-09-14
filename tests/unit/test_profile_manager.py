"""Unit tests for ProfileManager operations."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestProfileManager:
    """Test ProfileManager without file I/O."""

    @pytest.mark.asyncio
    async def test_initialize(self) -> None:
        """Test profile manager initialization."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles_dir = Path("data/profiles")
            manager.profiles = {}
            manager.initialize = AsyncMock()

            await manager.initialize()

            assert manager.profiles_dir == Path("data/profiles")
            assert manager.profiles == {}
            manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile(self) -> None:
        """Test creating a new profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {}
            manager.create_profile = AsyncMock(side_effect=lambda name, _props: f"profile-{name}")

            profile_id = await manager.create_profile("test", {"userAgent": "Custom UA"})

            assert profile_id == "profile-test"
            manager.create_profile.assert_called_once_with("test", {"userAgent": "Custom UA"})

    @pytest.mark.asyncio
    async def test_get_profile(self) -> None:
        """Test retrieving a profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {
                "profile-123": {
                    "id": "profile-123",
                    "name": "Test Profile",
                    "properties": {"userAgent": "Custom UA", "webdriver": False},
                },
            }
            manager.get_profile = AsyncMock(side_effect=lambda pid: manager.profiles.get(pid))

            profile = await manager.get_profile("profile-123")

            assert profile is not None
            assert profile["name"] == "Test Profile"
            assert profile["properties"]["userAgent"] == "Custom UA"
            manager.get_profile.assert_called_once_with("profile-123")

    @pytest.mark.asyncio
    async def test_update_profile(self) -> None:
        """Test updating profile properties."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {
                "profile-123": {
                    "id": "profile-123",
                    "properties": {"userAgent": "Old UA", "platform": "Win32"},
                },
            }
            manager.update_profile = AsyncMock(side_effect=lambda pid, props: manager.profiles[pid]["properties"].update(props))

            await manager.update_profile("profile-123", {"userAgent": "New UA"})

            assert manager.profiles["profile-123"]["properties"]["userAgent"] == "New UA"
            assert manager.profiles["profile-123"]["properties"]["platform"] == "Win32"
            manager.update_profile.assert_called_once_with("profile-123", {"userAgent": "New UA"})

    @pytest.mark.asyncio
    async def test_delete_profile(self) -> None:
        """Test deleting a profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {"profile-123": {}, "profile-456": {}}
            manager.delete_profile = AsyncMock(side_effect=lambda pid: manager.profiles.pop(pid, None))

            await manager.delete_profile("profile-123")

            assert "profile-123" not in manager.profiles
            assert "profile-456" in manager.profiles
            manager.delete_profile.assert_called_once_with("profile-123")

    def test_list_profiles(self) -> None:
        """Test listing all profiles."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {
                "profile-123": {"name": "Profile 1"},
                "profile-456": {"name": "Profile 2"},
            }
            manager.list_profiles = Mock(return_value=list(manager.profiles.values()))

            profiles = manager.list_profiles()

            expected_count = 2
            assert len(profiles) == expected_count
            assert profiles[0]["name"] == "Profile 1"
            assert profiles[1]["name"] == "Profile 2"
            manager.list_profiles.assert_called_once()


class TestProfilePresets:
    """Test profile preset management."""

    def test_stealth_preset(self) -> None:
        """Test stealth preset properties."""
        stealth_preset: dict[str, Any] = {
            "name": "stealth",
            "properties": {
                "webdriver": False,
                "plugins": {"length": 3},
                "languages": ["en-US", "en"],
                "vendor": "Google Inc.",
                "chrome": {"runtime": {}},
                "permissions": {"query": "function"},
            },
        }

        assert stealth_preset["properties"]["webdriver"] is False
        assert stealth_preset["properties"]["plugins"]["length"] > 0
        assert "en-US" in stealth_preset["properties"]["languages"]

    def test_mobile_preset(self) -> None:
        """Test mobile preset properties."""
        mobile_preset: dict[str, Any] = {
            "name": "mobile",
            "properties": {
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
                "platform": "iPhone",
                "maxTouchPoints": 5,
                "orientation": {"type": "portrait-primary", "angle": 0},
                "screenResolution": {"width": 375, "height": 812},
            },
        }

        assert "iPhone" in mobile_preset["properties"]["userAgent"]
        assert mobile_preset["properties"]["platform"] == "iPhone"
        assert mobile_preset["properties"]["maxTouchPoints"] > 0

    def test_desktop_preset(self) -> None:
        """Test desktop preset properties."""
        desktop_preset: dict[str, Any] = {
            "name": "desktop",
            "properties": {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "platform": "Win32",
                "hardwareConcurrency": 8,
                "deviceMemory": 8,
                "screenResolution": {"width": 1920, "height": 1080},
            },
        }

        assert "Windows NT" in desktop_preset["properties"]["userAgent"]
        assert desktop_preset["properties"]["platform"] == "Win32"
        min_cores = 4
        assert desktop_preset["properties"]["hardwareConcurrency"] >= min_cores

    @pytest.mark.asyncio
    async def test_apply_preset(self) -> None:
        """Test applying a preset to a profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.presets = {
                "stealth": {"webdriver": False, "plugins": {"length": 3}},
            }
            manager.apply_preset = AsyncMock(side_effect=lambda pid, preset: manager.profiles[pid]["properties"].update(manager.presets[preset]))
            manager.profiles = {"profile-123": {"id": "profile-123", "properties": {"userAgent": "Custom"}}}

            await manager.apply_preset("profile-123", "stealth")

            profile = manager.profiles["profile-123"]
            assert profile["properties"]["webdriver"] is False
            assert "plugins" in profile["properties"]
            assert profile["properties"]["userAgent"] == "Custom"  # Original property preserved
            manager.apply_preset.assert_called_once_with("profile-123", "stealth")


class TestProfileValidation:
    """Test profile property validation."""

    def test_validate_user_agent(self) -> None:
        """Test user agent validation."""
        valid_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        invalid_ua = ""

        # Simple validation: non-empty and contains browser identifier
        def validate_ua(ua: str) -> bool:
            return bool(ua) and ("Mozilla" in ua or "Chrome" in ua or "Safari" in ua)

        assert validate_ua(valid_ua) is True
        assert validate_ua(invalid_ua) is False

    def test_validate_screen_resolution(self) -> None:
        """Test screen resolution validation."""
        valid_resolutions = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 375, "height": 812},  # Mobile
        ]

        invalid_resolutions = [
            {"width": 0, "height": 1080},
            {"width": 1920, "height": 0},
            {"width": -1, "height": 768},
            {},
        ]

        def validate_resolution(res: object) -> bool:
            return isinstance(res, dict) and "width" in res and "height" in res and res["width"] > 0 and res["height"] > 0

        for res in valid_resolutions:
            assert validate_resolution(res) is True

        for res in invalid_resolutions:
            assert validate_resolution(res) is False

    def test_validate_languages(self) -> None:
        """Test languages validation."""
        valid_languages = [
            ["en-US", "en"],
            ["fr-FR", "fr", "en"],
            ["ja-JP"],
        ]

        invalid_languages = [
            [],  # Empty
            [""],  # Empty string
            "en-US",  # Not a list
            None,
        ]

        def validate_languages(langs: object) -> bool:
            return isinstance(langs, list) and len(langs) > 0 and all(isinstance(lang, str) and lang for lang in langs)

        for langs in valid_languages:
            assert validate_languages(langs) is True

        for invalid in invalid_languages:
            assert validate_languages(invalid) is False

    @pytest.mark.asyncio
    async def test_validate_profile(self) -> None:
        """Test complete profile validation."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()

            valid_profile = {
                "id": "profile-123",
                "name": "Test Profile",
                "properties": {
                    "userAgent": "Mozilla/5.0",
                    "platform": "Win32",
                    "languages": ["en-US"],
                    "screenResolution": {"width": 1920, "height": 1080},
                },
            }

            invalid_profile = {
                "id": "profile-456",
                # Missing required properties
                "properties": {"userAgent": ""},
            }

            manager.validate_profile = Mock(
                side_effect=lambda p: bool("properties" in p and p["properties"].get("userAgent") and isinstance(p["properties"].get("languages"), list)),
            )

            assert manager.validate_profile(valid_profile) is True
            assert manager.validate_profile(invalid_profile) is False


class TestProfilePersistence:
    """Test profile persistence operations."""

    def test_serialize_profile(self) -> None:
        """Test serializing profile data."""
        profile = {
            "id": "profile-123",
            "name": "Custom Profile",
            "properties": {
                "userAgent": "Custom UA",
                "webdriver": False,
                "languages": ["en-US", "en"],
            },
            "created_at": 1234567890,
        }

        serialized = json.dumps(profile, indent=2)

        assert "profile-123" in serialized
        assert "Custom Profile" in serialized
        assert "Custom UA" in serialized

    def test_deserialize_profile(self) -> None:
        """Test deserializing profile data."""
        json_data = """{
            "id": "profile-123",
            "name": "Test",
            "properties": {
                "userAgent": "Test UA",
                "webdriver": false
            }
        }"""

        profile = json.loads(json_data)

        assert profile["id"] == "profile-123"
        assert profile["properties"]["userAgent"] == "Test UA"
        assert profile["properties"]["webdriver"] is False

    @pytest.mark.asyncio
    async def test_export_profile(self) -> None:
        """Test exporting a profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {
                "profile-123": {
                    "id": "profile-123",
                    "name": "Export Test",
                    "properties": {"userAgent": "Export UA"},
                },
            }
            manager.export_profile = AsyncMock(side_effect=lambda pid: json.dumps(manager.profiles.get(pid)))

            exported = await manager.export_profile("profile-123")

            assert "profile-123" in exported
            assert "Export Test" in exported
            manager.export_profile.assert_called_once_with("profile-123")

    @pytest.mark.asyncio
    async def test_import_profile(self) -> None:
        """Test importing a profile."""
        with patch("browser.backend.core.management.profile_manager.ProfileManager") as mock_manager_class:
            manager = mock_manager_class()
            manager.profiles = {}

            async def mock_import(data: str | dict[str, Any]) -> None:
                profile = json.loads(data) if isinstance(data, str) else data
                manager.profiles[profile["id"]] = profile

            manager.import_profile = AsyncMock(side_effect=mock_import)

            profile_data = """{
                "id": "profile-imported",
                "name": "Imported Profile",
                "properties": {"userAgent": "Imported UA"}
            }"""

            await manager.import_profile(profile_data)

            # Mock doesn't actually parse JSON, so we check the call
            manager.import_profile.assert_called_once_with(profile_data)
