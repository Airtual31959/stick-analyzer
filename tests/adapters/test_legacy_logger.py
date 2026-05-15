from __future__ import annotations

import importlib
import sys
import types

import pytest


@pytest.fixture
def legacy_logger(monkeypatch):
    module_name = "app.adapters.cli.legacy_logger"
    previous = sys.modules.pop(module_name, None)
    fake_xinput = types.ModuleType("XInput")
    fake_xinput.get_connected = lambda: [False, True, False, False]
    monkeypatch.setitem(sys.modules, "XInput", fake_xinput)
    module = importlib.import_module(module_name)
    try:
        yield module
    finally:
        sys.modules.pop(module_name, None)
        if previous is not None:
            sys.modules[module_name] = previous


def test_find_controller_returns_first_connected_index(legacy_logger):
    assert legacy_logger.find_controller() == 1


def test_is_button_pressed_supports_buttons_and_triggers(legacy_logger):
    buttons = {"A": True, "B": False}

    assert legacy_logger.is_button_pressed("A", buttons, lt=0.0, rt=0.0) is True
    assert legacy_logger.is_button_pressed("B", buttons, lt=0.0, rt=0.0) is False
    assert legacy_logger.is_button_pressed("TRIGGER_LEFT", buttons, lt=0.51, rt=0.0) is True
    assert legacy_logger.is_button_pressed("TRIGGER_RIGHT", buttons, lt=0.0, rt=0.49) is False


def test_main_exits_when_no_controller(monkeypatch, legacy_logger, capsys):
    legacy_logger.XInput.get_connected = lambda: [False, False, False, False]
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    with pytest.raises(SystemExit) as exc_info:
        legacy_logger.main()

    assert exc_info.value.code == 1
    assert "未检测到任何手柄" in capsys.readouterr().out
