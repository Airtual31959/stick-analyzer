"""兼容旧入口：实际 Tkinter GUI 实现位于 stick_analyzer.adapters.ui.tkinter_app。"""
import sys

try:
    from stick_analyzer.adapters.ui import tkinter_app as _tkinter_app
except ModuleNotFoundError:
    from src.stick_analyzer.adapters.ui import tkinter_app as _tkinter_app

sys.modules[__name__] = _tkinter_app

if __name__ == "__main__":
    _tkinter_app.main()
