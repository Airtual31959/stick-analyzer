"""分析标签页 mixin。"""
import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from stick_analyzer.application import AnalyzeRecording, AnalyzeRecordingRequest
except ModuleNotFoundError:
    from src.stick_analyzer.application import AnalyzeRecording, AnalyzeRecordingRequest

try:
    import error_reporter
except ImportError:
    error_reporter = None


def _import_analyzer():
    try:
        import analyzer as analyzer_mod
        return analyzer_mod
    except ImportError:
        return None


def _get_runtime_attr(name, default):
    for module_name in (
        "stick_analyzer.adapters.ui.tkinter_app",
        "src.stick_analyzer.adapters.ui.tkinter_app",
        "main_gui",
    ):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return default


class AnalyzeTabMixin:
    """封装分析标签页的 UI 与操作。"""

    def _build_analyze_tab(self, parent):
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(file_frame, text="CSV 文件:").pack(side="left")
        ttk.Entry(file_frame, textvariable=self.csv_path_var, width=50).pack(
            side="left", padx=5, fill="x", expand=True)
        ttk.Button(file_frame, text="选择...",
                   command=self._choose_csv).pack(side="left")

        param_frame = ttk.LabelFrame(parent, text="分析参数（一般保持默认即可）", padding=10)
        param_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(param_frame, text="最大事件数:").grid(row=0, column=0, sticky="e")
        self.max_events_var = tk.IntVar(value=50)
        ttk.Spinbox(param_frame, from_=5, to=200, increment=5,
                    textvariable=self.max_events_var, width=10).grid(
            row=0, column=1, sticky="w", padx=5)

        ttk.Label(param_frame, text="最短爆发(秒):").grid(
            row=0, column=2, sticky="e", padx=10)
        self.min_dur_var = tk.DoubleVar(value=0.05)
        ttk.Spinbox(param_frame, from_=0.0, to=2.0, increment=0.05,
                    textvariable=self.min_dur_var, width=10).grid(
            row=0, column=3, sticky="w", padx=5)

        param_hint = (
            "● 最大事件数：最多分析多少次开火。事件太多会生成很多张图，"
            "默认 50 够用，不用改。\n"
            "● 最短爆发(秒)：开火持续多久才算一次有效射击，"
            "用于过滤误触（比如手抖按了一下就松开）。\n"
            "  默认 0.05 秒适合大多数情况，不用改。"
            "如果你专门用栓狙单点射，可以调到 0.0 让单发也被分析。"
        )
        ttk.Label(param_frame, text=param_hint, foreground="#666",
                  font=("", 8), justify="left").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=5, pady=(8, 2))

        self.analyze_btn = ttk.Button(parent, text="▶ 开始分析",
                                      command=self._start_analyze)
        self.analyze_btn.pack(pady=10)

        result_frame = ttk.LabelFrame(parent, text="分析结果", padding=10)
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.result_text = scrolledtext.ScrolledText(
            result_frame, height=15, font=("Consolas", 9))
        self.result_text.pack(fill="both", expand=True)

        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(pady=5)
        self.open_dir_btn = ttk.Button(bottom_frame, text="📁 打开输出目录",
                                       command=self._open_output_dir,
                                       state="disabled")
        self.open_dir_btn.pack(side="left", padx=5)
        self.go_to_ai_btn = ttk.Button(
            bottom_frame, text="→ 下一步：生成 AI 调参提示词",
            command=lambda: self.notebook.select(2),
            state="disabled")
        self.go_to_ai_btn.pack(side="left", padx=5)

    def _choose_csv(self):
        f = filedialog.askopenfilename(
            initialdir=self.out_dir_var.get(),
            filetypes=[("CSV 文件", "*.csv")])
        if f:
            self.csv_path_var.set(f)

    def _start_analyze(self):
        csv_path = self.csv_path_var.get()
        if not csv_path or not Path(csv_path).exists():
            messagebox.showerror("错误", "请先选择有效的 CSV 文件")
            return

        self.analyze_btn["state"] = "disabled"
        self.go_to_ai_btn["state"] = "disabled"
        self.result_text.delete(1.0, "end")
        self._result_log(f"开始分析 {Path(csv_path).name}...\n")

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
                           "[错误] 找不到 analyzer.py，请确认它和本程序在同一目录")
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
            self.after(0, lambda: self.analyze_btn.configure(state="normal"))

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

        self.open_dir_btn.configure(state="normal")
        self.go_to_ai_btn.configure(state="normal")
        self._refresh_prompt_template()

    def _open_output_dir(self):
        if hasattr(self, "_last_output_dir"):
            try:
                if sys.platform == "win32":
                    os.startfile(self._last_output_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(self._last_output_dir)])
                else:
                    subprocess.run(["xdg-open", str(self._last_output_dir)])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录: {e}")

    def _result_log(self, msg):
        self.result_text.insert("end", msg + "\n")
        self.result_text.see("end")
