"""DevTools submodule for Chrome DevTools Protocol operations.

This module provides DevTools-related functionality split into focused components:
- DevToolsController: Core CDP operations and device emulation
- NetworkController: Network monitoring and control
- PerformanceController: Performance metrics and profiling
"""

from .config import DEVICE_CONFIGS, DeviceEmulation, add_custom_device, get_device_config, list_available_devices
from .devtools import DevToolsController
from .network import NetworkController
from .performance import PerformanceController

__all__ = [
    "DevToolsController",
    "NetworkController",
    "PerformanceController",
    "DeviceEmulation",
    "DEVICE_CONFIGS",
    "get_device_config",
    "list_available_devices",
    "add_custom_device",
]
