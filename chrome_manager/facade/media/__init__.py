"""Media submodule for screenshots and video recording.

This module provides media-related functionality split into focused components:
- ScreenshotController: Screenshot capture and image manipulation
- VideoRecorder: Video recording of browser sessions
"""

from .screenshot import ScreenshotController
from .video import VideoRecorder

__all__ = ["ScreenshotController", "VideoRecorder"]


# Backward compatibility - create unified controllers
class MediaController(ScreenshotController, VideoRecorder):
    """Unified media controller combining screenshot and video functionality.

    This class maintains backward compatibility while using the new
    modular structure underneath.
    """
