from __future__ import annotations

import importlib
import math
import sys
import types
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _install_analyzer_import_fakes(monkeypatch):
    fake_numpy = types.ModuleType("numpy")
    fake_numpy.isnan = math.isnan

    fake_pandas = types.ModuleType("pandas")
    fake_pandas.DataFrame = type("DataFrame", (), {})

    fake_matplotlib = types.ModuleType("matplotlib")
    fake_matplotlib.__path__ = []
    fake_matplotlib.rcParams = {}
    fake_matplotlib.use = lambda backend: None

    fake_pyplot = types.ModuleType("matplotlib.pyplot")
    fake_font_manager = types.ModuleType("matplotlib.font_manager")
    fake_font_manager.fontManager = types.SimpleNamespace(
        ttflist=[types.SimpleNamespace(name="Microsoft YaHei")],
        addfont=lambda path: None,
    )
    fake_matplotlib.pyplot = fake_pyplot
    fake_matplotlib.font_manager = fake_font_manager

    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setitem(sys.modules, "pandas", fake_pandas)
    monkeypatch.setitem(sys.modules, "matplotlib", fake_matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_pyplot)
    monkeypatch.setitem(sys.modules, "matplotlib.font_manager", fake_font_manager)


@pytest.fixture
def analyzer_cli(monkeypatch):
    module_name = "app.compat.analyzer"
    previous_analyzer = sys.modules.pop(module_name, None)
    _install_analyzer_import_fakes(monkeypatch)
    module = importlib.import_module(module_name)
    try:
        yield module
    finally:
        sys.modules.pop(module_name, None)
        if previous_analyzer is not None:
            sys.modules[module_name] = previous_analyzer


def test_main_calls_analyze_recording_with_current_module_and_prints_result(
    analyzer_cli,
    monkeypatch,
    tmp_path,
    capsys,
):
    csv_path = tmp_path / "record.csv"
    csv_path.write_text("elapsed_s,fire\n", encoding="utf-8")

    instances = []

    class FakeAnalyzeRecording:
        def __init__(self, analyzer=None, report_writer=None):
            self.analyzer = analyzer
            self.report_writer = report_writer
            self.request = None
            instances.append(self)

        def execute(self, request, progress=None):
            self.request = request
            progress(types.SimpleNamespace(
                step="detect_bursts",
                message="检测到 1 次开火爆发",
                current=None,
                total=None,
            ))
            progress(types.SimpleNamespace(
                step="noise_floor",
                message="应用硬件本底校准：X=0.01000  Y=0.02000",
                current=None,
                total=None,
            ))
            progress(types.SimpleNamespace(
                step="weapon",
                message="武器识别：R-99（1080 RPM，开火中窗口=200ms）",
                current=None,
                total=None,
            ))
            progress(types.SimpleNamespace(
                step="analyze_burst",
                message="正在分析第 1/1 次开火",
                current=1,
                total=1,
            ))
            return types.SimpleNamespace(
                events=(
                    {
                        "index": 1,
                        "metrics": {
                            "burst_start": 1.23,
                            "pre_stability": 0.0112,
                            "during_stability": 0.0223,
                            "total_reversals": 4,
                        },
                        "classification": "稳定射击",
                    },
                ),
                report_text="报告正文",
                report_path=tmp_path / "record_report.txt",
                summary_image_path=tmp_path / "record_summary.png",
            )

    monkeypatch.setattr(analyzer_cli, "AnalyzeRecording", FakeAnalyzeRecording)

    analyzer_cli.main([
        str(csv_path),
        "--max_events",
        "5",
        "--min_duration",
        "0.2",
    ])

    output = capsys.readouterr().out
    assert instances[0].analyzer is analyzer_cli
    assert instances[0].request.csv_path == csv_path
    assert instances[0].request.max_events == 5
    assert instances[0].request.min_duration_s == 0.2
    assert "[*] 检测到 1 次开火爆发" in output
    assert "[√] 应用硬件本底校准：X=0.01000  Y=0.02000" in output
    assert "[√] 武器识别：R-99（1080 RPM，开火中窗口=200ms）" in output
    assert "[*] 开始分析..." in output
    assert "前稳=0.0112 | 中稳=0.0223 | 反转=  4" in output
    assert f"[√] 总览图：{tmp_path / 'record_summary.png'}" in output
    assert "报告正文" in output
    assert f"[√] 报告已保存：{tmp_path / 'record_report.txt'}" in output


def test_main_exits_when_csv_is_missing(analyzer_cli, tmp_path, capsys):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(SystemExit) as exc_info:
        analyzer_cli.main([str(missing_path)])

    assert exc_info.value.code == 1
    assert f"[X] 找不到文件：{missing_path}" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("exception_name", "expected_lines"),
    [
        (
            "MissingFireColumnError",
            ["[X] CSV 缺少 fire 列，请用本工具最新版本重新录制"],
        ),
        (
            "NoFireBurstsError",
            [
                "[X] 没有检测到任何开火事件",
                "请确认 GUI 中的 FIRE_BUTTON 配置正确",
                "（你的开火键应配置为 RIGHT_SHOULDER）",
            ],
        ),
    ],
)
def test_main_exits_for_analyze_input_errors(
    analyzer_cli,
    monkeypatch,
    tmp_path,
    capsys,
    exception_name,
    expected_lines,
):
    csv_path = tmp_path / "record.csv"
    csv_path.write_text("elapsed_s,fire\n", encoding="utf-8")
    error_type = getattr(analyzer_cli, exception_name)

    class FakeAnalyzeRecording:
        def __init__(self, analyzer=None, report_writer=None):
            pass

        def execute(self, request, progress=None):
            raise error_type("测试错误")

    monkeypatch.setattr(analyzer_cli, "AnalyzeRecording", FakeAnalyzeRecording)

    with pytest.raises(SystemExit) as exc_info:
        analyzer_cli.main([str(csv_path)])

    output = capsys.readouterr().out
    assert exc_info.value.code == 1
    for line in expected_lines:
        assert line in output
