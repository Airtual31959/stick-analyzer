from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from stick_analyzer.application import AnalyzeRecording, AnalyzeRecordingRequest
from stick_analyzer.application.use_cases import (
    MissingFireColumnError,
    NoFireBurstsError,
)


class FakeFrame:
    def __init__(self, columns):
        self.columns = columns


class FakeReportWriter:
    def __init__(self):
        self.writes = []

    def write_text(self, path, content):
        self.writes.append((path, content))


class FakeAnalyzer:
    def __init__(
        self,
        columns=("elapsed_s", "fire"),
        bursts=((1.0, 1.2), (2.0, 2.4)),
        metadata=None,
    ):
        self.columns = columns
        self.bursts = list(bursts)
        self.metadata = metadata or {
            "noise_floor_x": "0.010",
            "noise_floor_y": "0.020",
            "weapons": "R-99",
        }
        self.analyzed_bursts = []
        self.event_plots = []
        self.summary_plots = []
        self.report_inputs = []

    def load_csv(self, path):
        return FakeFrame(self.columns), self.metadata

    def get_stability_thresholds(self, metadata):
        return {"pre_stable": 0.04, "metadata": metadata}

    def detect_fire_bursts(self, df, min_duration_s):
        return self.bursts

    def detect_weapon_rpm(self, weapons_str):
        return 1080 if weapons_str else 0

    def rpm_to_during_window_ms(self, rpm):
        return 200 if rpm > 900 else 300

    def analyze_burst(
        self,
        df,
        burst_start,
        burst_end,
        noise_floor_x=0.0,
        noise_floor_y=0.0,
        weapon_rpm=0,
    ):
        self.analyzed_bursts.append({
            "burst_start": burst_start,
            "burst_end": burst_end,
            "noise_floor_x": noise_floor_x,
            "noise_floor_y": noise_floor_y,
            "weapon_rpm": weapon_rpm,
        })
        return {
            "duration": burst_end - burst_start,
            "is_ads": True,
            "pre_stability": 0.01,
            "during_stability": 0.02,
            "total_reversals": 3,
            "burst_start": burst_start,
            "burst_end": burst_end,
        }

    def classify_burst(self, metrics):
        return f"分类-{metrics['burst_start']:.1f}"

    def plot_burst(self, metrics, output_path, title):
        self.event_plots.append((metrics, output_path, title))

    def plot_summary(self, events, output_path):
        self.summary_plots.append((list(events), output_path))

    def generate_report(self, events, csv_path, metadata, thresholds):
        self.report_inputs.append((list(events), csv_path, metadata, thresholds))
        return "测试报告"


def test_execute_returns_legacy_output_paths_and_writes_report(tmp_path):
    analyzer = FakeAnalyzer()
    writer = FakeReportWriter()
    progress_events = []

    result = AnalyzeRecording(analyzer, writer).execute(
        AnalyzeRecordingRequest(
            csv_path=tmp_path / "stick_log.csv",
            max_events=10,
            min_duration_s=0.1,
        ),
        progress_events.append,
    )

    assert result.source_path == tmp_path / "stick_log.csv"
    assert result.report_path == tmp_path / "stick_log_report.txt"
    assert result.summary_image_path == tmp_path / "stick_log_summary.png"
    assert result.event_image_paths == (
        tmp_path / "stick_log_event_01.png",
        tmp_path / "stick_log_event_02.png",
    )
    assert result.report_text == "测试报告"
    assert writer.writes == [(tmp_path / "stick_log_report.txt", "测试报告")]
    assert [event["index"] for event in result.events] == [1, 2]
    assert [call["noise_floor_x"] for call in analyzer.analyzed_bursts] == [0.01, 0.01]
    assert [call["weapon_rpm"] for call in analyzer.analyzed_bursts] == [1080, 1080]
    assert analyzer.summary_plots[0][1] == tmp_path / "stick_log_summary.png"
    assert progress_events[-1].message == "分析完成"


def test_execute_truncates_to_last_max_events(tmp_path):
    analyzer = FakeAnalyzer(
        bursts=((1.0, 1.1), (2.0, 2.1), (3.0, 3.1), (4.0, 4.1)),
    )
    progress_events = []

    result = AnalyzeRecording(analyzer, FakeReportWriter()).execute(
        AnalyzeRecordingRequest(tmp_path / "record.csv", max_events=2),
        progress_events.append,
    )

    assert [call["burst_start"] for call in analyzer.analyzed_bursts] == [3.0, 4.0]
    assert [event["index"] for event in result.events] == [1, 2]
    assert result.event_image_paths == (
        tmp_path / "record_event_01.png",
        tmp_path / "record_event_02.png",
    )
    assert any("事件过多，仅分析最后 2 次" in event.message for event in progress_events)


def test_execute_raises_when_fire_column_is_missing(tmp_path):
    analyzer = FakeAnalyzer(columns=("elapsed_s", "rx", "ry"))

    with pytest.raises(MissingFireColumnError, match="fire 列"):
        AnalyzeRecording(analyzer, FakeReportWriter()).execute(
            AnalyzeRecordingRequest(tmp_path / "record.csv")
        )

    assert analyzer.analyzed_bursts == []


def test_execute_raises_when_no_fire_bursts_detected(tmp_path):
    analyzer = FakeAnalyzer(bursts=())

    with pytest.raises(NoFireBurstsError, match="没有检测到任何开火事件"):
        AnalyzeRecording(analyzer, FakeReportWriter()).execute(
            AnalyzeRecordingRequest(tmp_path / "record.csv")
        )

    assert analyzer.analyzed_bursts == []

