"""录制标签页 mixin。"""
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from stick_analyzer.app_paths import resolve_output_dir
    from stick_analyzer.application import CalibrationRequest, CalibrateController
    from stick_analyzer.adapters.ui.controller_panel import ControllerPanelMixin
except ModuleNotFoundError:
    from src.stick_analyzer.app_paths import resolve_output_dir
    from src.stick_analyzer.application import CalibrationRequest, CalibrateController
    from src.stick_analyzer.adapters.ui.controller_panel import ControllerPanelMixin

try:
    import controller_backend as cb
except ImportError:
    cb = None

try:
    import error_reporter
except ImportError:
    error_reporter = None

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


def _runtime_cb():
    return _get_runtime_attr("cb", cb)


def _runtime_error_reporter():
    return _get_runtime_attr("error_reporter", error_reporter)


class RecordTabMixin(ControllerPanelMixin):
    """封装录制标签页的 UI 与操作。"""

    # ========== 标签 1：录制 ==========
    def _build_record_tab(self, parent):
        self._build_controller_panel(parent)
        self._build_key_mapping_panel(parent)

        # ====== 性能模式（如果电脑卡可调低）======
        perf_frame = ttk.LabelFrame(parent, text="性能模式", padding=10)
        perf_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(perf_frame, text="采样精度:", width=14).grid(
            row=0, column=0, sticky="e", padx=5, pady=2)
        self.perf_profile_var = tk.StringVar(
            value=self.config.get("perf_profile", "high"))
        perf_options = [
            ("⚡ 高精度（默认，500Hz）- 推荐配置较好的电脑", "high"),
            ("🔋 平衡（250Hz）- 大多数电脑", "normal"),
            ("🐢 低性能（125Hz）- 老电脑或同时运行 Apex 卡顿时", "low"),
        ]
        self._perf_options = perf_options
        perf_combo = ttk.Combobox(perf_frame,
                                   values=[o[0] for o in perf_options],
                                   state="readonly", width=50)
        perf_codes = [o[1] for o in perf_options]
        current_perf = self.perf_profile_var.get()
        if current_perf not in perf_codes:
            current_perf = "high"
            self.perf_profile_var.set(current_perf)
        perf_combo.current(perf_codes.index(current_perf))
        perf_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        perf_combo.bind("<<ComboboxSelected>>",
                        lambda e: self._on_perf_change(perf_combo))
        self.perf_combo = perf_combo

        ttk.Label(perf_frame,
                  text="提示：录制时如果游戏掉帧或电脑卡顿，请切换到「低性能」模式。\n"
                       "采样率降低不会显著影响分析准确度（200Hz 就足够压枪分析）。",
                  foreground="#666", font=("", 8), justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # 元数据输入区
        meta_frame = ttk.LabelFrame(
            parent, text="本次记录元数据（建议填写）", padding=10)
        meta_frame.pack(fill="x", padx=10, pady=5)

        self.meta_vars = {}

        # ===== [T1.1] 摇杆传感器类型 + 回报率 =====
        sensor_row = ttk.Frame(meta_frame)
        sensor_row.pack(fill="x", pady=(0, 6))
        ttk.Label(sensor_row, text="摇杆传感器类型:",
                  width=16).pack(side="left", padx=5)

        sensor_options = [
            ("TMR（主流 FPS 默认）", "tmr"),
            ("碳膜 ALPS（传统）", "alps"),
            ("霍尔（非主流，钝）", "hall"),
            ("不确定（按 TMR）", "tmr"),
        ]
        # 默认选 TMR（第 1 个选项，当前主流）
        v_sensor_label = tk.StringVar(value=sensor_options[0][0])
        v_sensor_code = tk.StringVar(value="tmr")
        self.meta_vars["sensor_type"] = v_sensor_code

        def _sync_sensor_code(*_):
            label = v_sensor_label.get()
            for lbl, code in sensor_options:
                if lbl == label:
                    v_sensor_code.set(code)
                    return
        v_sensor_label.trace_add("write", _sync_sensor_code)

        ttk.Combobox(sensor_row, textvariable=v_sensor_label,
                     values=[o[0] for o in sensor_options],
                     state="readonly", width=28).pack(side="left", padx=5)

        # 回报率输入
        ttk.Label(sensor_row, text="回报率:").pack(side="left", padx=(15, 2))
        v_polling = tk.StringVar(value="1000")
        self.meta_vars["polling_rate"] = v_polling
        ttk.Entry(sensor_row, textvariable=v_polling, width=6).pack(
            side="left", padx=2)
        ttk.Label(sensor_row, text="Hz",
                  foreground="#666").pack(side="left", padx=(0, 4))
        ttk.Label(sensor_row,
                  text="（手柄向电脑发数据的频率，常见 125/250/500/1000）",
                  foreground="#888", font=("", 8)).pack(side="left", padx=5)

        # ===== [T1.1] RC 设置（自动算百分比，不再让用户自己折算） =====
        rc_group = ttk.LabelFrame(
            meta_frame,
            text="RC（防抖 / 增抖）设置 — 程序自动算百分比", padding=8)
        rc_group.pack(fill="x", pady=(0, 6))

        ttk.Label(
            rc_group, foreground="#666", font=("", 8), justify="left",
            text=("不同手柄 RC 范围差异大（±10、±100、±500 都有）。\n"
                  "下面填【范围】+【当前数值】+【方向】，程序自动算百分比并选等级。\n"
                  "手柄没有 RC 功能 → 把'最小'和'最大'都填 0，方向选'中性'。\n"
                  "防抖 = 抑制摇杆抖动；增抖 = 增强摇杆响应（让小幅推杆放大）。")
        ).pack(fill="x", pady=(0, 6), anchor="w")

        # 单/双 RC 模式切换勾选框
        v_dual_rc = tk.BooleanVar(value=False)
        self.meta_vars["rc_dual"] = v_dual_rc
        ttk.Checkbutton(
            rc_group,
            text="腰射和开镜的 RC 是分开设置的（不勾 = 用一组统一的 RC）",
            variable=v_dual_rc,
            command=self._on_rc_dual_toggle
        ).pack(anchor="w", pady=(0, 4))

        # 存每个 RC 行的"自动算结果"标签，供 _recompute_rc_intensity 更新
        self._rc_auto_labels = {}

        def _build_rc_row(parent, label_text, prefix):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=2)

            ttk.Label(row, text=label_text, width=10).pack(side="left", padx=2)

            ttk.Label(row, text="范围:").pack(side="left", padx=(6, 2))
            v_min = tk.StringVar(value="-10")
            v_max = tk.StringVar(value="10")
            self.meta_vars[f"{prefix}_range_min"] = v_min
            self.meta_vars[f"{prefix}_range_max"] = v_max
            ttk.Entry(row, textvariable=v_min, width=5).pack(side="left", padx=1)
            ttk.Label(row, text="到").pack(side="left", padx=1)
            ttk.Entry(row, textvariable=v_max, width=5).pack(side="left", padx=1)

            ttk.Label(row, text="当前值:").pack(side="left", padx=(8, 2))
            v_value = tk.StringVar(value="0")
            self.meta_vars[prefix] = v_value
            ttk.Entry(row, textvariable=v_value, width=6).pack(side="left", padx=1)

            ttk.Label(row, text="方向:").pack(side="left", padx=(8, 2))
            v_dir = tk.StringVar(value="neutral")
            self.meta_vars[f"{prefix}_direction"] = v_dir
            for code, txt in [("antishake", "防抖"),
                              ("neutral", "中性"),
                              ("motion", "增抖")]:
                ttk.Radiobutton(
                    row, text=txt, variable=v_dir, value=code,
                    command=self._recompute_rc_intensity
                ).pack(side="left", padx=1)

            auto_lbl = ttk.Label(
                row, text="→ 0%", foreground="#3498DB",
                font=("", 9, "italic"), width=22)
            auto_lbl.pack(side="left", padx=(6, 2))
            self._rc_auto_labels[prefix] = auto_lbl

            # intensity code 隐式存到 meta_vars，由重算逻辑更新
            self.meta_vars[f"{prefix}_intensity"] = tk.StringVar(value="none")

            # 监听三个数值变化
            for v in (v_min, v_max, v_value):
                v.trace_add("write",
                            lambda *a: self._recompute_rc_intensity())

        # 单 RC 模式（默认显示）
        self._rc_single_frame = ttk.Frame(rc_group)
        _build_rc_row(self._rc_single_frame, "RC:", "rc_combined")
        self._rc_single_frame.pack(fill="x")

        # 双 RC 模式（默认隐藏，勾选后显示）
        self._rc_dual_frame = ttk.Frame(rc_group)
        _build_rc_row(self._rc_dual_frame, "腰射 RC:", "rc_hipfire")
        _build_rc_row(self._rc_dual_frame, "开镜 RC:", "rc_ads")
        # 不 pack，等用户勾选才显示

        # 启动后立即算一次
        self.after(50, self._recompute_rc_intensity)

        # ===== 其他元数据字段（保持原样） =====
        others_frame = ttk.Frame(meta_frame)
        others_frame.pack(fill="x", pady=(4, 0))
        other_rows = [
            ("curve", "曲线版本/名称:", "",
             "便于后续区分多次记录，如 v1, v2, 试用版 等"),
            ("weapons", "主要使用武器:", "",
             "如 R99、R301（冲锋枪、步枪等）"),
            ("scene", "测试场景:", "训练场",
             "训练场 / 比赛 / 休闲对战 等"),
        ]
        for i, (key, label, default, hint) in enumerate(other_rows):
            ttk.Label(others_frame, text=label, width=14).grid(
                row=i, column=0, sticky="e", padx=5, pady=2)
            var = tk.StringVar(value=default)
            self.meta_vars[key] = var
            ttk.Entry(others_frame, textvariable=var, width=22).grid(
                row=i, column=1, sticky="w", padx=5, pady=2)
            ttk.Label(others_frame, text=hint, foreground="gray",
                      font=("", 8)).grid(
                row=i, column=2, sticky="w", padx=5, pady=2)

        # 输出位置
        out_frame = ttk.Frame(parent)
        out_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(out_frame, text="输出目录:").pack(side="left")
        output_dir = resolve_output_dir(self.config)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[警告] 创建默认输出目录失败: {e}")
        self.out_dir_var = tk.StringVar(value=str(output_dir))
        ttk.Entry(out_frame, textvariable=self.out_dir_var, width=50).pack(
            side="left", padx=5)
        ttk.Button(out_frame, text="选择...",
                   command=self._choose_out_dir).pack(side="left")

        # 按钮区
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)
        self.start_btn = ttk.Button(btn_frame, text="● 开始录制",
                                    command=self._start_record)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="■ 停止录制",
                                   command=self._stop_record, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # 状态显示区
        status_frame = ttk.LabelFrame(parent, text="实时状态", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_text = scrolledtext.ScrolledText(
            status_frame, height=8, font=("Consolas", 9))
        self.status_text.pack(fill="both", expand=True)
        self._log("等待开始录制...\n\n"
                  "操作步骤：\n"
                  "1. 上方选择你的开火键和开镜键（必须选对！）\n"
                  "2. 填写元数据（RC 值不知道就填 0）\n"
                  "3. 点击 ● 开始录制\n"
                  "4. 正常打游戏，观察实时状态确认 FIRE/ADS 标记会亮\n"
                  "5. 打完后点 ■ 停止录制")

    def _on_perf_change(self, combo):
        """性能模式切换"""
        idx = combo.current()
        if 0 <= idx < len(self._perf_options):
            label, code = self._perf_options[idx]
            self.perf_profile_var.set(code)
            self._persist_user_config()

    # ========== 通用辅助 ==========
    def _log(self, msg):
        self.status_text.insert("end", msg + "\n")
        self.status_text.see("end")

    def _choose_out_dir(self):
        d = filedialog.askdirectory(initialdir=self.out_dir_var.get())
        if d:
            self.out_dir_var.set(d)
            self._persist_user_config()

    # ========== 录制控制 ==========
    def _start_record(self):
        out_dir = Path(self.out_dir_var.get())
        if not out_dir.exists():
            messagebox.showerror("错误", f"输出目录不存在: {out_dir}")
            return

        # 检查是否选择了控制器
        if self.controller_mgr is None:
            if self._init_pending:
                messagebox.showinfo(
                    "请稍候",
                    "正在初始化手柄驱动，请等待几秒钟后再点击开始录制。")
            else:
                messagebox.showerror("错误", "控制器管理器未初始化")
            return

        ctrl = self.controller_mgr.get_current_controller()
        if ctrl is None:
            messagebox.showerror(
                "错误",
                "未选择控制器！请先在「① 选择控制器」中选定一个手柄。\n"
                "如果列表显示全部为「空」，请先点「🔄 刷新设备列表」。")
            return

        fire_btn = self.fire_button_var.get()
        ads_btn = self.ads_button_var.get()
        mark_btn = self.mark_button_var.get() if hasattr(self, "mark_button_var") else ""
        if fire_btn == ads_btn:
            messagebox.showerror("错误", "开火键和开镜键不能相同！")
            return
        # [T2.1] 标记键不能和开火/开镜冲突
        if mark_btn and mark_btn in (fire_btn, ads_btn):
            messagebox.showerror(
                "错误",
                f"标记键不能和开火键/开镜键相同！\n"
                f"当前：开火={fire_btn} 开镜={ads_btn} 标记={mark_btn}\n"
                f"请重新选一个不冲突的键作为标记键。")
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"stick_log_{timestamp_str}.csv"

        # [T1.1] 现在 meta_vars 里 sensor_type、rc_*_intensity、rc_*_direction
        # 已经是 code（"alps"/"hall"/"light"/"motion" 等），不再需要中文→code 映射。
        # 直接收集即可，但要正确处理 BooleanVar 等非字符串类型。
        metadata = {}
        for k, v in self.meta_vars.items():
            try:
                raw = v.get() if hasattr(v, "get") else v
            except Exception:
                raw = ""
            if isinstance(raw, bool):
                val = "true" if raw else "false"
            elif isinstance(raw, str):
                val = raw.strip()
            else:
                val = str(raw)
            metadata[k] = val if val else "unknown"

        # [T1.1] 单 RC 模式：把 rc_combined 的所有子字段同步到 rc_hipfire 和 rc_ads
        # 这样 analyzer.py 不用区分单/双 RC，老 CSV 兼容
        if metadata.get("rc_dual", "false") == "false":
            for sub in ("", "_range_min", "_range_max",
                        "_direction", "_intensity"):
                src_key = f"rc_combined{sub}"
                if src_key in metadata and metadata[src_key] not in ("unknown", ""):
                    metadata[f"rc_hipfire{sub}"] = metadata[src_key]
                    metadata[f"rc_ads{sub}"] = metadata[src_key]

        # [T0.3] 先做 3 秒静止校准，校准完成后才真正开始录制
        self._calibrate_then_record(
            output_path, metadata, fire_btn, ads_btn, mark_btn, ctrl)

    def _calibrate_then_record(self, output_path, metadata,
                                fire_btn, ads_btn, mark_btn, ctrl):
        """[T0.3] 录制前 3 秒静止校准，UI 只负责弹窗和线程。"""
        # 录制按钮立刻禁用，防止用户重复点击
        self.start_btn["state"] = "disabled"

        dlg = tk.Toplevel(self)
        dlg.title("校准传感器本底")
        dlg.geometry("440x260")
        dlg.transient(self)
        dlg.resizable(False, False)
        # 禁止关闭（必须等校准结束）
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)
        # 居中显示
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 440) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 260) // 2
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        ttk.Label(
            dlg,
            text="校准传感器本底",
            font=("", 14, "bold")).pack(pady=(20, 5))
        ttk.Label(
            dlg,
            text="请把双摇杆完全松手放好，保持 3 秒不动\n"
                 "（用于记录摇杆静止时的微小波动）",
            justify="center",
            foreground="#555").pack(pady=(0, 12))

        countdown_lbl = tk.Label(
            dlg, text="3", font=("", 48, "bold"), fg="#3498DB")
        countdown_lbl.pack(pady=4)

        live_lbl = ttk.Label(
            dlg, text="正在采集…", foreground="#888", font=("", 9))
        live_lbl.pack()

        # 后台线程只调用应用用例；采样节奏和本底计算由 CalibrateController 负责。
        counting_reader_cls = _get_runtime_attr("_CountingControllerReader", None)
        clock_cls = _get_runtime_attr("_SystemClock", None)
        counting_reader = counting_reader_cls(self.controller_mgr)
        result_holder = []
        err_holder = []
        threading_mod = _get_runtime_attr("threading", threading)
        worker_done = threading_mod.Event()

        def collect_worker():
            try:
                result = _get_runtime_attr("CalibrateController", CalibrateController)(
                    counting_reader, clock_cls()).execute(
                        _get_runtime_attr("CalibrationRequest", CalibrationRequest)(
                            controller_info=ctrl,
                            duration_s=3.0,
                            sample_interval_s=0.004))
                result_holder.append(result)
            except Exception as e:
                err_holder.append(str(e))
            finally:
                worker_done.set()

        threading_mod.Thread(
            target=collect_worker, daemon=True,
            name="calibration-collect").start()

        # 倒计时 3 → 2 → 1 → "完成"
        def tick(remaining):
            if remaining > 0:
                countdown_lbl.configure(text=str(remaining), fg="#3498DB")
                # 实时显示当前采集到的样本数让用户安心
                live_lbl.configure(
                    text=f"已采集 {counting_reader.sample_count} 个样本…")
                self.after(1000, tick, remaining - 1)
            else:
                countdown_lbl.configure(text="完成", fg="#27AE60")
                live_lbl.configure(text="正在完成校准…")
                # 留 200ms 让收集线程退出，再做 finalize
                self.after(250, finalize)

        def finalize():
            if not worker_done.is_set():
                live_lbl.configure(
                    text=f"正在完成校准… 已采集 {counting_reader.sample_count} 个样本")
                self.after(50, finalize)
                return

            if err_holder:
                # 校准期间读手柄出错
                dlg.destroy()
                self.start_btn["state"] = "normal"
                messagebox.showerror(
                    "校准失败",
                    f"校准期间无法读取手柄状态：\n{err_holder[0]}\n\n"
                    "请重新点'开始录制'再试。")
                return
            if not result_holder:
                dlg.destroy()
                self.start_btn["state"] = "normal"
                messagebox.showerror(
                    "校准失败",
                    "校准没有返回结果，请重新点'开始录制'再试。")
                return

            result = result_holder[0]
            nfx = result.noise_floor_x
            nfy = result.noise_floor_y
            sample_count = result.sample_count

            metadata["noise_floor_x"] = f"{nfx:.6f}"
            metadata["noise_floor_y"] = f"{nfy:.6f}"

            dlg.destroy()
            # 把校准结果记到 status_text，让用户看到
            self.status_text.delete(1.0, "end")
            self._log(f"✓ 校准完成：本底 X={nfx:.5f}  Y={nfy:.5f}  "
                      f"（采样 {sample_count} 帧）")
            if max(nfx, nfy) > 0.01:
                self._log(
                    f"  [提示] 本底偏高，可能是回中虚位较大或摇杆有漂移迹象，"
                    f"分析报告会自动减去这部分。")
            self._actually_start_recording(
                output_path, metadata, fire_btn, ads_btn, mark_btn,
                ctrl, nfx, nfy)

        # 立即显示 3，开始倒计时
        tick(3)

    def _actually_start_recording(self, output_path, metadata,
                                   fire_btn, ads_btn, mark_btn,
                                   ctrl, nfx, nfy):
        """[T0.3] 校准完成后真正启动 Recorder。"""
        recorder_cls = _get_runtime_attr("StickRecorder", None)
        self.recorder = recorder_cls(
            output_path, metadata, fire_btn, ads_btn,
            controller_info=ctrl,
            controller_manager=self.controller_mgr,
            on_update=lambda s: self.after(0, self._on_recorder_update, s),
            on_done=lambda ok, info: self.after(0, self._on_recorder_done, ok, info),
            perf_profile=self.perf_profile_var.get(),
            noise_floor_x=nfx,
            noise_floor_y=nfy,
            mark_button=mark_btn or None)
        self.recorder.start()

        self.start_btn["state"] = "disabled"
        self.stop_btn["state"] = "normal"
        self.fire_combo["state"] = "disabled"
        self.ads_combo["state"] = "disabled"
        if hasattr(self, "mark_combo"):
            self.mark_combo["state"] = "disabled"
        self.perf_combo["state"] = "disabled"
        # 录制时禁用槽位切换
        for w in self.slot_widgets:
            w["radio"].configure(state="disabled")

        self._log(f"开始录制 → {output_path.name}")
        self._log(f"控制器: {ctrl.display_string()}")
        # 显示用户友好的按键标签
        cb_mod = _runtime_cb()
        if cb_mod is not None:
            fire_label = cb_mod.get_button_display_name(ctrl.layout, fire_btn)
            ads_label = cb_mod.get_button_display_name(ctrl.layout, ads_btn)
            line = f"键位: 开火={fire_label}, 开镜={ads_label}"
            if mark_btn:
                mark_label = cb_mod.get_button_display_name(ctrl.layout, mark_btn)
                line += f", 标记={mark_label}"
            self._log(line)
        else:
            line = f"键位: 开火={fire_btn}, 开镜={ads_btn}"
            if mark_btn:
                line += f", 标记={mark_btn}"
            self._log(line)
        if mark_btn:
            self._log(f"💡 录制时按一下'标记键'就标记当前为'压得好' —— "
                      f"事后报告会和算法评分对照")
        self._log("-" * 60)


    def _stop_record(self):
        if self.recorder:
            self.recorder.stop()
            self._log("正在停止...")

    def _on_recorder_update(self, s):
        bar_fire = "🔴 FIRE" if s["fire"] else "      "
        bar_ads = "🟢 ADS " if s["ads"] else "      "
        prefix = "状态 ▶"
        # [T0.2] 显示有效采样率（标称 + 有效）
        eff = s.get("effective_rate", s["rate"])
        if eff < 250:
            rate_str = f"采样率={s['rate']:.0f}Hz(有效{eff:.0f}⚠)"
        else:
            rate_str = f"采样率={s['rate']:.0f}Hz(有效{eff:.0f})"
        # [T2.1] 标记反馈：刚刚按下标记键时给一行提示，并维持总数
        mark_count = s.get("mark_count", 0)
        mark_str = f"⭐{mark_count}" if mark_count > 0 else ""
        if s.get("just_marked"):
            self._log(f"⭐ 已标记 第 {mark_count} 次（'压得好'）")
        cur = (f"{prefix} T={s['elapsed']:6.1f}s  {rate_str}  "
               f"L=({s['lx']:+.2f},{s['ly']:+.2f}) "
               f"R=({s['rx']:+.2f},{s['ry']:+.2f}) "
               f"FIRE={s['fire_pct']:.1f}% ADS={s['ads_pct']:.1f}% "
               f"{bar_fire} {bar_ads}")

        content = self.status_text.get("1.0", "end-1c")
        rows = content.split("\n")
        replaced = False
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].startswith(prefix):
                rows[i] = cur
                replaced = True
                break
        if not replaced:
            rows.append(cur)

        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", "\n".join(rows))
        self.status_text.see("end")

    def _on_recorder_done(self, ok, info):
        self.start_btn["state"] = "normal"
        self.stop_btn["state"] = "disabled"
        self.fire_combo["state"] = "readonly"
        self.ads_combo["state"] = "readonly"
        if hasattr(self, "mark_combo"):
            self.mark_combo["state"] = "readonly"
        self.perf_combo["state"] = "readonly"
        # 恢复槽位选择
        self._refresh_slot_display()

        if not ok:
            self._log(f"\n[错误] {info}")
            # 录制失败弹错误反馈窗（区分常见可恢复错误和严重错误）
            recoverable_keywords = ["未检测到", "未选择", "无法创建", "目录"]
            if any(kw in str(info) for kw in recoverable_keywords):
                # 常见用户错误，普通提示即可
                messagebox.showerror("录制失败", str(info))
            elif _runtime_error_reporter() is not None:
                # 程序异常，弹反馈窗
                _runtime_error_reporter().show_error_dialog(
                    self, "录制失败", str(info), None,
                    "录制过程中发生异常")
            else:
                messagebox.showerror("录制失败", str(info))
            return

        self._log("")
        self._log("-" * 60)
        self._log("✓ 录制完成")
        self._log(f"  时长: {info['duration']:.1f} 秒")
        self._log(f"  样本: {info['samples']} 帧")
        self._log(f"  采样率: {info['rate']:.0f} Hz")
        # [T0.2] 有效采样率提示
        eff = info.get('effective_rate', info['rate'])
        dup = info.get('dup_ratio', 0.0)
        self._log(f"  有效采样率: {eff:.0f} Hz "
                  f"（重复帧 {dup*100:.1f}%）")
        if eff < 250:
            self._log(
                f"  [警告] 有效采样率较低，分析结果可能偏乐观。")
            self._log(
                f"         可能原因：手柄走蓝牙连接、底层 HID 报告率低、"
                f"USB 端口性能差。")
            self._log(f"         建议改用有线 USB 连接重测。")
        # [T0.3] 本底信息
        nfx = info.get('noise_floor_x', 0.0)
        nfy = info.get('noise_floor_y', 0.0)
        if nfx > 0 or nfy > 0:
            self._log(f"  传感器本底: X={nfx:.5f}  Y={nfy:.5f}（已记录到 CSV）")
        self._log(f"  开火帧: {info['fire_count']} "
                  f"({100*info['fire_count']/max(info['samples'],1):.1f}%)")
        self._log(f"  开镜帧: {info['ads_count']} "
                  f"({100*info['ads_count']/max(info['samples'],1):.1f}%)")
        # [T2.1] 标记总数
        marks = info.get('mark_count', 0)
        if marks > 0:
            self._log(f"  ⭐ 玩家标记: {marks} 次（'压得好'，分析时会和算法评分对照）")
        self._log(f"  文件: {info['output']}")

        if info['fire_count'] == 0:
            messagebox.showwarning(
                "提示",
                f"没有检测到开火事件！\n"
                f"可能是开火键选错了（当前选: {self.fire_button_var.get()}）\n"
                f"请重新检查键位设置后再试。")
        else:
            self.csv_path_var.set(info['output'])
            if messagebox.askyesno("录制完成", "录制成功！\n是否切换到分析页面？"):
                self.notebook.select(1)
