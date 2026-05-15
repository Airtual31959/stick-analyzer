"""pygame 控制器后端。"""
from __future__ import annotations

import os
from typing import Any

from .button_maps import (
    LAYOUT_GENERIC,
    LAYOUT_PS,
    LAYOUT_PS_EDGE,
    LAYOUT_SWITCH,
    LAYOUT_XBOX,
    LOGICAL_BUTTONS,
    get_pygame_button_map,
)


# pygame/SDL 环境变量必须在 import pygame 之前设置才生效。
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_JOYSTICK_THREAD", "1")
os.environ.setdefault("SDL_HINT_JOYSTICK_THREAD", "1")
os.environ.setdefault("SDL_HINT_AUTO_UPDATE_JOYSTICKS", "1")


class _PygameBackend:
    """pygame 实现。"""

    def __init__(self):
        self._initialized = False
        self._available = self._try_init()

    def _try_init(self) -> bool:
        try:
            import pygame
            pygame.init()
            pygame.joystick.init()
            # 我们用轮询方式读状态，不依赖 joystick 事件队列。
            try:
                pygame.event.set_blocked([
                    pygame.JOYAXISMOTION,
                    pygame.JOYBALLMOTION,
                    pygame.JOYBUTTONDOWN,
                    pygame.JOYBUTTONUP,
                    pygame.JOYHATMOTION,
                    pygame.JOYDEVICEADDED,
                    pygame.JOYDEVICEREMOVED,
                ])
            except Exception:
                pass  # 老版本 pygame 可能没有部分事件常量，忽略
            self._initialized = True
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"[警告] pygame 初始化失败: {e}")
            return False

    def is_available(self) -> bool:
        return self._available

    def scan(self) -> list[dict[str, Any]]:
        """扫描所有 pygame 识别的手柄，返回原始信息。"""
        if not self._available:
            return []
        try:
            import pygame
            # 必须重新初始化 joystick 系统才能识别新插入的设备
            pygame.joystick.quit()
            pygame.joystick.init()

            results = []
            count = pygame.joystick.get_count()
            for i in range(count):
                try:
                    joystick = pygame.joystick.Joystick(i)
                    joystick.init()
                    name = joystick.get_name()
                    guid = joystick.get_guid() if hasattr(joystick, "get_guid") else ""
                    results.append({
                        "index": i,
                        "name": name,
                        "guid": guid,
                        "handle": joystick,
                        "num_axes": joystick.get_numaxes(),
                        "num_buttons": joystick.get_numbuttons(),
                        "num_hats": joystick.get_numhats(),
                    })
                except Exception as e:
                    print(f"[警告] pygame 手柄 {i} 初始化失败: {e}")
            return results
        except Exception as e:
            print(f"[警告] pygame 扫描失败: {e}")
            return []

    def detect_layout(self, name: str, num_buttons: int) -> str:
        """根据手柄名称和按键数判断布局。"""
        normalized = name.lower()
        if "dualsense edge" in normalized or "ps5 edge" in normalized:
            return LAYOUT_PS_EDGE
        if any(k in normalized for k in [
            "dualsense", "playstation", "ps5", "ps4", "ps3",
            "dualshock", "wireless controller",
        ]):
            # 普通 PS 手柄但按键多于 16 个 → 可能是 Edge
            if num_buttons >= 17:
                return LAYOUT_PS_EDGE
            return LAYOUT_PS
        if any(k in normalized for k in [
            "xbox", "x-box", "microsoft", "xinput",
        ]):
            return LAYOUT_XBOX
        if any(k in normalized for k in [
            "switch", "joy-con", "joycon", "nintendo", "pro controller",
        ]):
            return LAYOUT_SWITCH
        return LAYOUT_GENERIC

    def read_state(self, info: Any):
        """从指定手柄读一帧。"""
        from .controller_manager import ControllerState

        try:
            import pygame
            # 必须调用 pump 让 SDL 内部更新 joystick 状态。
            pygame.event.pump()
            pygame.event.clear()
            joystick = info.handle
            state = ControllerState()

            # 摇杆轴：pygame SDL2 GameController 标准
            axes_count = info.num_axes
            if axes_count >= 1:
                state.lx = float(joystick.get_axis(0))
            if axes_count >= 2:
                # pygame Y 轴方向：上为 -1，下为 +1（XInput 是反的，统一成 XInput 风格）
                state.ly = -float(joystick.get_axis(1))
            if axes_count >= 3:
                state.rx = float(joystick.get_axis(2))
            if axes_count >= 4:
                state.ry = -float(joystick.get_axis(3))
            if axes_count >= 5:
                # 扳机：pygame 给 -1（未按）到 +1（按到底），归一化到 0~1
                lt_raw = float(joystick.get_axis(4))
                state.lt = (lt_raw + 1.0) / 2.0
            if axes_count >= 6:
                rt_raw = float(joystick.get_axis(5))
                state.rt = (rt_raw + 1.0) / 2.0

            button_map = get_pygame_button_map(
                info.layout,
                num_hats=info.num_hats,
                num_buttons=info.num_buttons,
            )
            buttons = {}
            for i in range(info.num_buttons):
                pressed = bool(joystick.get_button(i))
                logical = button_map.get(i)
                if logical:
                    buttons[logical] = pressed

            if info.num_hats > 0:
                hx, hy = joystick.get_hat(0)
                # pygame hat：上 +1，下 -1
                buttons["DPAD_UP"] = hy > 0
                buttons["DPAD_DOWN"] = hy < 0
                buttons["DPAD_LEFT"] = hx < 0
                buttons["DPAD_RIGHT"] = hx > 0

            buttons["TRIGGER_LEFT"] = state.lt > 0.5
            buttons["TRIGGER_RIGHT"] = state.rt > 0.5

            # 补齐所有逻辑按键（默认 False）
            for logical in LOGICAL_BUTTONS:
                buttons.setdefault(logical, False)

            state.buttons = buttons
            return state
        except Exception:
            return ControllerState()


PygameBackend = _PygameBackend


__all__ = ["PygameBackend", "_PygameBackend"]
