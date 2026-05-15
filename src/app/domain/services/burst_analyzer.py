from __future__ import annotations

from typing import Any

import numpy as np

from ..constants import (
    PRE_FIRE_STABILITY_MS,
    WINDOW_AFTER_S,
    WINDOW_BEFORE_S,
)
from .weapon_policy import WeaponPolicy


class BurstAnalyzer:
    """分析单次开火爆发的稳定度、反转和推杆区间。"""

    def __init__(self, weapon_policy: WeaponPolicy | None = None) -> None:
        self._weapon_policy = weapon_policy or WeaponPolicy()

    def analyze_burst(
        self,
        df: Any,
        burst_start: float,
        burst_end: float,
        noise_floor_x: float = 0.0,
        noise_floor_y: float = 0.0,
        weapon_rpm: int = 0,
    ) -> dict | None:
        win = _select_burst_window(df, burst_start, burst_end)
        if len(win) < 10:
            return None

        win["rel_t"] = win["elapsed_s"] - burst_start
        burst_duration = burst_end - burst_start

        pre_stability = _calculate_pre_stability(
            win,
            noise_floor_x,
            noise_floor_y,
        )
        during_window_ms = self._weapon_policy.rpm_to_during_window_ms(weapon_rpm)
        during_stability = _calculate_during_stability(
            win,
            during_window_ms,
            noise_floor_x,
            noise_floor_y,
        )
        avg_magnitude, max_magnitude = _calculate_magnitude_metrics(win)
        reversal_metrics = _calculate_reversal_metrics(win, burst_duration)
        dom_low, dom_high = _calculate_dominant_input_range(win, burst_duration)
        is_ads = _detect_ads_at_fire_start(win)
        is_moving, lx_range, ly_range = _detect_movement(win)

        return {
            "burst_start": burst_start,
            "burst_end": burst_end,
            "duration": burst_duration,
            "data": win,
            "pre_stability": pre_stability,
            "during_stability": during_stability,
            "avg_magnitude": avg_magnitude,
            "max_magnitude": max_magnitude,
            "total_reversals": reversal_metrics["total_reversals"],
            "large_overshoots": reversal_metrics["large_overshoots"],
            "small_jitters": reversal_metrics["small_jitters"],
            "max_reversal_amplitude": reversal_metrics["max_reversal_amplitude"],
            "dominant_input_low": dom_low,
            "dominant_input_high": dom_high,
            "is_ads": is_ads,
            "is_moving": is_moving,
            "lx_range": lx_range,
            "ly_range": ly_range,
            "weapon_rpm": weapon_rpm,
            "during_window_ms": during_window_ms,
        }


def _select_burst_window(df: Any, burst_start: float, burst_end: float) -> Any:
    t_win_start = burst_start - WINDOW_BEFORE_S
    t_win_end = burst_end + WINDOW_AFTER_S
    return df[
        (df["elapsed_s"] >= t_win_start)
        & (df["elapsed_s"] <= t_win_end)
    ].copy()


def _denoise(
    std_x: float,
    std_y: float,
    noise_floor_x: float,
    noise_floor_y: float,
) -> float:
    """用方差相减扣除硬件本底，避免报告把传感器噪声算成手部抖动。"""
    var_x = max(0.0, std_x ** 2 - noise_floor_x ** 2)
    var_y = max(0.0, std_y ** 2 - noise_floor_y ** 2)
    return float(np.sqrt(var_x + var_y))


def _calculate_pre_stability(
    win: Any,
    noise_floor_x: float,
    noise_floor_y: float,
) -> float:
    pre_window = win[
        (win["rel_t"] >= -PRE_FIRE_STABILITY_MS / 1000.0)
        & (win["rel_t"] <= 0)
    ]
    if len(pre_window) > 5:
        pre_rx_std = pre_window["rx"].std()
        pre_ry_std = pre_window["ry"].std()
        return _denoise(pre_rx_std, pre_ry_std, noise_floor_x, noise_floor_y)
    return float("nan")


def _calculate_during_stability(
    win: Any,
    during_window_ms: int,
    noise_floor_x: float,
    noise_floor_y: float,
) -> float:
    if during_window_ms <= 0:
        return float("nan")

    fire_during = win[
        (win["rel_t"] >= 0)
        & (win["rel_t"] <= during_window_ms / 1000.0)
    ]
    if len(fire_during) <= 5:
        return float("nan")

    rx_arr = fire_during["rx"].values
    ry_arr = fire_during["ry"].values
    x_idx = np.arange(len(rx_arr))
    if len(x_idx) > 2:
        rx_trend = np.polyfit(x_idx, rx_arr, 1)
        ry_trend = np.polyfit(x_idx, ry_arr, 1)
        rx_residual = rx_arr - np.polyval(rx_trend, x_idx)
        ry_residual = ry_arr - np.polyval(ry_trend, x_idx)
        return _denoise(
            rx_residual.std(),
            ry_residual.std(),
            noise_floor_x,
            noise_floor_y,
        )
    return _denoise(rx_arr.std(), ry_arr.std(), noise_floor_x, noise_floor_y)


def _calculate_magnitude_metrics(win: Any) -> tuple[float, float]:
    rx = win["rx"].values
    ry = win["ry"].values
    magnitude = np.sqrt(rx ** 2 + ry ** 2)
    return float(np.mean(magnitude)), float(np.max(magnitude))


def _calculate_reversal_metrics(win: Any, burst_duration: float) -> dict:
    burst_data = win[(win["rel_t"] >= 0) & (win["rel_t"] <= burst_duration)]
    if len(burst_data) <= 50:
        return {
            "total_reversals": 0,
            "large_overshoots": 0,
            "small_jitters": 0,
            "max_reversal_amplitude": 0.0,
        }

    smooth_win = max(5, min(50, len(burst_data) // 5))
    rx_t, rx_l, rx_s, rx_m = _count_meaningful_reversals(
        burst_data["rx"].values,
        smooth_win,
    )
    ry_t, ry_l, ry_s, ry_m = _count_meaningful_reversals(
        burst_data["ry"].values,
        smooth_win,
    )
    return {
        "total_reversals": int(rx_t + ry_t),
        "large_overshoots": int(rx_l + ry_l),
        "small_jitters": int(rx_s + ry_s),
        "max_reversal_amplitude": float(max(rx_m, ry_m)),
    }


def _count_meaningful_reversals(arr: Any, smooth_win: int) -> tuple[int, int, int, float]:
    """返回 (total, large_overshoots, small_jitters, max_amplitude)。"""
    kernel = np.ones(smooth_win) / smooth_win
    smoothed = np.convolve(arr, kernel, mode="valid")
    if len(smoothed) < 4:
        return 0, 0, 0, 0.0
    v = np.diff(smoothed)
    sign_change_idx = np.where(np.diff(np.sign(v)) != 0)[0]
    total = 0
    large = 0
    small = 0
    max_amp = 0.0
    last_extreme_val = smoothed[0]
    for idx in sign_change_idx:
        cur_extreme = smoothed[idx + 1]
        amp = abs(cur_extreme - last_extreme_val)
        if amp > 0.05:
            total += 1
            if amp > 0.15:
                large += 1
            else:
                small += 1
            if amp > max_amp:
                max_amp = amp
            last_extreme_val = cur_extreme
    return total, large, small, max_amp


def _calculate_dominant_input_range(
    win: Any,
    burst_duration: float,
) -> tuple[float, float]:
    relevant = win[(win["rel_t"] >= -0.5) & (win["rel_t"] <= burst_duration)]
    rel_mag = np.sqrt(relevant["rx"] ** 2 + relevant["ry"] ** 2).values
    nonzero = rel_mag[rel_mag > 0.05]
    if len(nonzero) > 10:
        dom_low = float(np.percentile(nonzero, 25)) * 100
        dom_high = float(np.percentile(nonzero, 75)) * 100
        return dom_low, dom_high
    return 0, 0


def _detect_ads_at_fire_start(win: Any) -> bool:
    fire_pre = win[(win["rel_t"] >= -0.05) & (win["rel_t"] <= 0)]
    if len(fire_pre) > 0:
        return bool(fire_pre["ads"].astype(bool).any())
    return False


def _detect_movement(win: Any) -> tuple[bool, float, float]:
    lx_range = float(win["lx"].max() - win["lx"].min())
    ly_range = float(win["ly"].max() - win["ly"].min())
    is_moving = lx_range > 0.3 or ly_range > 0.3
    return is_moving, lx_range, ly_range


_DEFAULT_ANALYZER = BurstAnalyzer()


def analyze_burst(
    df: Any,
    burst_start: float,
    burst_end: float,
    noise_floor_x: float = 0.0,
    noise_floor_y: float = 0.0,
    weapon_rpm: int = 0,
) -> dict | None:
    return _DEFAULT_ANALYZER.analyze_burst(
        df,
        burst_start,
        burst_end,
        noise_floor_x=noise_floor_x,
        noise_floor_y=noise_floor_y,
        weapon_rpm=weapon_rpm,
    )

