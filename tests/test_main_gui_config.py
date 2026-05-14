from pathlib import Path

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
