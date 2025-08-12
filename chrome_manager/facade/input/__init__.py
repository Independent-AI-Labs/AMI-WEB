"""Input submodule for browser interaction.

This module provides input-related functionality split into focused components:
- MouseController: Mouse operations (click, hover, drag)
- KeyboardController: Keyboard input and text entry
- FormsController: Form interaction and controls
- TouchController: Touch gestures for mobile emulation
"""

from .forms import FormsController
from .keyboard import KeyboardController
from .mouse import MouseController
from .touch import TouchController

__all__ = ["MouseController", "KeyboardController", "FormsController", "TouchController"]


# Backward compatibility - create a unified InputController
class InputController(MouseController, KeyboardController, FormsController, TouchController):
    """Unified input controller combining all input functionality.

    This class maintains backward compatibility while using the new
    modular structure underneath.
    """
