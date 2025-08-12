"""Facade module providing high-level browser control interfaces.

The facade module is organized into specialized submodules:

- navigation: Page navigation, waiting, scrolling, and content extraction
  - Navigator: Core navigation (back, forward, refresh, navigate)
  - Waiter: Wait conditions and element waiting
  - Scroller: Scrolling and viewport control
  - ContentExtractor: Page content extraction

- input: User input simulation
  - MouseController: Mouse operations (click, hover, drag)
  - KeyboardController: Keyboard input and text entry
  - FormsController: Form interaction and controls
  - TouchController: Touch gestures for mobile

- media: Screenshot and video capture
  - ScreenshotController: Screenshot capture and manipulation
  - VideoRecorder: Video recording of sessions

- devtools: Chrome DevTools Protocol operations
  - DevToolsController: Core CDP operations
  - NetworkController: Network monitoring and control
  - PerformanceController: Performance metrics

- context: Tab and frame management
  - TabController: Tab management
  - FrameController: Frame/iframe control

For backward compatibility, unified controllers are available that combine
the functionality of the submodules.
"""

# Import submodule components
# Import base and utilities
from .base import BaseController
from .config import FACADE_CONFIG, FacadeConfig
from .context import ContextManager, FrameController, TabController
from .devtools import DevToolsController, NetworkController, PerformanceController
from .input import FormsController, InputController, KeyboardController, MouseController, TouchController
from .media import MediaController, ScreenshotController, VideoRecorder
from .navigation import ContentExtractor, NavigationController, Navigator, Scroller, Waiter
from .utils import build_js_function_call, parameterized_js_execution, safe_js_property_access, sanitize_js_string

__all__ = [
    # Navigation
    "NavigationController",
    "Navigator",
    "Waiter",
    "Scroller",
    "ContentExtractor",
    # Input
    "InputController",
    "MouseController",
    "KeyboardController",
    "FormsController",
    "TouchController",
    # Media
    "MediaController",
    "ScreenshotController",
    "VideoRecorder",
    # DevTools
    "DevToolsController",
    "NetworkController",
    "PerformanceController",
    # Context
    "ContextManager",
    "TabController",
    "FrameController",
    # Base and utilities
    "BaseController",
    "FacadeConfig",
    "FACADE_CONFIG",
    "sanitize_js_string",
    "build_js_function_call",
    "safe_js_property_access",
    "parameterized_js_execution",
]
