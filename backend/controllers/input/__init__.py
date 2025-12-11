"""Input controllers for browser automation."""

from browser.backend.controllers.input.coordinate import CoordinateController
from browser.backend.controllers.input.drag import DragController
from browser.backend.controllers.input.forms import FormsController
from browser.backend.controllers.input.keyboard import KeyboardController
from browser.backend.controllers.input.mouse import MouseController
from browser.backend.controllers.input.touch import TouchController


__all__ = [
    "DragController",
    "CoordinateController",
    "FormsController",
    "KeyboardController",
    "MouseController",
    "TouchController",
]
