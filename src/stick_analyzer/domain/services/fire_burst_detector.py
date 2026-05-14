from __future__ import annotations

from typing import Any

from ..constants import DEFAULT_MIN_DURATION_S, FIRE_GAP_THRESHOLD_S


class FireBurstDetector:
    """从采样序列中检测连续开火爆发段。"""

    def __init__(self, fire_gap_threshold_s: float = FIRE_GAP_THRESHOLD_S) -> None:
        self._fire_gap_threshold_s = fire_gap_threshold_s

    def detect_fire_bursts(
        self,
        df: Any,
        min_duration_s: float = DEFAULT_MIN_DURATION_S,
    ) -> list[tuple[float, float]]:
        fire_mask = df["fire"].astype(bool).values
        times = df["elapsed_s"].values

        bursts = []
        in_burst = False
        burst_start = 0.0
        last_fire_t = 0.0

        for t, f in zip(times, fire_mask):
            if f:
                if not in_burst:
                    burst_start = t
                    in_burst = True
                last_fire_t = t
            else:
                if in_burst and (t - last_fire_t) > self._fire_gap_threshold_s:
                    if last_fire_t - burst_start >= min_duration_s:
                        bursts.append((burst_start, last_fire_t))
                    in_burst = False

        if in_burst and last_fire_t - burst_start >= min_duration_s:
            bursts.append((burst_start, last_fire_t))

        return bursts


_DEFAULT_DETECTOR = FireBurstDetector()


def detect_fire_bursts(
    df: Any,
    min_duration_s: float = DEFAULT_MIN_DURATION_S,
) -> list[tuple[float, float]]:
    return _DEFAULT_DETECTOR.detect_fire_bursts(df, min_duration_s)

