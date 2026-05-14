from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stick_analyzer.adapters.reporting.text_report_renderer import TextReportRenderer


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
