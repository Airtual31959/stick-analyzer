from __future__ import annotations

import pytest

from app.domain.services.threshold_policy import ThresholdPolicy


def test_get_stability_thresholds_returns_default_thresholds():
    thresholds = ThresholdPolicy().get_stability_thresholds({})

    assert thresholds["pre_stable"] == pytest.approx(0.04)
    assert thresholds["pre_unstable"] == pytest.approx(0.10)
    assert thresholds["during_stable"] == pytest.approx(0.04)
    assert thresholds["during_unstable"] == pytest.approx(0.08)
    assert thresholds["sensor_label"] == "未知 / 默认（按主流处理）"
    assert thresholds["sensor_factor"] == pytest.approx(1.0)


def test_get_stability_thresholds_applies_intensity_and_hall_sensor_factors():
    thresholds = ThresholdPolicy().get_stability_thresholds({
        "rc_ads_intensity": "medium",
        "sensor_type": "hall",
    })

    factor = 1.25 * 1.25
    assert thresholds["pre_stable"] == pytest.approx(0.04 * factor)
    assert thresholds["pre_unstable"] == pytest.approx(0.10 * factor)
    assert thresholds["during_stable"] == pytest.approx(0.04 * factor)
    assert thresholds["during_unstable"] == pytest.approx(0.08 * factor)
    assert thresholds["intensity_label"] == "中度增抖"
    assert thresholds["sensor_label"] == "霍尔"


def test_get_stability_thresholds_preserves_legacy_rc_behavior():
    thresholds = ThresholdPolicy().get_stability_thresholds({
        "rc_ads": "-4",
        "sensor_type": "tmr",
    })

    assert thresholds["pre_stable"] == pytest.approx(0.04 * 1.2)
    assert thresholds["intensity_label"] == "老格式 RC=-4.0"
    assert thresholds["sensor_label"] == "TMR（隧道磁阻）"

