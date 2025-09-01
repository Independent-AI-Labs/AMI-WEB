"""Configuration for DevTools functionality."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DeviceEmulation:
    """Device emulation configuration."""

    width: int
    height: int
    deviceScaleFactor: float  # noqa: N815 - CDP spec requires this name
    mobile: bool
    userAgent: str  # noqa: N815 - CDP spec requires this name


def _load_user_agents_config() -> dict[str, Any]:
    """Load user agents configuration from JSON file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "user_agents.json"
    if config_path.exists():
        with config_path.open() as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {"presets": {}, "device_emulation": {}}


# Predefined device configurations
DEVICE_CONFIGS: dict[str, DeviceEmulation] = {
    "iPhone 12": DeviceEmulation(
        width=390,
        height=844,
        deviceScaleFactor=3.0,
        mobile=True,
        userAgent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ),
    "iPhone 13 Pro": DeviceEmulation(
        width=390,
        height=844,
        deviceScaleFactor=3.0,
        mobile=True,
        userAgent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    ),
    "iPhone SE": DeviceEmulation(
        width=375,
        height=667,
        deviceScaleFactor=2.0,
        mobile=True,
        userAgent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ),
    "iPad": DeviceEmulation(
        width=768,
        height=1024,
        deviceScaleFactor=2.0,
        mobile=True,
        userAgent="Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ),
    "iPad Pro": DeviceEmulation(
        width=1024,
        height=1366,
        deviceScaleFactor=2.0,
        mobile=True,
        userAgent="Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    ),
    "Pixel 5": DeviceEmulation(
        width=393,
        height=851,
        deviceScaleFactor=2.625,
        mobile=True,
        userAgent="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ),
    "Pixel 6": DeviceEmulation(
        width=412,
        height=915,
        deviceScaleFactor=2.625,
        mobile=True,
        userAgent="Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ),
    "Samsung Galaxy S21": DeviceEmulation(
        width=384,
        height=854,
        deviceScaleFactor=2.625,
        mobile=True,
        userAgent="Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ),
    "Desktop 1080p": DeviceEmulation(
        width=1920,
        height=1080,
        deviceScaleFactor=1.0,
        mobile=False,
        userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
    "Desktop 1440p": DeviceEmulation(
        width=2560,
        height=1440,
        deviceScaleFactor=1.0,
        mobile=False,
        userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
    "Desktop 4K": DeviceEmulation(
        width=3840,
        height=2160,
        deviceScaleFactor=1.0,
        mobile=False,
        userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
}


def get_device_config(device_name: str) -> DeviceEmulation | None:
    """Get device configuration by name.

    Args:
        device_name: Name of the device

    Returns:
        DeviceEmulation config or None if not found
    """
    return DEVICE_CONFIGS.get(device_name)


def list_available_devices() -> list[str]:
    """Get list of available device names.

    Returns:
        List of device names
    """
    return list(DEVICE_CONFIGS.keys())


def add_custom_device(name: str, config: DeviceEmulation) -> None:
    """Add a custom device configuration.

    Args:
        name: Name for the custom device
        config: Device configuration
    """
    DEVICE_CONFIGS[name] = config
