"""分析标签页 mixin。"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

try:
    from app.application import AnalyzeRecording, AnalyzeRecordingRequest
    from app.adapters.ui import error_reporter
    from app.adapters.ui.theme import (
        COLOR_ACCENT_MAGENTA,
        COLOR_BG,
        COLOR_LINE,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_MONO,
        entry,
        line_button,
        section,
        set_state,
        show_message,
        solid_button,
        textbox,
    )
except ModuleNotFoundError:
    from src.app.application import AnalyzeRecording, AnalyzeRecordingRequest
    from src.app.adapters.ui import error_reporter
    from src.app.adapters.ui.theme import (
        COLOR_ACCENT_MAGENTA,
        COLOR_BG,
        COLOR_LINE,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_MONO,
        entry,
        line_button,
        section,
        set_state,
        show_message,
        solid_button,
        textbox,
    )


def _import_analyzer():
    try:
        from app.compat import analyzer as analyzer_mod
    except ModuleNotFoundError:
        try:
            from src.app.compat import analyzer as analyzer_mod
        except ModuleNotFoundError:
            return None
    return analyzer_mod


def _get_runtime_attr(name, default):
    for module_name in (
        "app.adapters.ui.tkinter_app",
        "src.app.adapters.ui.tkinter_app",
    ):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return default


class AnalyzeTabMixin:
    """封装分析标签页的 UI 与操作。"""

    def _build_analyze_tab(self, parent):
        file_body = section(parent, "1. 选择 CSV", "使用录制页生成的文件")
        file_body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            file_body,
            text="CSV 文件",
            width=96,
            anchor="e",
            text_color=COLOR_TEXT,
            font=FONT_BODY,
        ).grid(row=0, column=0, sticky="e", padx=(0, 12), pady=6)
        entry(file_body, textvariable=self.csv_path_var).grid(
            row=0, column=1, sticky="ew", pady=6)
        line_button(file_body, "选择", command=self._choose_csv, width=92).grid(
            row=0, column=2, padx=(10, 0), pady=6)

        param_body = section(parent, "2. 分析参数", "默认参数适合大多数压枪记录")
        param_body.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(
            param_body,
            text="最大事件数",
            text_color=COLOR_TEXT,
            font=FONT_BODY,
        ).grid(row=0, column=0, sticky="w", pady=6)
        self.max_events_var = tk.IntVar(value=50)
        entry(param_body, textvariable=self.max_events_var, width=96).grid(
            row=0, column=1, sticky="w", padx=(10, 28), pady=6)
        ctk.CTkLabel(
            param_body,
            text="最短爆发秒数",
            text_color=COLOR_TEXT,
            font=FONT_BODY,
        ).grid(row=0, column=2, sticky="w", pady=6)
        self.min_dur_var = tk.DoubleVar(value=0.05)
        entry(param_body, textvariable=self.min_dur_var, width=96).grid(
            row=0, column=3, sticky="w", padx=(10, 0), pady=6)
        self.analyze_btn = solid_button(
            param_body,
            "开始分析",
            command=self._start_analyze,
            width=150,
        )
        self.analyze_btn.grid(row=0, column=4, sticky="e", pady=6)

        metric_body = section(parent, "3. 关键指标")
        self._analysis_metric_labels = {}
        for idx, (key, label) in enumerate((
            ("events", "分析事件"),
            ("ads", "开镜占比"),
            ("duration", "平均时长"),
            ("stability", "平均稳定度"),
        )):
            card = ctk.CTkFrame(
                metric_body,
                fg_color=COLOR_PANEL,
                border_width=1,
                border_color=COLOR_LINE,
                corner_radius=0,
            )
            card.grid(row=0, column=idx, sticky="ew", padx=(0, 10), pady=4)
            metric_body.grid_columnconfigure(idx, weight=1)
            ctk.CTkLabel(
                card,
                text=label,
                text_color=COLOR_MUTED,
                font=FONT_BODY,
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(12, 0))
            value_label = ctk.CTkLabel(
                card,
                text="--",
                text_color=COLOR_ACCENT_MAGENTA,
                font=(FONT_BODY[0], 28, "bold"),
                anchor="w",
            )
            value_label.pack(anchor="w", padx=14, pady=(2, 12))
            self._analysis_metric_labels[key] = value_label

        result_body = section(parent, "4. 分析日志与报告")
        self.result_text = textbox(result_body, height=280, font=FONT_MONO)
        self.result_text.pack(fill="both", expand=True)

        bottom_frame = ctk.CTkFrame(parent, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=10, pady=(14, 8))
        self.open_dir_btn = line_button(
            bottom_frame,
            "打开输出目录",
            command=self._open_output_dir,
            width=150,
        )
        self.open_dir_btn.pack(side="left")
        set_state(self.open_dir_btn, "disabled")
        self.go_to_ai_btn = solid_button(
            bottom_frame,
            "生成 AI 提示词",
            command=lambda: self._show_page("prompt"),
            width=170,
        )
        self.go_to_ai_btn.pack(side="right")
        set_state(self.go_to_ai_btn, "disabled")

    def _choose_csv(self):
        f = filedialog.askopenfilename(
            initialdir=self.out_dir_var.get(),
            filetypes=[("CSV 文件", "*.csv")])
        if f:
            self.csv_path_var.set(f)

    def _start_analyze(self):
        csv_path = self.csv_path_var.get()
        if not csv_path or not Path(csv_path).exists():
            show_message("error", "无法分析", "请先选择有效的 CSV 文件", parent=self)
            return

        set_state(self.analyze_btn, "disabled")
        set_state(self.go_to_ai_btn, "disabled")
        self.result_text.delete("1.0", "end")
        self._result_log(f"开始分析 {Path(csv_path).name}...")

        threading.Thread(
            target=self._run_analyzer,
            args=(csv_path, self.max_events_var.get(), self.min_dur_var.get()),
            daemon=True).start()

    def _run_analyzer(self, csv_path, max_events, min_dur):
        try:
            import_analyzer = _get_runtime_attr("_import_analyzer", _import_analyzer)
            analyze_recording = _get_runtime_attr("AnalyzeRecording", AnalyzeRecording)
            request_cls = _get_runtime_attr(
                "AnalyzeRecordingRequest", AnalyzeRecordingRequest)

            if import_analyzer() is None:
                self.after(0, self._result_log,
                           "[错误] 找不到分析模块，请确认程序文件完整")
                return

            request = request_cls(
                csv_path=Path(csv_path),
                max_events=max_events,
                min_duration_s=min_dur,
            )
            result = analyze_recording().execute(
                request,
                progress=self._queue_analysis_progress,
            )
            self.after(0, self._handle_analysis_success, result)

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.after(0, self._result_log, f"\n[错误] {e}\n{err}")
            if error_reporter is not None:
                exc = e
                self.after(0, lambda: error_reporter.show_error_dialog(
                    self, "分析失败", str(exc), exc,
                    f"分析 CSV 文件: {csv_path}"))

        finally:
            self.after(0, lambda: set_state(self.analyze_btn, "normal"))

    def _queue_analysis_progress(self, progress):
        self.after(0, self._result_log, progress.message)

    def _handle_analysis_success(self, result):
        self._result_log("\n" + "=" * 50)
        self._result_log("分析完成！\n")
        self._result_log(result.report_text)
        self._result_log(f"\n报告：{result.report_path}")
        self._result_log(f"总览图：{result.summary_image_path}")

        self.last_report_content = result.report_text
        self._last_output_dir = result.report_path.parent

        set_state(self.open_dir_btn, "normal")
        set_state(self.go_to_ai_btn, "normal")
        if hasattr(self, "_refresh_analysis_metrics"):
            self._refresh_analysis_metrics(result)
        self._refresh_prompt_template()

    def _refresh_analysis_metrics(self, result):
        labels = getattr(self, "_analysis_metric_labels", None)
        if not labels:
            return
        metrics = [event.get("metrics") for event in getattr(result, "events", ())
                   if event.get("metrics") is not None]
        count = len(metrics)
        ads_count = sum(1 for metric in metrics if metric.get("is_ads"))
        durations = [float(metric.get("duration", 0.0) or 0.0)
                     for metric in metrics]
        stabilities = []
        for metric in metrics:
            try:
                value = float(metric.get("during_stability"))
            except (TypeError, ValueError):
                continue
            if value == value:
                stabilities.append(value)
        avg_duration = sum(durations) / count if count else 0.0
        avg_stability = sum(stabilities) / len(stabilities) if stabilities else 0.0
        values = {
            "events": f"{count}",
            "ads": f"{ads_count / count * 100:.0f}%" if count else "--",
            "duration": f"{avg_duration:.2f}s" if count else "--",
            "stability": f"{avg_stability:.4f}" if stabilities else "--",
        }
        for key, value in values.items():
            labels[key].configure(text=value)

    def _open_output_dir(self):
        if hasattr(self, "_last_output_dir"):
            try:
                if sys.platform == "win32":
                    os.startfile(self._last_output_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(self._last_output_dir)], check=False)
                else:
                    subprocess.run(["xdg-open", str(self._last_output_dir)], check=False)
            except Exception as e:
                show_message("error", "无法打开目录", str(e), parent=self)

    def _result_log(self, msg):
        self.result_text.insert("end", msg + "\n")
        self.result_text.see("end")
