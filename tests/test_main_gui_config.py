from pathlib import Path
from types import SimpleNamespace

import main_gui
from stick_analyzer import app_paths


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _ConfigOwner:
    def __init__(self):
        self._config_ready = True
        self.config = {"welcome_seen": True}
        self.fire_button_var = _Var("TRIGGER_RIGHT")
        self.ads_button_var = _Var("TRIGGER_LEFT")
        self.mark_button_var = _Var("BACK")
        self.perf_profile_var = _Var("normal")
        self.out_dir_var = _Var(r"C:\StickAnalyzerData")
        self.saved = None

    def _save_config(self, cfg):
        self.saved = cfg


class _Button:
    def __init__(self):
        self.state = None

    def configure(self, **kwargs):
        self.state = kwargs.get("state", self.state)


class _AnalysisOwner:
    _queue_analysis_progress = main_gui.App._queue_analysis_progress
    _handle_analysis_success = main_gui.App._handle_analysis_success

    def __init__(self):
        self.logs = []
        self.after_calls = []
        self.analyze_btn = _Button()
        self.open_dir_btn = _Button()
        self.go_to_ai_btn = _Button()
        self.last_report_content = None
        self.prompt_refreshed = False

    def after(self, delay, callback, *args):
        self.after_calls.append((delay, callback, args))
        callback(*args)

    def _result_log(self, msg):
        self.logs.append(msg)

    def _refresh_prompt_template(self):
        self.prompt_refreshed = True


def test_default_output_dir_uses_app_data_subdirectory(tmp_path):
    app_data_dir = Path(tmp_path) / ".stickanalyzer"
    expected = Path(tmp_path) / ".stickanalyzer" / "data"

    assert app_paths.get_app_data_dir(tmp_path) == app_data_dir
    assert app_paths.get_config_path(tmp_path) == app_data_dir / "config.json"
    assert app_paths.get_default_output_dir(tmp_path) == expected
    assert app_paths.resolve_output_dir({}, tmp_path) == expected
    assert main_gui.get_app_data_dir(tmp_path) == app_data_dir
    assert main_gui.get_config_path(tmp_path) == app_data_dir / "config.json"
    assert main_gui.get_default_output_dir(tmp_path) == (
        Path(tmp_path) / ".stickanalyzer" / "data"
    )
    assert main_gui.resolve_output_dir({}, tmp_path) == (
        Path(tmp_path) / ".stickanalyzer" / "data"
    )


def test_resolve_output_dir_keeps_saved_directory():
    cfg = {"out_dir": "~/custom-stick-data"}

    assert str(app_paths.resolve_output_dir(cfg)).endswith("custom-stick-data")
    assert str(main_gui.resolve_output_dir(cfg)).endswith("custom-stick-data")


def test_persist_user_config_saves_key_mapping_and_output_dir():
    owner = _ConfigOwner()

    main_gui.App._persist_user_config(owner)

    assert owner.saved == {
        "welcome_seen": True,
        "fire_button": "TRIGGER_RIGHT",
        "ads_button": "TRIGGER_LEFT",
        "mark_button": "BACK",
        "perf_profile": "normal",
        "out_dir": r"C:\StickAnalyzerData",
    }


def test_run_analyzer_uses_application_use_case_and_updates_gui_state(
    monkeypatch,
    tmp_path,
):
    owner = _AnalysisOwner()
    recorded = {}

    class FakeAnalyzeRecording:
        def execute(self, request, progress=None):
            recorded["request"] = request
            progress(SimpleNamespace(message="进度消息"))
            return SimpleNamespace(
                report_text="测试报告",
                report_path=tmp_path / "record_report.txt",
                summary_image_path=tmp_path / "record_summary.png",
            )

    monkeypatch.setattr(main_gui, "_import_analyzer", lambda: object())
    monkeypatch.setattr(main_gui, "AnalyzeRecording", FakeAnalyzeRecording)

    main_gui.App._run_analyzer(owner, tmp_path / "record.csv", 3, 0.25)

    request = recorded["request"]
    assert request.csv_path == tmp_path / "record.csv"
    assert request.max_events == 3
    assert request.min_duration_s == 0.25
    assert any(
        callback.__name__ == "_result_log" and args == ("进度消息",)
        for _, callback, args in owner.after_calls
    )
    assert "测试报告" in owner.logs
    assert f"\n报告：{tmp_path / 'record_report.txt'}" in owner.logs
    assert owner.last_report_content == "测试报告"
    assert owner._last_output_dir == tmp_path
    assert owner.open_dir_btn.state == "normal"
    assert owner.go_to_ai_btn.state == "normal"
    assert owner.analyze_btn.state == "normal"
    assert owner.prompt_refreshed is True


def test_run_analyzer_keeps_missing_analyzer_message(monkeypatch):
    owner = _AnalysisOwner()
    recorded = {"constructed": False}

    class FakeAnalyzeRecording:
        def __init__(self):
            recorded["constructed"] = True

    monkeypatch.setattr(main_gui, "_import_analyzer", lambda: None)
    monkeypatch.setattr(main_gui, "AnalyzeRecording", FakeAnalyzeRecording)

    main_gui.App._run_analyzer(owner, "missing.csv", 3, 0.25)

    assert owner.logs == ["[错误] 找不到 analyzer.py，请确认它和本程序在同一目录"]
    assert owner.analyze_btn.state == "normal"
    assert recorded["constructed"] is False
