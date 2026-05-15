"""控制器按键布局、映射和显示名。"""
from __future__ import annotations


# 按键布局（决定 GUI 显示什么标签）
LAYOUT_XBOX = "xbox"
LAYOUT_PS = "ps"
LAYOUT_PS_EDGE = "ps_edge"      # DualSense Edge，多了背键 FN1/FN2/RB1/RB2
LAYOUT_SWITCH = "switch"
LAYOUT_GENERIC = "generic"


# 这些是统一的"逻辑名"，CSV 写入用这套，GUI 显示时根据布局映射成原生标签
LOGICAL_BUTTONS = [
    # 面板按键（南/东/西/北）
    "ACTION_SOUTH",     # XBOX A / PS ×
    "ACTION_EAST",      # XBOX B / PS ○
    "ACTION_WEST",      # XBOX X / PS □
    "ACTION_NORTH",     # XBOX Y / PS △

    # 方向键
    "DPAD_UP",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",

    # 肩键
    "LEFT_SHOULDER",    # LB / L1
    "RIGHT_SHOULDER",   # RB / R1

    # 摇杆按下
    "LEFT_THUMB",       # L3
    "RIGHT_THUMB",      # R3

    # 选择/开始
    "BACK",             # BACK / SHARE
    "START",            # START / OPTIONS

    # PS 中央
    "GUIDE",            # XBOX GUIDE / PS HOME
    "TOUCHPAD",         # PS 触摸板按下（XBOX 没有）

    # DualSense Edge 专属（背键、功能键）
    "EDGE_FN1",
    "EDGE_FN2",
    "EDGE_RB1",
    "EDGE_RB2",

    # 扳机当按键用（部分场景需要）
    "TRIGGER_LEFT",     # 等价 LT > 0.5
    "TRIGGER_RIGHT",    # 等价 RT > 0.5
]


# 各布局下的中文显示名
BUTTON_DISPLAY_NAMES: dict[str, dict[str, str]] = {
    LAYOUT_XBOX: {
        "ACTION_SOUTH": "A 键",
        "ACTION_EAST": "B 键",
        "ACTION_WEST": "X 键",
        "ACTION_NORTH": "Y 键",
        "DPAD_UP": "方向键上",
        "DPAD_DOWN": "方向键下",
        "DPAD_LEFT": "方向键左",
        "DPAD_RIGHT": "方向键右",
        "LEFT_SHOULDER": "LB 左肩键",
        "RIGHT_SHOULDER": "RB 右肩键",
        "LEFT_THUMB": "L3 左摇杆按下",
        "RIGHT_THUMB": "R3 右摇杆按下",
        "BACK": "BACK / 视图",
        "START": "START / 菜单",
        "GUIDE": "XBOX GUIDE",
        "TOUCHPAD": "(无)",
        "EDGE_FN1": "(无)",
        "EDGE_FN2": "(无)",
        "EDGE_RB1": "(无)",
        "EDGE_RB2": "(无)",
        "TRIGGER_LEFT": "LT 左扳机",
        "TRIGGER_RIGHT": "RT 右扳机",
    },
    LAYOUT_PS: {
        "ACTION_SOUTH": "× 叉",
        "ACTION_EAST": "○ 圆",
        "ACTION_WEST": "□ 方",
        "ACTION_NORTH": "△ 三角",
        "DPAD_UP": "方向键上",
        "DPAD_DOWN": "方向键下",
        "DPAD_LEFT": "方向键左",
        "DPAD_RIGHT": "方向键右",
        "LEFT_SHOULDER": "L1 左肩键",
        "RIGHT_SHOULDER": "R1 右肩键",
        "LEFT_THUMB": "L3 左摇杆按下",
        "RIGHT_THUMB": "R3 右摇杆按下",
        "BACK": "SHARE / CREATE",
        "START": "OPTIONS",
        "GUIDE": "PS HOME",
        "TOUCHPAD": "触摸板按下",
        "EDGE_FN1": "(无)",
        "EDGE_FN2": "(无)",
        "EDGE_RB1": "(无)",
        "EDGE_RB2": "(无)",
        "TRIGGER_LEFT": "L2 左扳机",
        "TRIGGER_RIGHT": "R2 右扳机",
    },
    LAYOUT_PS_EDGE: {
        "ACTION_SOUTH": "× 叉",
        "ACTION_EAST": "○ 圆",
        "ACTION_WEST": "□ 方",
        "ACTION_NORTH": "△ 三角",
        "DPAD_UP": "方向键上",
        "DPAD_DOWN": "方向键下",
        "DPAD_LEFT": "方向键左",
        "DPAD_RIGHT": "方向键右",
        "LEFT_SHOULDER": "L1 左肩键",
        "RIGHT_SHOULDER": "R1 右肩键",
        "LEFT_THUMB": "L3 左摇杆按下",
        "RIGHT_THUMB": "R3 右摇杆按下",
        "BACK": "SHARE / CREATE",
        "START": "OPTIONS",
        "GUIDE": "PS HOME",
        "TOUCHPAD": "触摸板按下",
        "EDGE_FN1": "FN1 功能键",
        "EDGE_FN2": "FN2 功能键",
        "EDGE_RB1": "RB1 后置左键",
        "EDGE_RB2": "RB2 后置右键",
        "TRIGGER_LEFT": "L2 左扳机",
        "TRIGGER_RIGHT": "R2 右扳机",
    },
    LAYOUT_SWITCH: {
        "ACTION_SOUTH": "B 键",
        "ACTION_EAST": "A 键",
        "ACTION_WEST": "Y 键",
        "ACTION_NORTH": "X 键",
        "DPAD_UP": "方向键上",
        "DPAD_DOWN": "方向键下",
        "DPAD_LEFT": "方向键左",
        "DPAD_RIGHT": "方向键右",
        "LEFT_SHOULDER": "L 左肩键",
        "RIGHT_SHOULDER": "R 右肩键",
        "LEFT_THUMB": "L摇 按下",
        "RIGHT_THUMB": "R摇 按下",
        "BACK": "- 减号",
        "START": "+ 加号",
        "GUIDE": "HOME",
        "TOUCHPAD": "(无)",
        "EDGE_FN1": "(无)",
        "EDGE_FN2": "(无)",
        "EDGE_RB1": "(无)",
        "EDGE_RB2": "(无)",
        "TRIGGER_LEFT": "ZL 左扳机",
        "TRIGGER_RIGHT": "ZR 右扳机",
    },
    LAYOUT_GENERIC: {  # 兜底，用通用名
        "ACTION_SOUTH": "Btn 1 (下)",
        "ACTION_EAST": "Btn 2 (右)",
        "ACTION_WEST": "Btn 3 (左)",
        "ACTION_NORTH": "Btn 4 (上)",
        "DPAD_UP": "方向键上",
        "DPAD_DOWN": "方向键下",
        "DPAD_LEFT": "方向键左",
        "DPAD_RIGHT": "方向键右",
        "LEFT_SHOULDER": "左肩键",
        "RIGHT_SHOULDER": "右肩键",
        "LEFT_THUMB": "左摇杆按下",
        "RIGHT_THUMB": "右摇杆按下",
        "BACK": "BACK",
        "START": "START",
        "GUIDE": "GUIDE",
        "TOUCHPAD": "(可能无)",
        "EDGE_FN1": "(可能无)",
        "EDGE_FN2": "(可能无)",
        "EDGE_RB1": "(可能无)",
        "EDGE_RB2": "(可能无)",
        "TRIGGER_LEFT": "左扳机",
        "TRIGGER_RIGHT": "右扳机",
    },
}


# XBOX 风格手柄（包括天剑等 XInput 协议手柄）的 pygame Joystick button 索引
# 对应 Windows 下 XInput 协议手柄通过 pygame 时的实际行为
PYGAME_BUTTON_TO_LOGICAL_XBOX = {
    0: "ACTION_SOUTH",      # A
    1: "ACTION_EAST",       # B
    2: "ACTION_WEST",       # X
    3: "ACTION_NORTH",      # Y
    4: "LEFT_SHOULDER",     # LB ← 关键！
    5: "RIGHT_SHOULDER",    # RB ← 关键！修复 v2.0 bug
    6: "BACK",              # BACK / View
    7: "START",             # START / Menu
    8: "LEFT_THUMB",        # L3
    9: "RIGHT_THUMB",       # R3
    10: "GUIDE",            # XBOX Guide 键（少数手柄会暴露）
}


# PS 系列手柄（DualSense / DualSense Edge / DualShock 4）pygame SDL GameController button 索引
# 参考：https://wiki.libsdl.org/SDL2/SDL_GameControllerButton
PYGAME_BUTTON_TO_LOGICAL_PS = {
    0: "ACTION_SOUTH",      # × / Cross
    1: "ACTION_EAST",       # ○ / Circle
    2: "ACTION_WEST",       # □ / Square
    3: "ACTION_NORTH",      # △ / Triangle
    4: "BACK",              # SHARE / CREATE
    5: "GUIDE",             # PS Home
    6: "START",             # OPTIONS
    7: "LEFT_THUMB",        # L3
    8: "RIGHT_THUMB",       # R3
    9: "LEFT_SHOULDER",     # L1
    10: "RIGHT_SHOULDER",   # R1
    11: "DPAD_UP",
    12: "DPAD_DOWN",
    13: "DPAD_LEFT",
    14: "DPAD_RIGHT",
    15: "TOUCHPAD",         # 触摸板按下
    # DualSense Edge 背键
    16: "EDGE_FN1",
    17: "EDGE_FN2",
    18: "EDGE_RB1",
    19: "EDGE_RB2",
    20: "EDGE_RB1",         # 备用
    21: "EDGE_RB2",
}


# Switch Pro Controller（基于 SDL GameController，但部分手柄 ABXY 位置和 XBOX 不同）
PYGAME_BUTTON_TO_LOGICAL_SWITCH = {
    0: "ACTION_SOUTH",      # B（Switch 的下方按键）
    1: "ACTION_EAST",       # A
    2: "ACTION_WEST",       # Y
    3: "ACTION_NORTH",      # X
    4: "BACK",              # -
    5: "GUIDE",
    6: "START",             # +
    7: "LEFT_THUMB",
    8: "RIGHT_THUMB",
    9: "LEFT_SHOULDER",     # L
    10: "RIGHT_SHOULDER",   # R
    11: "DPAD_UP",
    12: "DPAD_DOWN",
    13: "DPAD_LEFT",
    14: "DPAD_RIGHT",
}


# 通用兜底（按 XBOX 风格猜测，更适合"未知 XInput 兼容手柄"）
PYGAME_BUTTON_TO_LOGICAL_GENERIC = PYGAME_BUTTON_TO_LOGICAL_XBOX


def get_pygame_button_map(
    layout: str,
    num_hats: int = 0,
    num_buttons: int = 0,
) -> dict[int, str]:
    """根据布局返回对应的 pygame button → 逻辑名映射表。

    XBOX 风格手柄在不同 pygame/SDL 版本下有 raw Joystick 和
    SDL GameController 两种抽象，通过 hat 数量自动判别走哪套索引。
    """
    if layout in (LAYOUT_PS, LAYOUT_PS_EDGE):
        return PYGAME_BUTTON_TO_LOGICAL_PS
    if layout == LAYOUT_SWITCH:
        return PYGAME_BUTTON_TO_LOGICAL_SWITCH

    # XBOX 风格 / GENERIC：根据 hat 数量自动判别抽象类型
    if num_hats == 0 and num_buttons >= 11:
        # SDL GameController 抽象：方向键已被映射成 button 11-14，
        # 索引和 PS 完全一致，直接复用
        return PYGAME_BUTTON_TO_LOGICAL_PS

    # 否则走旧的 raw Joystick 索引
    if layout == LAYOUT_XBOX:
        return PYGAME_BUTTON_TO_LOGICAL_XBOX
    return PYGAME_BUTTON_TO_LOGICAL_GENERIC


# 旧的统一映射表（向后兼容用，但不推荐直接使用）
SDL_BUTTON_TO_LOGICAL = PYGAME_BUTTON_TO_LOGICAL_PS


# XInput 按键映射
XINPUT_BUTTON_TO_LOGICAL = {
    "A": "ACTION_SOUTH",
    "B": "ACTION_EAST",
    "X": "ACTION_WEST",
    "Y": "ACTION_NORTH",
    "DPAD_UP": "DPAD_UP",
    "DPAD_DOWN": "DPAD_DOWN",
    "DPAD_LEFT": "DPAD_LEFT",
    "DPAD_RIGHT": "DPAD_RIGHT",
    "LEFT_SHOULDER": "LEFT_SHOULDER",
    "RIGHT_SHOULDER": "RIGHT_SHOULDER",
    "LEFT_THUMB": "LEFT_THUMB",
    "RIGHT_THUMB": "RIGHT_THUMB",
    "BACK": "BACK",
    "START": "START",
}


def get_button_display_name(layout: str, logical_button: str) -> str:
    """根据手柄布局获取按键的中文显示名。"""
    return BUTTON_DISPLAY_NAMES.get(layout, BUTTON_DISPLAY_NAMES[LAYOUT_GENERIC]).get(
        logical_button, logical_button)


def get_button_options_for_layout(layout: str) -> list[tuple[str, str]]:
    """返回 [(显示名, 逻辑代码), ...]，用于 GUI 下拉框。"""
    options = []
    # 屏蔽不存在的按键（显示名是 "(无)"）
    names = BUTTON_DISPLAY_NAMES.get(layout, BUTTON_DISPLAY_NAMES[LAYOUT_GENERIC])
    for logical in LOGICAL_BUTTONS:
        display = names.get(logical, logical)
        if display.startswith("(") and display.endswith(")"):
            continue
        options.append((display, logical))
    return options


__all__ = [
    "LAYOUT_XBOX",
    "LAYOUT_PS",
    "LAYOUT_PS_EDGE",
    "LAYOUT_SWITCH",
    "LAYOUT_GENERIC",
    "LOGICAL_BUTTONS",
    "BUTTON_DISPLAY_NAMES",
    "PYGAME_BUTTON_TO_LOGICAL_XBOX",
    "PYGAME_BUTTON_TO_LOGICAL_PS",
    "PYGAME_BUTTON_TO_LOGICAL_SWITCH",
    "PYGAME_BUTTON_TO_LOGICAL_GENERIC",
    "SDL_BUTTON_TO_LOGICAL",
    "XINPUT_BUTTON_TO_LOGICAL",
    "get_pygame_button_map",
    "get_button_display_name",
    "get_button_options_for_layout",
]
