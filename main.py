"""统一启动入口。"""
from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence
from pathlib import Path


def _ensure_src_path() -> None:
    src_dir = Path(__file__).resolve().parent / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _build_parser(*, add_help: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="摇杆射击行为分析工具",
        add_help=add_help,
    )
    parser.add_argument(
        "-args",
        choices=("gui", "cli"),
        default="gui",
        help="启动模式：gui 打开图形界面，cli 分析 CSV（默认 gui）",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _ensure_src_path()
    argv_list = list(sys.argv[1:] if argv is None else argv)
    args, remaining = _build_parser(add_help=False).parse_known_args(argv_list)
    if args.args == "cli":
        analyzer = importlib.import_module("app.compat.analyzer")
        analyzer.main(list(remaining))
        return

    from app.adapters.ui import tkinter_app

    if any(arg in {"-h", "--help"} for arg in argv_list):
        _build_parser().parse_args(argv_list)
        return

    if remaining:
        print(f"[!] GUI 模式忽略未知参数：{' '.join(remaining)}")
    tkinter_app.main()


if __name__ == "__main__":
    main(sys.argv[1:])
