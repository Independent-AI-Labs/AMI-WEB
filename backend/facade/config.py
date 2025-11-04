"""Configuration for facade controllers with customizable timing values."""

from typing import Any

from pydantic import BaseModel


class FacadeConfig(BaseModel):
    """Configuration for facade controller timing and behavior."""

    # Navigation timings
    scroll_wait_smooth: float = 0.5  # Wait after smooth scroll (seconds)
    scroll_wait_instant: float = 0.1  # Wait after instant scroll (seconds)

    # Input timings
    click_delay_default: float = 0.05  # Default delay between clicks (seconds)
    type_delay_default: float = 0.01  # Default delay between keystrokes (seconds)

    # Screenshot timings
    screenshot_stitch_delay: float = 0.2  # Delay between screenshots for stitching (seconds)

    # Video recording
    recording_fps_default: int = 30  # Default FPS for video recording

    # General waits
    default_wait_timeout: int = 30  # Default timeout for wait operations (seconds)
    poll_frequency: float = 0.5  # Default poll frequency for wait conditions (seconds)

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "FacadeConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})


# Global config instance - can be overridden by user
FACADE_CONFIG = FacadeConfig()
