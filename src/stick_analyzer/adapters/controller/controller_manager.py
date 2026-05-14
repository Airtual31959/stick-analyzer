"""控制器槽位管理和统一状态模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .button_maps import (
    LAYOUT_GENERIC,
    LAYOUT_PS,
    LAYOUT_PS_EDGE,
    LAYOUT_SWITCH,
    LAYOUT_XBOX,
)
from .pygame_backend import PygameBackend, _PygameBackend
from .xinput_backend import XInputBackend, _XInputBackend


PROTO_PYGAME = "pygame"
PROTO_XINPUT = "xinput"

MAX_SLOTS = 4


@dataclass
class ControllerInfo:
    """单个手柄信息。"""

    slot: int                    # 0-3
    name: str                    # 显示名，如 "DualSense Edge Wireless Controller"
    protocol: str                # PROTO_PYGAME / PROTO_XINPUT
    layout: str                  # LAYOUT_XBOX / LAYOUT_PS_EDGE / ...
    guid: str = ""               # pygame 的 GUID，XInput 没有
    handle: Any = None           # 实际句柄（pygame.Joystick 或 XInput 索引）
    num_axes: int = 0
    num_buttons: int = 0
    num_hats: int = 0
    is_active: bool = True       # 是否仍在线（被拔出后变 False）

    def display_string(self) -> str:
        """给 GUI 显示的字符串。"""
        proto = "pygame" if self.protocol == PROTO_PYGAME else "XInput"
        return f"{self.name} [{proto}]"


@dataclass
class ControllerState:
    """单帧的统一状态。"""

    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0
    buttons: dict[str, bool] = field(default_factory=dict)


class ControllerManager:
    """4 槽位管理器。"""

    def __init__(self):
        self._pygame = PygameBackend()
        self._xinput = XInputBackend()
        # 4 个槽位，初始全空
        self.slots: list[Optional[ControllerInfo]] = [None] * MAX_SLOTS
        self._current_slot: Optional[int] = None  # 用户当前选中的槽位

    def has_pygame(self) -> bool:
        return self._pygame.is_available()

    def has_xinput(self) -> bool:
        return self._xinput.is_available()

    def scan_and_assign(self) -> str:
        """重新扫描并分配槽位。返回一段说明文字（适合显示在 GUI）。"""
        pygame_devs = self._pygame.scan() if self._pygame.is_available() else []
        xinput_devs = self._xinput.scan() if self._xinput.is_available() else []

        # XBOX 风格手柄优先 XInput；PS / Switch / 通用 HID 仍走 pygame。
        pygame_xbox_devs = [
            dev for dev in pygame_devs if self._is_xbox_style(dev["name"])
        ]
        pygame_other_devs = [
            dev for dev in pygame_devs if not self._is_xbox_style(dev["name"])
        ]

        # 同时被两边识别的 XBOX 手柄，按顺序用 pygame 友好名替换 XInput 名称。
        n_replace = min(len(pygame_xbox_devs), len(xinput_devs))
        xinput_used = []
        for i in range(n_replace):
            xinput_dev = dict(xinput_devs[i])
            xinput_dev["name"] = pygame_xbox_devs[i]["name"]
            xinput_used.append(xinput_dev)

        xinput_extra = xinput_devs[n_replace:]
        pygame_xbox_fallback = pygame_xbox_devs[n_replace:]

        candidates: list[tuple[str, dict[str, Any]]] = []
        candidates.extend((PROTO_XINPUT, dev) for dev in xinput_used)
        candidates.extend((PROTO_XINPUT, dev) for dev in xinput_extra)
        candidates.extend((PROTO_PYGAME, dev) for dev in pygame_xbox_fallback)
        candidates.extend((PROTO_PYGAME, dev) for dev in pygame_other_devs)

        new_slots: list[Optional[ControllerInfo]] = [None] * MAX_SLOTS
        used_candidates = self._keep_existing_slots(candidates, new_slots)
        self._assign_new_candidates(candidates, used_candidates, new_slots)

        self.slots = new_slots
        self._normalize_current_slot()

        active_count = sum(1 for slot in self.slots if slot is not None)
        overflow = len(candidates) - active_count
        msg_parts = [f"扫描完成：检测到 {active_count} 个手柄"]
        if overflow > 0:
            msg_parts.append(
                f"⚠ 还有 {overflow} 个手柄未显示（槽位已满），请拔出未使用的手柄后重新扫描")
        return "，".join(msg_parts)

    def get_slot(self, slot_idx: int) -> Optional[ControllerInfo]:
        if 0 <= slot_idx < MAX_SLOTS:
            return self.slots[slot_idx]
        return None

    def get_current_slot(self) -> Optional[int]:
        return self._current_slot

    def set_current_slot(self, slot_idx: Optional[int]) -> None:
        if slot_idx is None or self.slots[slot_idx] is not None:
            self._current_slot = slot_idx

    def get_current_controller(self) -> Optional[ControllerInfo]:
        if self._current_slot is None:
            return None
        return self.slots[self._current_slot]

    def read_state(self, info: ControllerInfo) -> ControllerState:
        """从指定手柄读一帧。"""
        if info.protocol == PROTO_PYGAME:
            return self._pygame.read_state(info)
        if info.protocol == PROTO_XINPUT:
            return self._xinput.read_state(info)
        return ControllerState()

    @staticmethod
    def _is_xbox_style(name: str) -> bool:
        normalized = name.lower()
        return any(k in normalized for k in [
            "xbox", "x-box", "xinput", "controller for windows",
        ])

    def _keep_existing_slots(
        self,
        candidates: list[tuple[str, dict[str, Any]]],
        new_slots: list[Optional[ControllerInfo]],
    ) -> set[int]:
        used_candidates: set[int] = set()
        for slot_idx, existing in enumerate(self.slots):
            if existing is None:
                continue
            matched_idx = self._find_existing_candidate(
                existing,
                candidates,
                used_candidates,
            )
            if matched_idx is None:
                continue
            _, dev = candidates[matched_idx]
            self._refresh_existing_info(existing, dev)
            new_slots[slot_idx] = existing
            used_candidates.add(matched_idx)
        return used_candidates

    def _find_existing_candidate(
        self,
        existing: ControllerInfo,
        candidates: list[tuple[str, dict[str, Any]]],
        used_candidates: set[int],
    ) -> Optional[int]:
        for cand_idx, (proto, dev) in enumerate(candidates):
            if cand_idx in used_candidates or proto != existing.protocol:
                continue
            if proto == PROTO_PYGAME and dev["guid"] == existing.guid and dev["guid"]:
                return cand_idx
            if proto == PROTO_XINPUT and dev["index"] == existing.handle:
                return cand_idx
        return None

    @staticmethod
    def _refresh_existing_info(existing: ControllerInfo, dev: dict[str, Any]) -> None:
        existing.handle = dev["handle"]
        existing.num_axes = dev["num_axes"]
        existing.num_buttons = dev["num_buttons"]
        existing.num_hats = dev["num_hats"]
        existing.is_active = True

    def _assign_new_candidates(
        self,
        candidates: list[tuple[str, dict[str, Any]]],
        used_candidates: set[int],
        new_slots: list[Optional[ControllerInfo]],
    ) -> None:
        for cand_idx, (proto, dev) in enumerate(candidates):
            if cand_idx in used_candidates:
                continue
            free_idx = next((i for i, slot in enumerate(new_slots) if slot is None), None)
            if free_idx is None:
                continue

            layout = self._detect_candidate_layout(proto, dev)
            new_slots[free_idx] = ControllerInfo(
                slot=free_idx,
                name=dev["name"],
                protocol=proto,
                layout=layout,
                guid=dev["guid"],
                handle=dev["handle"],
                num_axes=dev["num_axes"],
                num_buttons=dev["num_buttons"],
                num_hats=dev["num_hats"],
                is_active=True,
            )

    def _detect_candidate_layout(self, proto: str, dev: dict[str, Any]) -> str:
        if proto == PROTO_PYGAME:
            return self._pygame.detect_layout(dev["name"], dev["num_buttons"])
        return LAYOUT_XBOX

    def _normalize_current_slot(self) -> None:
        if self._current_slot is not None and self.slots[self._current_slot] is None:
            self._current_slot = None
        if self._current_slot is None:
            for i, slot in enumerate(self.slots):
                if slot is not None:
                    self._current_slot = i
                    break


__all__ = [
    "PROTO_PYGAME",
    "PROTO_XINPUT",
    "LAYOUT_XBOX",
    "LAYOUT_PS",
    "LAYOUT_PS_EDGE",
    "LAYOUT_SWITCH",
    "LAYOUT_GENERIC",
    "MAX_SLOTS",
    "ControllerInfo",
    "ControllerState",
    "ControllerManager",
    "PygameBackend",
    "_PygameBackend",
    "XInputBackend",
    "_XInputBackend",
]
