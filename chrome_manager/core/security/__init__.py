"""Browser security and anti-detection functionality."""

from .antidetect import (
    ChromeDriverPatcher,
    execute_anti_detection_scripts,
    get_anti_detection_arguments,
    get_anti_detection_prefs,
)
from .tab_injector import SimpleTabInjector

__all__ = [
    "ChromeDriverPatcher",
    "execute_anti_detection_scripts",
    "get_anti_detection_arguments",
    "get_anti_detection_prefs",
    "SimpleTabInjector",
]
