"""XInput 控制器后端。"""
from __future__ import annotations

from typing import Any

from .button_maps import LOGICAL_BUTTONS, XINPUT_BUTTON_TO_LOGICAL


class _XInputBackend:
    """XInput 实现（保留作为 XBOX 兼容设备的备选）。"""

    def __init__(self):
        self._available = False
        try:
            import XInput
            self._XInput = XInput
            self._available = True
        except ImportError:
            self._XInput = None

    def is_available(self) -> bool:
        return self._available

    def scan(self) -> list[dict[str, Any]]:
        """扫描 XInput 0-3 槽位。"""
        if not self._available:
            return []
        results = []
        try:
            connected = self._XInput.get_connected()
            for i in range(4):
                if connected[i]:
                    results.append({
                        "index": i,
                        "name": f"XBOX 360 兼容控制器 #{i}",
                        "guid": f"xinput_{i}",
                        "handle": i,
                        "num_axes": 6,
                        "num_buttons": 14,
                        "num_hats": 0,
                    })
        except Exception as e:
            print(f"[警告] XInput 扫描失败: {e}")
        return results

    def read_state(self, info: Any):
        from .controller_manager import ControllerState

        if not self._available:
            return ControllerState()
        try:
            idx = info.handle
            xinput_state = self._XInput.get_state(idx)
            (lx, ly), (rx, ry) = self._XInput.get_thumb_values(xinput_state)
            lt, rt = self._XInput.get_trigger_values(xinput_state)
            buttons_raw = self._XInput.get_button_values(xinput_state)

            state = ControllerState(
                lx=float(lx), ly=float(ly), rx=float(rx), ry=float(ry),
                lt=float(lt), rt=float(rt),
            )
            buttons = {}
            for xinput_name, logical in XINPUT_BUTTON_TO_LOGICAL.items():
                buttons[logical] = bool(buttons_raw.get(xinput_name, False))
            buttons["TRIGGER_LEFT"] = lt > 0.5
            buttons["TRIGGER_RIGHT"] = rt > 0.5
            # XInput 没有 GUIDE/TOUCHPAD/EDGE_*，全为 False
            for logical in LOGICAL_BUTTONS:
                buttons.setdefault(logical, False)
            state.buttons = buttons
            return state
        except Exception:
            return ControllerState()


XInputBackend = _XInputBackend


__all__ = ["XInputBackend", "_XInputBackend"]
