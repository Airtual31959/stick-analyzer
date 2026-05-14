from __future__ import annotations

from collections.abc import Mapping
from typing import Any


INTENSITY_FACTORS = {
    "none": 1.00,
    "antishake": 0.90,
    "light": 1.10,
    "medium": 1.25,
    "strong": 1.45,
    "extreme": 1.70,
}

INTENSITY_LABELS = {
    "none": "无 RC 功能",
    "antishake": "防抖方向",
    "light": "轻度增抖",
    "medium": "中度增抖",
    "strong": "强增抖",
    "extreme": "极限增抖",
}

SENSOR_FACTORS = {
    "alps": 1.00,
    "tmr": 1.00,
    "hall": 1.25,
    "unknown": 1.00,
}

SENSOR_LABELS = {
    "alps": "碳膜 ALPS",
    "tmr": "TMR（隧道磁阻）",
    "hall": "霍尔",
    "unknown": "未知 / 默认（按主流处理）",
}


class ThresholdPolicy:
    """根据 RC 动感强度和传感器类型调整稳定度阈值。"""

    def get_stability_thresholds(self, metadata: Mapping[str, Any]) -> dict:
        thresholds = _default_thresholds()
        factor = _read_intensity_factor(metadata, thresholds)
        if factor is not None and factor != 1.0:
            _scale_stability_thresholds(thresholds, factor)

        sensor = metadata.get("sensor_type", "unknown").strip().lower()
        sensor_factor = SENSOR_FACTORS.get(sensor, 1.00)
        thresholds["sensor_label"] = SENSOR_LABELS.get(sensor, "未知")
        thresholds["sensor_factor"] = sensor_factor
        if sensor_factor != 1.0:
            _scale_stability_thresholds(thresholds, sensor_factor)
        return thresholds


def _default_thresholds() -> dict:
    return {
        "pre_stable": 0.04,
        "pre_unstable": 0.10,
        "during_stable": 0.04,
        "during_unstable": 0.08,
        "rev_good": 10,
        "rev_bad": 25,
        "intensity_label": "无 RC / 中性",
        "sensor_label": "碳膜 / 默认",
        "sensor_factor": 1.00,
    }


def _read_intensity_factor(
    metadata: Mapping[str, Any],
    thresholds: dict,
) -> float | None:
    intensity = metadata.get("rc_ads_intensity", "").strip().lower()
    if intensity and intensity in INTENSITY_FACTORS:
        thresholds["intensity_label"] = INTENSITY_LABELS[intensity]
        return INTENSITY_FACTORS[intensity]
    return _read_legacy_rc_factor(metadata, thresholds)


def _read_legacy_rc_factor(
    metadata: Mapping[str, Any],
    thresholds: dict,
) -> float | None:
    try:
        rc_ads = float(metadata.get("rc_ads", "0"))
        if -15 <= rc_ads < 0:
            thresholds["intensity_label"] = f"老格式 RC={rc_ads}"
            return 1.0 + abs(rc_ads) * 0.05
        if rc_ads < -15:
            thresholds["intensity_label"] = (
                f"老格式 RC={rc_ads}（数值范围未知，按中度增抖处理）")
            return INTENSITY_FACTORS["medium"]
    except (ValueError, TypeError):
        pass
    return None


def _scale_stability_thresholds(thresholds: dict, factor: float) -> None:
    thresholds["pre_stable"] *= factor
    thresholds["pre_unstable"] *= factor
    thresholds["during_stable"] *= factor
    thresholds["during_unstable"] *= factor


_DEFAULT_POLICY = ThresholdPolicy()


def get_stability_thresholds(metadata: Mapping[str, Any]) -> dict:
    return _DEFAULT_POLICY.get_stability_thresholds(metadata)

