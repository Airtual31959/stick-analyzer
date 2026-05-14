import math

import numpy as np
import pandas as pd
import pytest

import analyzer


@pytest.mark.parametrize(
    ("weapons", "expected_rpm"),
    [
        ("R-99", 1080),
        ("r301", 810),
        ("冲锋枪", 800),
        ("unknown weapon", 0),
    ],
)
def test_detect_weapon_rpm_matches_known_names_and_fallback(weapons, expected_rpm):
    assert analyzer.detect_weapon_rpm(weapons) == expected_rpm


@pytest.mark.parametrize(
    ("rpm", "expected_window_ms"),
    [
        (1080, 200),
        (600, 300),
        (30, 0),
        (0, analyzer.DURING_FIRE_STABILITY_MS),
    ],
)
def test_rpm_to_during_window_ms_selects_expected_window(rpm, expected_window_ms):
    assert analyzer.rpm_to_during_window_ms(rpm) == expected_window_ms


def _fire_df(fire_ranges, end_s=2.5, step_s=0.05):
    times = np.round(np.arange(0.0, end_s + step_s / 2, step_s), 3)
    fire = [
        any(start_s <= t <= stop_s for start_s, stop_s in fire_ranges)
        for t in times
    ]
    return pd.DataFrame({"elapsed_s": times, "fire": fire})


def test_detect_fire_bursts_filters_short_taps_and_splits_large_gaps():
    df = _fire_df(
        [
            (0.10, 0.12),
            (0.65, 0.80),
            (1.35, 1.50),
            (2.05, 2.20),
        ],
        end_s=2.5,
    )

    bursts = analyzer.detect_fire_bursts(df, min_duration_s=0.1)

    assert bursts == [
        (0.65, 0.80),
        (1.35, 1.50),
        (2.05, 2.20),
    ]


def test_detect_fire_bursts_keeps_segments_joined_within_gap_threshold():
    df = _fire_df([(0.20, 0.30), (0.60, 0.75)])

    bursts = analyzer.detect_fire_bursts(df, min_duration_s=0.05)

    assert bursts == [(0.20, 0.75)]


def _analysis_df():
    times = np.round(np.arange(0.0, 2.51, 0.01), 3)
    sample_index = np.arange(len(times))
    rel_t = times - 1.0
    in_burst = (times >= 1.0) & (times <= 1.6)

    rx = 0.025 * np.sin(sample_index * 0.47)
    ry = 0.020 * np.cos(sample_index * 0.41)
    rx = rx + np.where(in_burst, 0.12 * rel_t, 0.0)
    ry = ry + np.where(in_burst, -0.08 * rel_t, 0.0)

    return pd.DataFrame(
        {
            "elapsed_s": times,
            "fire": in_burst,
            "rx": rx,
            "ry": ry,
            "ads": (times >= 0.95) & (times <= 1.0),
            "lx": np.where(times >= 1.2, 0.2, 0.0),
            "ly": np.zeros_like(times),
        }
    )


def test_analyze_burst_returns_core_metrics_and_weapon_window_fields():
    df = _analysis_df()

    metrics = analyzer.analyze_burst(df, 1.0, 1.6, weapon_rpm=1080)

    assert metrics is not None
    assert metrics["burst_start"] == pytest.approx(1.0)
    assert metrics["burst_end"] == pytest.approx(1.6)
    assert metrics["duration"] == pytest.approx(0.6)
    assert metrics["weapon_rpm"] == 1080
    assert metrics["during_window_ms"] == 200
    assert metrics["is_ads"] is True
    assert math.isfinite(metrics["pre_stability"])
    assert math.isfinite(metrics["during_stability"])
    assert {"data", "total_reversals", "dominant_input_low"} <= set(metrics)


def test_analyze_burst_noise_floor_reduces_stability_and_clamps_to_zero():
    df = _analysis_df()

    baseline = analyzer.analyze_burst(df, 1.0, 1.6, weapon_rpm=600)
    denoised = analyzer.analyze_burst(
        df,
        1.0,
        1.6,
        noise_floor_x=10.0,
        noise_floor_y=10.0,
        weapon_rpm=600,
    )

    assert baseline["pre_stability"] > 0
    assert baseline["during_stability"] > 0
    assert denoised["pre_stability"] == 0.0
    assert denoised["during_stability"] == 0.0


def test_analyze_burst_low_rpm_skips_during_stability():
    df = _analysis_df()

    metrics = analyzer.analyze_burst(df, 1.0, 1.6, weapon_rpm=30)

    assert metrics["weapon_rpm"] == 30
    assert metrics["during_window_ms"] == 0
    assert math.isnan(metrics["during_stability"])
