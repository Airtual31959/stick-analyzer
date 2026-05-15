from __future__ import annotations

import sys
from types import ModuleType

import main


def test_main_dispatches_cli_args(monkeypatch):
    captured = {}
    fake_analyzer = ModuleType("app.compat.analyzer")
    fake_analyzer.main = lambda argv: captured.setdefault("argv", argv)
    monkeypatch.setitem(sys.modules, "app.compat.analyzer", fake_analyzer)

    main.main(["-args", "cli", "record.csv", "--max_events", "5"])

    assert captured["argv"] == ["record.csv", "--max_events", "5"]


def test_main_dispatches_cli_help_to_cli_parser(monkeypatch):
    captured = {}
    fake_analyzer = ModuleType("app.compat.analyzer")
    fake_analyzer.main = lambda argv: captured.setdefault("argv", argv)
    monkeypatch.setitem(sys.modules, "app.compat.analyzer", fake_analyzer)

    main.main(["-args", "cli", "--help"])

    assert captured["argv"] == ["--help"]


def test_main_dispatches_gui(monkeypatch):
    from app.adapters.ui import tkinter_app

    captured = {"called": False}
    monkeypatch.setattr(
        tkinter_app,
        "main",
        lambda: captured.update(called=True),
    )

    main.main(["-args", "gui"])

    assert captured["called"] is True
