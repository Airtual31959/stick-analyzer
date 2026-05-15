from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.adapters.reporting.text_report_renderer import TextReportRenderer


def test_generate_report_returns_legacy_message_for_empty_events(tmp_path):
    renderer = TextReportRenderer()

    report = renderer.generate_report(
        events=[],
        csv_path=tmp_path / "record.csv",
        metadata={},
        thresholds={},
    )

    assert report == "[!] 没有可分析的事件"


def test_generate_report_renders_non_empty_report_without_optional_plot_deps(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setitem(sys.modules, "pandas", None)
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    renderer = TextReportRenderer()

    report = renderer.generate_report(
        events=[
            {
                "metrics": {
                    "pre_stability": 0.02,
                    "during_stability": 0.02,
                    "total_reversals": 4,
                    "avg_magnitude": 0.25,
                    "duration": 0.6,
                    "is_ads": True,
                    "is_moving": False,
                    "dominant_input_low": 20,
                    "dominant_input_high": 40,
                    "weapon_rpm": 1080,
                    "data": SimpleNamespace(columns=()),
                },
            }
        ],
        csv_path=tmp_path / "r99_record.csv",
        metadata={"weapons": "r99"},
        thresholds={
            "pre_stable": 0.04,
            "pre_unstable": 0.08,
            "during_stable": 0.04,
            "during_unstable": 0.08,
            "rev_bad": 25,
        },
    )

    assert "摇杆射击行为分析报告" in report
    assert "源文件: r99_record.csv" in report
    assert "分析事件总数: 1" in report
    assert "武器射速: 1080 RPM" in report
    assert "开火中分析窗口已自动设为 200ms" in report
    assert "四、行为分类" in report
    assert "完美稳定" in report
    assert "教科书级压枪，准星几乎纹丝不动" in report
    assert "_event_*.png" in report
    assert "_summary.png" in report


def test_generate_report_renders_mixed_mode_sections(tmp_path):
    renderer = TextReportRenderer()

    def event(
        index,
        *,
        pre,
        during,
        revs,
        ads,
        moving,
        mark="",
        burst_start=None,
    ):
        burst_start = float(index) if burst_start is None else burst_start
        return {
            "metrics": {
                "pre_stability": pre,
                "during_stability": during,
                "total_reversals": revs,
                "avg_magnitude": 0.18 + index * 0.01,
                "duration": 0.55,
                "is_ads": ads,
                "is_moving": moving,
                "dominant_input_low": 4 + index,
                "dominant_input_high": 12 + index,
                "weapon_rpm": 1080,
                "large_overshoots": 3 if revs > 20 else 0,
                "small_jitters": 12 if revs > 20 else 2,
                "max_reversal_amplitude": 0.18 if revs > 20 else 0.08,
                "burst_start": burst_start,
                "burst_end": burst_start + 0.55,
                "data": pd.DataFrame(
                    {
                        "elapsed_s": [burst_start, burst_start + 0.2],
                        "mark": ["", mark],
                    }
                ),
            }
        }

    report = renderer.generate_report(
        events=[
            event(1, pre=0.02, during=0.03, revs=4, ads=False, moving=False),
            event(2, pre=0.07, during=0.09, revs=26, ads=True, moving=True, mark="good"),
            event(3, pre=0.05, during=0.07, revs=14, ads=True, moving=False),
            event(4, pre=0.09, during=0.11, revs=30, ads=False, moving=True),
        ],
        csv_path=tmp_path / "mixed.csv",
        metadata={
            "curve": "v5",
            "rc_hipfire": "-3",
            "rc_hipfire_intensity": "light",
            "rc_ads": "-7",
            "rc_ads_intensity": "strong",
            "weapons": "R-99",
            "scene": "训练场",
            "sensor_type": "hall",
            "effective_rate": "180",
            "nominal_rate": "500",
            "duplicate_ratio": "0.20",
            "polling_rate": "1000",
            "noise_floor_x": "0.020",
            "noise_floor_y": "0.018",
        },
        thresholds={
            "pre_stable": 0.04,
            "pre_unstable": 0.08,
            "during_stable": 0.04,
            "during_unstable": 0.08,
            "rev_good": 10,
            "rev_bad": 25,
            "intensity_label": "强增抖",
            "sensor_label": "霍尔",
            "sensor_factor": 1.25,
        },
    )

    assert "七、腰射 vs 开镜 模式不对称分析" in report
    assert "八、走位 vs 站桩 模式对比" in report
    assert "九、今日状态一致性" in report
    assert "十、玩家自评 vs 算法评分对照" in report
    assert "霍尔摇杆且主导推杆区间在 X<10 中心钝化区" in report
    assert "实际有效采样率过低" in report
    assert "主要是小抖动" in report
