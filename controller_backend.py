"""根目录控制器兼容入口。

真实实现已移入 ``stick_analyzer.adapters.controller``。保留本文件是为了让
旧代码继续 ``import controller_backend as cb``，并保留 ``python
controller_backend.py`` 的简单自测能力。
"""
from __future__ import annotations

import time

try:
    from stick_analyzer.adapters.controller import (
        BUTTON_DISPLAY_NAMES,
        LOGICAL_BUTTONS,
        LAYOUT_GENERIC,
        LAYOUT_PS,
        LAYOUT_PS_EDGE,
        LAYOUT_SWITCH,
        LAYOUT_XBOX,
        MAX_SLOTS,
        PROTO_PYGAME,
        PROTO_XINPUT,
        PYGAME_BUTTON_TO_LOGICAL_GENERIC,
        PYGAME_BUTTON_TO_LOGICAL_PS,
        PYGAME_BUTTON_TO_LOGICAL_SWITCH,
        PYGAME_BUTTON_TO_LOGICAL_XBOX,
        SDL_BUTTON_TO_LOGICAL,
        XINPUT_BUTTON_TO_LOGICAL,
        ControllerInfo,
        ControllerManager,
        ControllerState,
        PygameBackend,
        XInputBackend,
        _PygameBackend,
        _XInputBackend,
        get_button_display_name,
        get_button_options_for_layout,
        get_pygame_button_map,
    )
except ModuleNotFoundError:
    from src.stick_analyzer.adapters.controller import (
        BUTTON_DISPLAY_NAMES,
        LOGICAL_BUTTONS,
        LAYOUT_GENERIC,
        LAYOUT_PS,
        LAYOUT_PS_EDGE,
        LAYOUT_SWITCH,
        LAYOUT_XBOX,
        MAX_SLOTS,
        PROTO_PYGAME,
        PROTO_XINPUT,
        PYGAME_BUTTON_TO_LOGICAL_GENERIC,
        PYGAME_BUTTON_TO_LOGICAL_PS,
        PYGAME_BUTTON_TO_LOGICAL_SWITCH,
        PYGAME_BUTTON_TO_LOGICAL_XBOX,
        SDL_BUTTON_TO_LOGICAL,
        XINPUT_BUTTON_TO_LOGICAL,
        ControllerInfo,
        ControllerManager,
        ControllerState,
        PygameBackend,
        XInputBackend,
        _PygameBackend,
        _XInputBackend,
        get_button_display_name,
        get_button_options_for_layout,
        get_pygame_button_map,
    )


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
    "XInputBackend",
    "_PygameBackend",
    "_XInputBackend",
    "get_pygame_button_map",
    "get_button_display_name",
    "get_button_options_for_layout",
]


def _run_self_test() -> None:
    print("=" * 60)
    print("控制器后端自测")
    print("=" * 60)
    manager = ControllerManager()
    print(f"pygame 可用: {manager.has_pygame()}")
    print(f"XInput 可用: {manager.has_xinput()}")
    print()
    print(manager.scan_and_assign())
    print()
    for i, slot in enumerate(manager.slots):
        if slot is None:
            print(f"  槽位 {i + 1}: [空]")
        else:
            print(f"  槽位 {i + 1}: {slot.display_string()}  布局={slot.layout}")
    print()

    current = manager.get_current_controller()
    if current is None:
        return

    print(f"测试读取 {current.name} 5 次：")
    for i in range(5):
        state = manager.read_state(current)
        pressed = [name for name, is_pressed in state.buttons.items() if is_pressed]
        print(
            f"  [{i + 1}] L=({state.lx:+.2f},{state.ly:+.2f}) "
            f"R=({state.rx:+.2f},{state.ry:+.2f}) "
            f"LT={state.lt:.2f} RT={state.rt:.2f} "
            f"按键={pressed}"
        )
        time.sleep(0.5)


if __name__ == "__main__":
    _run_self_test()
