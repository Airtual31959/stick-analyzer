"""CSV 分析命令行入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ...application import (
    AnalysisResult,
    AnalyzeRecording,
    AnalyzeRecordingRequest,
)
from ...application.use_cases import (
    MissingFireColumnError,
    NoFireBurstsError,
)
from ...domain.constants import DEFAULT_MIN_DURATION_S


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="摇杆数据分析器")
    parser.add_argument("csv_file", help="stick_logger 输出的 CSV 文件")
    parser.add_argument(
        "--max_events",
        type=int,
        default=20,
        help="最多分析多少个事件（默认20，避免图太多）",
    )
    parser.add_argument(
        "--min_duration",
        type=float,
        default=DEFAULT_MIN_DURATION_S,
        help="最短爆发持续秒数，过滤误触（默认0.05）",
    )
    return parser


def print_analysis_progress(progress: Any) -> None:
    if progress.step == "detect_bursts":
        print(f"[*] {progress.message}")
    elif progress.step == "truncate_bursts":
        print(f"[!] {progress.message}")
    elif progress.step in {"noise_floor", "weapon"}:
        print(f"[√] {progress.message}")
    elif progress.step == "analyze_burst" and progress.current == 1:
        print("[*] 开始分析...")


def format_metric_value(value: Any) -> str:
    try:
        if np.isnan(value):
            return "N/A"
    except TypeError:
        return "N/A"
    return f"{value:.4f}"


def print_event_summaries(result: AnalysisResult) -> None:
    total = len(result.events)
    for position, event in enumerate(result.events, 1):
        metrics = event["metrics"]
        classification = str(event["classification"])
        event_index = int(event.get("index", position))
        burst_start = float(metrics.get("burst_start", 0.0))
        pre_str = format_metric_value(metrics.get("pre_stability"))
        dur_str = format_metric_value(metrics.get("during_stability"))
        reversals = int(metrics.get("total_reversals", 0))
        print(
            f"  [{event_index}/{total}] @ {burst_start:6.2f}s | "
            f"{classification:18} | 前稳={pre_str} | 中稳={dur_str} | "
            f"反转={reversals:3d}"
        )


def print_analysis_result(result: AnalysisResult) -> None:
    print_event_summaries(result)
    print(f"[√] 总览图：{result.summary_image_path}")
    print()
    print(result.report_text)
    print()
    print(f"[√] 报告已保存：{result.report_path}")


def main(
    argv: list[str] | None = None,
    *,
    analyzer_module: Any | None = None,
    analyze_recording_cls: type[AnalyzeRecording] = AnalyzeRecording,
) -> None:
    args = build_arg_parser().parse_args(argv)

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"[X] 找不到文件：{csv_path}")
        sys.exit(1)

    request = AnalyzeRecordingRequest(
        csv_path=csv_path,
        max_events=args.max_events,
        min_duration_s=args.min_duration,
    )

    use_case = analyze_recording_cls(analyzer=analyzer_module)
    try:
        result = use_case.execute(request, print_analysis_progress)
    except MissingFireColumnError:
        print("[X] CSV 缺少 fire 列，请用本工具最新版本的 stick_logger.py 重新录制")
        sys.exit(1)
    except NoFireBurstsError:
        print("[X] 没有检测到任何开火事件")
        print("    请确认 stick_logger.py 顶部的 FIRE_BUTTON 配置正确")
        print("    （你的开火键应配置为 RIGHT_SHOULDER）")
        sys.exit(1)

    print_analysis_result(result)
