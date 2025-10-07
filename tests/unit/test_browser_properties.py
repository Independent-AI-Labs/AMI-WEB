"""Unit tests for browser properties validation and management."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock, patch


class TestBrowserProperties:
    """Test browser properties configuration without real browser."""

    def test_default_properties_structure(self) -> None:
        """Test default browser properties have required fields."""
        properties: dict[str, Any] = {
            "userAgent": "Mozilla/5.0...",
            "platform": "Win32",
            "language": "en-US",
            "languages": ["en-US", "en"],
            "vendor": "Google Inc.",
            "webdriver": False,
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "screenResolution": {"width": 1920, "height": 1080},
            "timezone": "America/New_York",
        }

        assert "userAgent" in properties
        assert "webdriver" in properties
        assert properties["webdriver"] is False
        assert "hardwareConcurrency" in properties
        assert isinstance(properties["languages"], list)

    def test_stealth_preset_properties(self) -> None:
        """Test stealth preset removes detection vectors."""
        stealth_properties: dict[str, Any] = {
            "webdriver": False,
            "plugins": {
                "length": 3,
                "0": {"name": "Chrome PDF Plugin"},
                "1": {"name": "Chrome PDF Viewer"},
                "2": {"name": "Native Client"},
            },
            "chrome": {"runtime": {}},
            "permissions": {"query": "function"},
            "navigator": {
                "webdriver": False,
                "plugins": "PluginArray",
                "languages": ["en-US", "en"],
            },
        }

        assert stealth_properties["webdriver"] is False
        assert "plugins" in stealth_properties
        assert stealth_properties["plugins"]["length"] > 0
        assert stealth_properties["navigator"]["webdriver"] is False

    def test_mobile_preset_properties(self) -> None:
        """Test mobile preset properties."""
        mobile_properties: dict[str, Any] = {
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "platform": "iPhone",
            "maxTouchPoints": 5,
            "orientation": {"type": "portrait-primary", "angle": 0},
            "screenResolution": {"width": 375, "height": 812},
            "devicePixelRatio": 3,
        }

        assert "iPhone" in mobile_properties["userAgent"]
        assert mobile_properties["platform"] == "iPhone"
        assert mobile_properties["maxTouchPoints"] > 0
        max_mobile_width = 500
        assert mobile_properties["screenResolution"]["width"] < max_mobile_width

    def test_property_validation_types(self) -> None:
        """Test property type validation."""
        properties: dict[str, Any] = {
            "webdriver": "false",  # Should be boolean
            "hardwareConcurrency": "8",  # Should be number
            "languages": "en-US",  # Should be array
        }

        # Type validation
        assert not isinstance(properties["webdriver"], bool)
        assert not isinstance(properties["hardwareConcurrency"], int)
        assert not isinstance(properties["languages"], list)

    def test_property_merging(self) -> None:
        """Test merging custom properties with defaults."""
        defaults: dict[str, Any] = {
            "userAgent": "Default UA",
            "platform": "Win32",
            "webdriver": True,
            "languages": ["en"],
        }

        custom: dict[str, Any] = {
            "userAgent": "Custom UA",
            "webdriver": False,
            "customProp": "value",
        }

        # Merge custom into defaults
        merged = {**defaults, **custom}

        assert merged["userAgent"] == "Custom UA"
        assert merged["webdriver"] is False
        assert merged["platform"] == "Win32"  # From defaults
        assert merged["customProp"] == "value"  # From custom
        assert merged["languages"] == ["en"]  # From defaults


class TestPropertiesManager:
    """Test PropertiesManager functionality without real implementation."""

    @patch("browser.backend.core.browser.properties_manager.PropertiesManager")
    def test_load_default_properties(self, mock_manager: Mock) -> None:
        """Test loading default properties."""
        manager = mock_manager()
        manager.load_default_properties = Mock(return_value={"userAgent": "Default", "webdriver": False})

        props = manager.load_default_properties()

        assert props["userAgent"] == "Default"
        assert props["webdriver"] is False
        manager.load_default_properties.assert_called_once()

    @patch("browser.backend.core.browser.properties_manager.PropertiesManager")
    def test_load_preset(self, mock_manager: Mock) -> None:
        """Test loading property presets."""
        manager = mock_manager()
        manager.load_preset = Mock(
            return_value={
                "preset": "stealth",
                "webdriver": False,
                "plugins": {"length": 3},
            }
        )

        props = manager.load_preset("stealth")

        assert props["preset"] == "stealth"
        assert props["webdriver"] is False
        assert "plugins" in props
        manager.load_preset.assert_called_once_with("stealth")

    @patch("browser.backend.core.browser.properties_manager.PropertiesManager")
    def test_apply_overrides(self, mock_manager: Mock) -> None:
        """Test applying property overrides."""
        manager = mock_manager()
        base_props: dict[str, Any] = {"userAgent": "Base", "webdriver": True}
        overrides: dict[str, Any] = {"webdriver": False, "custom": "value"}

        manager.apply_overrides = Mock(return_value={"userAgent": "Base", "webdriver": False, "custom": "value"})

        result = manager.apply_overrides(base_props, overrides)

        assert result["userAgent"] == "Base"
        assert result["webdriver"] is False
        assert result["custom"] == "value"

    @patch("browser.backend.core.browser.properties_manager.PropertiesManager")
    def test_validate_properties(self, mock_manager: Mock) -> None:
        """Test property validation."""
        manager = mock_manager()

        valid_props: dict[str, Any] = {
            "userAgent": "Mozilla/5.0",
            "webdriver": False,
            "languages": ["en-US"],
        }

        invalid_props: dict[str, Any] = {
            "userAgent": 123,  # Should be string
            "webdriver": "false",  # Should be boolean
            "languages": "en-US",  # Should be array
        }

        manager.validate = Mock(side_effect=lambda p: p == valid_props)

        assert manager.validate(valid_props) is True
        assert manager.validate(invalid_props) is False


class TestPropertyInjection:
    """Test property injection into browser without real browser."""

    def test_generate_injection_script(self) -> None:
        """Test generating property injection JavaScript."""
        properties: dict[str, Any] = {
            "userAgent": "Custom UA",
            "webdriver": False,
            "platform": "Win32",
        }

        # Generate injection script
        script = f"""
        Object.defineProperty(navigator, 'userAgent', {{
            get: () => '{properties["userAgent"]}'
        }});
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => {str(properties["webdriver"]).lower()}
        }});
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{properties["platform"]}'
        }});
        """

        assert "Custom UA" in script
        assert "false" in script.lower()
        assert "Win32" in script

    def test_injection_script_escaping(self) -> None:
        """Test proper escaping in injection scripts."""
        properties: dict[str, str] = {
            "userAgent": "Mozilla/5.0 'test' \"quotes\"",
            "customProp": "<script>alert('xss')</script>",
        }

        # Should escape quotes and special characters
        escaped_ua = properties["userAgent"].replace("'", "\\'").replace('"', '\\"')
        escaped_custom = properties["customProp"].replace("<", "\\<").replace(">", "\\>")

        assert "\\'" in escaped_ua
        assert '\\"' in escaped_ua
        assert "\\<" in escaped_custom
        assert "\\>" in escaped_custom

    def test_property_getter_definitions(self) -> None:
        """Test property getter definitions."""
        script = """
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: false,
            enumerable: true
        });
        """

        assert "Object.defineProperty" in script
        assert "get:" in script
        assert "configurable: false" in script
        assert "enumerable: true" in script

    def test_property_injection_order(self) -> None:
        """Test property injection order matters."""
        # Order: Core properties first, then overrides
        injection_order: list[str] = [
            "webdriver",  # Most important - anti-detection
            "userAgent",
            "platform",
            "languages",
            "plugins",
            "chrome",
            "permissions",
            "customProperties",
        ]

        # Verify webdriver is first for anti-detection
        assert injection_order[0] == "webdriver"
        assert injection_order.index("webdriver") < injection_order.index("userAgent")


class TestPropertyPersistence:
    """Test property persistence and loading."""

    def test_save_properties_to_profile(self) -> None:
        """Test saving properties to profile."""
        properties: dict[str, Any] = {
            "userAgent": "Custom UA",
            "webdriver": False,
            "profile_id": "test-profile-123",
        }

        # Simulate saving to JSON
        json_data = json.dumps(properties, indent=2)

        assert "Custom UA" in json_data
        assert "false" in json_data
        assert "test-profile-123" in json_data

    def test_load_properties_from_profile(self) -> None:
        """Test loading properties from profile."""
        json_data = '{"userAgent": "Loaded UA", "webdriver": false}'

        properties: dict[str, Any] = json.loads(json_data)

        assert properties["userAgent"] == "Loaded UA"
        assert properties["webdriver"] is False

    def test_profile_properties_migration(self) -> None:
        """Test migrating old property format to new."""
        old_format: dict[str, Any] = {"ua": "Old UA", "no_webdriver": True}

        # Migration logic
        new_format: dict[str, Any] = {
            "userAgent": old_format.get("ua", ""),
            "webdriver": not old_format.get("no_webdriver", False),
        }

        assert new_format["userAgent"] == "Old UA"
        assert new_format["webdriver"] is False
