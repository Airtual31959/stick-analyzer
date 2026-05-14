"""控制器适配器公共入口。"""
from __future__ import annotations

from .button_maps import (
    BUTTON_DISPLAY_NAMES,
    LOGICAL_BUTTONS,
    PYGAME_BUTTON_TO_LOGICAL_GENERIC,
    PYGAME_BUTTON_TO_LOGICAL_PS,
    PYGAME_BUTTON_TO_LOGICAL_SWITCH,
    PYGAME_BUTTON_TO_LOGICAL_XBOX,
    SDL_BUTTON_TO_LOGICAL,
    XINPUT_BUTTON_TO_LOGICAL,
    get_button_display_name,
    get_button_options_for_layout,
    get_pygame_button_map,
)
from .controller_manager import (
    LAYOUT_GENERIC,
    LAYOUT_PS,
    LAYOUT_PS_EDGE,
    LAYOUT_SWITCH,
    LAYOUT_XBOX,
    MAX_SLOTS,
    PROTO_PYGAME,
    PROTO_XINPUT,
    ControllerInfo,
    ControllerManager,
    ControllerState,
)
from .pygame_backend import PygameBackend, _PygameBackend
from .xinput_backend import XInputBackend, _XInputBackend


__all__ = [
    "PROTO_PYGAME",
    "PROTO_XINPUT",
    "LAYOUT_XBOX",
    "LAYOUT_PS",
    "LAYOUT_PS_EDGE",
    "LAYOUT_SWITCH",
    "LAYOUT_GENERIC",
    "MAX_SLOTS",
    "LOGICAL_BUTTONS",
    "BUTTON_DISPLAY_NAMES",
    "PYGAME_BUTTON_TO_LOGICAL_XBOX",
    "PYGAME_BUTTON_TO_LOGICAL_PS",
    "PYGAME_BUTTON_TO_LOGICAL_SWITCH",
    "PYGAME_BUTTON_TO_LOGICAL_GENERIC",
    "SDL_BUTTON_TO_LOGICAL",
    "XINPUT_BUTTON_TO_LOGICAL",
    "ControllerInfo",
    "ControllerState",
    "ControllerManager",
    "PygameBackend",
    "_PygameBackend",
    "XInputBackend",
    "_XInputBackend",
    "get_pygame_button_map",
    "get_button_display_name",
    "get_button_options_for_layout",
]
