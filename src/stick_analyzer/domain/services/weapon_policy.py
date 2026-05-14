from __future__ import annotations

from collections.abc import Mapping

from ..constants import DURING_FIRE_STABILITY_MS, WEAPON_RPM


class WeaponPolicy:
    """根据武器文本推断射速和开火中稳定度窗口。"""

    def __init__(
        self,
        weapon_rpm: Mapping[str, int] | None = None,
        default_during_window_ms: int = DURING_FIRE_STABILITY_MS,
    ) -> None:
        self._weapon_rpm = weapon_rpm or WEAPON_RPM
        self._default_during_window_ms = default_during_window_ms

    def detect_weapon_rpm(self, weapons_str: str) -> int:
        """从用户填的武器字段里推断 RPM。识别不到返回 0（按默认处理）。"""
        if not weapons_str:
            return 0
        s = weapons_str.lower()
        # 优先匹配长关键词（r-301 比 r3 更精确）。
        for name in sorted(self._weapon_rpm.keys(), key=len, reverse=True):
            if name in s:
                return self._weapon_rpm[name]
        return 0

    def rpm_to_during_window_ms(self, rpm: int) -> int:
        """根据武器射速选择 during_stability 窗口长度。"""
        if rpm <= 0:
            return self._default_during_window_ms
        if rpm > 900:
            return 200
        if rpm < 150:
            return 0
        return self._default_during_window_ms


_DEFAULT_POLICY = WeaponPolicy()


def detect_weapon_rpm(weapons_str: str) -> int:
    return _DEFAULT_POLICY.detect_weapon_rpm(weapons_str)


def rpm_to_during_window_ms(rpm: int) -> int:
    return _DEFAULT_POLICY.rpm_to_during_window_ms(rpm)

