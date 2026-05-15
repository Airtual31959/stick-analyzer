from __future__ import annotations

from pathlib import Path

from app.packaging import build_exe


def test_build_constructs_pyinstaller_command(monkeypatch):
    captured = {}

    def fake_check_call(cmd, cwd=None):
        captured["cmd"] = cmd
        captured["cwd"] = cwd

    monkeypatch.setattr(build_exe.subprocess, "check_call", fake_check_call)

    build_exe.build("onedir")

    cmd = captured["cmd"]
    assert cmd[:3] == [build_exe.sys.executable, "-m", "PyInstaller"]
    assert "--onedir" in cmd
    assert "--windowed" in cmd
    assert "--collect-submodules=app" in cmd
    assert f"--paths={build_exe.SRC_DIR}" in cmd
    assert "--hidden-import=app.compat.analyzer" in cmd
    assert cmd[-1] == "main.py"
    assert captured["cwd"] == build_exe.PROJECT_DIR


def test_choose_mode_defaults_to_onedir(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    assert build_exe.choose_mode() == "onedir"


def test_choose_mode_accepts_onefile(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")

    assert build_exe.choose_mode() == "onefile"


def test_show_result_onedir_reports_existing_output(monkeypatch, tmp_path):
    project_dir = tmp_path
    out_dir = project_dir / "dist" / "StickAnalyzer"
    out_dir.mkdir(parents=True)
    (out_dir / "StickAnalyzer.exe").write_bytes(b"exe")
    (out_dir / "_internal.dat").write_bytes(b"data")

    monkeypatch.setattr(build_exe, "PROJECT_DIR", project_dir)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    build_exe.show_result("onedir")


def test_show_result_onefile_reports_existing_exe(monkeypatch, tmp_path):
    project_dir = Path(tmp_path)
    dist_dir = project_dir / "dist"
    dist_dir.mkdir()
    (dist_dir / "StickAnalyzer.exe").write_bytes(b"exe")

    monkeypatch.setattr(build_exe, "PROJECT_DIR", project_dir)

    build_exe.show_result("onefile")
