"""录制标签页 mixin。"""
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import customtkinter as ctk

try:
    from app.app_paths import resolve_output_dir
    from app.application import CalibrationRequest, CalibrateController
    from app.adapters import controller as cb
    from app.adapters.ui import error_reporter
    from app.adapters.ui.controller_panel import ControllerPanelMixin, _runtime_cb
    from app.adapters.ui.theme import (
        COLOR_ACCENT_MAGENTA,
        COLOR_ACCENT_MAGENTA_HOVER,
        COLOR_ACCENT_ORANGE,
        COLOR_BG,
        COLOR_DANGER,
        COLOR_HOVER_BG,
        COLOR_LINE,
        COLOR_LINE_DARK,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_SUCCESS,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_MONO,
        FONT_SECTION,
        FONT_SMALL,
        entry,
        line_button,
        outline_option_menu,
        section,
        set_state,
        show_message,
        solid_button,
        textbox,
    )
except ModuleNotFoundError:
    from src.app.app_paths import resolve_output_dir
    from src.app.application import CalibrationRequest, CalibrateController
    from src.app.adapters import controller as cb
    from src.app.adapters.ui import error_reporter
    from src.app.adapters.ui.controller_panel import ControllerPanelMixin, _runtime_cb
    from src.app.adapters.ui.theme import (
        COLOR_ACCENT_MAGENTA,
        COLOR_ACCENT_MAGENTA_HOVER,
        COLOR_ACCENT_ORANGE,
        COLOR_BG,
        COLOR_DANGER,
        COLOR_HOVER_BG,
        COLOR_LINE,
        COLOR_LINE_DARK,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_SUCCESS,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_MONO,
        FONT_SECTION,
        FONT_SMALL,
        entry,
        line_button,
        outline_option_menu,
        section,
        set_state,
        show_message,
        solid_button,
        textbox,
    )

def _get_runtime_attr(name, default):
    for module_name in (
        "app.adapters.ui.tkinter_app",
        "src.app.adapters.ui.tkinter_app",
    ):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return default

class RecordTabMixin(ControllerPanelMixin):
    """封装录制页相关 UI 和逻辑。依赖宿主提供控制器和后台录制功能。"""

    def _build_record_tab(self, parent):
        self._record_step_index = 0
        self._record_step_titles = [
            "选择控制器",
            "键位映射",
            "性能模式",
            "记录元数据",
            "输出与录制",
        ]

        step_host = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        step_host.pack(fill="both", expand=True)
        step_host.grid_rowconfigure(0, weight=1)
        step_host.grid_columnconfigure(0, weight=1)

        self._record_steps = []
        for _title in self._record_step_titles:
            step_frame = ctk.CTkFrame(step_host, fg_color="transparent", corner_radius=0)
            step_frame.grid(row=0, column=0, sticky="nsew")
            self._record_steps.append(step_frame)

        controller_step = self._record_steps[0]
        key_step = self._record_steps[1]
        perf_step = self._record_steps[2]
        meta_step = self._record_steps[3]
        action_step = self._record_steps[4]

        self._build_controller_panel(controller_step)
        self._build_key_mapping_panel(key_step)
        self._build_performance_panel(perf_step)
        self._build_metadata_panel(meta_step)
        self._build_action_panel(action_step)

        self._build_record_step_nav(parent)
        self._show_record_step(0)

    def _build_performance_panel(self, parent):
        perf_frame = section(parent, "3. 性能模式")
        ctk.CTkLabel(perf_frame, text="采样精度:", width=120, anchor="e", text_color=COLOR_TEXT, font=FONT_BODY).grid(
            row=0, column=0, sticky="e", padx=(0, 10), pady=2)
        self.perf_profile_var = tk.StringVar(
            value=self.config.get("perf_profile", "high"))
        perf_options = [
            ("高精度（默认，500Hz）- 推荐配置较好的电脑", "high"),
            ("平衡（250Hz）- 大多数电脑", "normal"),
            ("低性能（125Hz）- 老电脑或同时运行 Apex 卡顿时", "low"),
        ]
        self._perf_options = perf_options

        perf_label_var = tk.StringVar(value=perf_options[0][0])
        perf_wrapper, perf_combo = outline_option_menu(
            perf_frame,
            variable=perf_label_var,
            values=[o[0] for o in perf_options],
            command=self._on_perf_change_ctk,
            width=350,
        )

        perf_codes = [o[1] for o in perf_options]
        current_perf = self.perf_profile_var.get()
        if current_perf not in perf_codes:
            current_perf = "high"
            self.perf_profile_var.set(current_perf)

        current_idx = perf_codes.index(current_perf)
        perf_combo.set(perf_options[current_idx][0])
        perf_wrapper.grid(row=0, column=1, sticky="w", pady=2)

        self.perf_combo = perf_combo

        ctk.CTkLabel(perf_frame,
                  text="游戏掉帧时切换到低性能；200Hz 以上仍足够做压枪分析。",
                  text_color=COLOR_MUTED, font=FONT_BODY, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=2)

    def _build_metadata_panel(self, parent):
        meta_frame = section(parent, "4. 本次记录元数据")
        self.meta_vars = {}
        self._build_sensor_row(meta_frame)
        self._build_rc_settings(meta_frame)
        self._build_other_metadata_rows(meta_frame)

    def _build_sensor_row(self, meta_frame):
        sensor_row = ctk.CTkFrame(meta_frame, fg_color="transparent")
        sensor_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(sensor_row, text="摇杆传感器类型:",
                  width=120, anchor="e", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(0, 10))

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
        v_sensor_label.trace_add(
            "write",
            lambda *_: self._on_sensor_label_changed(
                v_sensor_label, v_sensor_code, sensor_options),
        )

        sensor_wrapper, _sensor_combo = outline_option_menu(
            sensor_row,
            variable=v_sensor_label,
            values=[o[0] for o in sensor_options],
            width=200,
        )
        sensor_wrapper.pack(side="left")

        # 回报率输入
        ctk.CTkLabel(sensor_row, text="回报率:", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(15, 2))
        v_polling = tk.StringVar(value="1000")
        self.meta_vars["polling_rate"] = v_polling

        polling_entry = entry(sensor_row, textvariable=v_polling, width=60)
        polling_entry.pack(side="left", padx=2)

        ctk.CTkLabel(sensor_row, text="Hz", text_color=COLOR_MUTED, font=FONT_BODY).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(sensor_row,
                  text="常见 125/250/500/1000",
                  text_color=COLOR_MUTED, font=FONT_BODY).pack(side="left", padx=5)

    def _on_sensor_label_changed(self, label_var, code_var, sensor_options):
        label = label_var.get()
        for option_label, code in sensor_options:
            if option_label == label:
                code_var.set(code)
                return

    def _build_rc_settings(self, meta_frame):
        ctk.CTkLabel(meta_frame, text="RC 设置", text_color=COLOR_TEXT, font=FONT_BODY_BOLD).pack(anchor="w", pady=(15, 0))
        rc_group = ctk.CTkFrame(meta_frame, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_LINE, corner_radius=0)
        rc_group.pack(fill="x", pady=(5, 6), ipadx=10, ipady=10)

        ctk.CTkLabel(
            rc_group, text_color=COLOR_MUTED, font=FONT_BODY, justify="left",
            text="填写范围、当前值和方向；没有 RC 功能时范围填 0，方向选中性。"
        ).pack(fill="x", pady=(5, 10), padx=5, anchor="w")

        # 单/双 RC 模式切换勾选框
        v_dual_rc = tk.BooleanVar(value=False)
        self.meta_vars["rc_dual"] = v_dual_rc
        ctk.CTkCheckBox(
            rc_group,
            text="腰射和开镜的 RC 是分开设置的（不勾 = 用一组统一的 RC）",
            variable=v_dual_rc,
            command=self._on_rc_dual_toggle,
            fg_color=COLOR_ACCENT_MAGENTA, hover_color=COLOR_ACCENT_MAGENTA_HOVER, border_color=COLOR_LINE_DARK, text_color=COLOR_TEXT, font=FONT_BODY
        ).pack(anchor="w", pady=(0, 10), padx=5)

        # 存每个 RC 行的"自动算结果"标签，供 _recompute_rc_intensity 更新
        self._rc_auto_labels = {}

        # 单 RC 模式（默认显示）
        self._rc_single_frame = ctk.CTkFrame(rc_group, fg_color="transparent")
        self._build_rc_row_ui(self._rc_single_frame, "RC:", "rc_combined")
        self._rc_single_frame.pack(fill="x")

        # 双 RC 模式（默认隐藏，勾选后显示）
        self._rc_dual_frame = ctk.CTkFrame(rc_group, fg_color="transparent")
        self._build_rc_row_ui(self._rc_dual_frame, "腰射 RC:", "rc_hipfire")
        self._build_rc_row_ui(self._rc_dual_frame, "开镜 RC:", "rc_ads")
        # 不 pack，等用户勾选才显示

        # 启动后立即算一次
        self.after(50, self._recompute_rc_intensity)

    def _build_rc_row_ui(self, parent, label_text, prefix):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4, padx=5)

        ctk.CTkLabel(row, text=label_text, width=70, anchor="w", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=2)
        ctk.CTkLabel(row, text="范围:", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(6, 2))

        v_min = tk.StringVar(value="-10")
        v_max = tk.StringVar(value="10")
        v_value = tk.StringVar(value="0")
        v_dir = tk.StringVar(value="neutral")
        self.meta_vars[f"{prefix}_range_min"] = v_min
        self.meta_vars[f"{prefix}_range_max"] = v_max
        self.meta_vars[prefix] = v_value
        self.meta_vars[f"{prefix}_direction"] = v_dir

        entry(row, textvariable=v_min, width=56).pack(side="left", padx=1)
        ctk.CTkLabel(row, text="到", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=1)
        entry(row, textvariable=v_max, width=56).pack(side="left", padx=1)
        ctk.CTkLabel(row, text="当前值:", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(12, 2))
        entry(row, textvariable=v_value, width=66).pack(side="left", padx=1)
        ctk.CTkLabel(row, text="方向:", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(12, 2))

        for code, text in [("antishake", "防抖"), ("neutral", "中性"), ("motion", "增抖")]:
            ctk.CTkRadioButton(
                row, text=text, variable=v_dir, value=code,
                command=self._recompute_rc_intensity,
                fg_color=COLOR_ACCENT_MAGENTA,
                hover_color=COLOR_ACCENT_MAGENTA_HOVER,
                border_color=COLOR_LINE_DARK,
                text_color=COLOR_TEXT,
                font=FONT_BODY,
            ).pack(side="left", padx=4)

        auto_lbl = ctk.CTkLabel(
            row, text="→ 0%", text_color=COLOR_ACCENT_MAGENTA,
            font=FONT_BODY_BOLD, width=150, anchor="w")
        auto_lbl.pack(side="left", padx=(12, 2))
        self._rc_auto_labels[prefix] = auto_lbl

        # intensity code 隐式存到 meta_vars，由重算逻辑更新。
        self.meta_vars[f"{prefix}_intensity"] = tk.StringVar(value="none")
        for value_var in (v_min, v_max, v_value):
            value_var.trace_add(
                "write", lambda *_: self._recompute_rc_intensity())

    def _build_other_metadata_rows(self, meta_frame):
        others_frame = ctk.CTkFrame(meta_frame, fg_color="transparent")
        others_frame.pack(fill="x", pady=(8, 0))
        other_rows = [
            ("curve", "曲线版本/名称:", "", "便于后续区分多次记录，如 v1, v2, 试用版 等"),
            ("weapons", "主要使用武器:", "", "如 R99、R301（冲锋枪、步枪等）"),
            ("scene", "测试场景:", "训练场", "训练场 / 比赛 / 休闲对战 等"),
        ]
        
        for i, (key, label, default, hint) in enumerate(other_rows):
            row_frame = ctk.CTkFrame(others_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)
            
            ctk.CTkLabel(row_frame, text=label, width=120, anchor="e", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(0, 10))
            
            var = tk.StringVar(value=default)
            self.meta_vars[key] = var

            entry(row_frame, textvariable=var, width=220).pack(side="left", padx=2)
            
            ctk.CTkLabel(row_frame, text=hint, text_color=COLOR_MUTED, font=FONT_BODY).pack(side="left", padx=10)

    def _build_action_panel(self, parent):
        action_frame = section(parent, "5. 输出与录制")

        out_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        out_frame.pack(fill="x", pady=15)

        ctk.CTkLabel(out_frame, text="输出目录:", width=120, anchor="e", text_color=COLOR_TEXT, font=FONT_BODY).pack(side="left", padx=(0, 10))
        output_dir = resolve_output_dir(self.config)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[警告] 无法创建默认目录 {output_dir}: {e}")
        
        self.out_dir_var = tk.StringVar(value=str(output_dir))
        out_entry = entry(
            out_frame,
            textvariable=self.out_dir_var,
            fg_color=COLOR_PANEL,
        )
        out_entry.pack(side="left", fill="x", expand=True, padx=2)
        
        line_button(out_frame, "浏览", command=self._choose_out_dir, width=86).pack(
            side="left", padx=5)

        # 操作按钮区 (巨型录制按钮)
        act_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        act_frame.pack(fill="x", pady=20)
        
        # Add subtle divider above button
        ctk.CTkFrame(act_frame, height=1, fg_color=COLOR_LINE).pack(fill="x", pady=(0, 20))

        button_row = ctk.CTkFrame(act_frame, fg_color="transparent")
        button_row.pack(fill="x", padx=10)

        self.btn_record = ctk.CTkButton(
            button_row,
            text="开始录制",
            command=self._start_record,
            font=(FONT_BODY[0], 22, "bold"),
            height=62,
            fg_color=COLOR_BG,
            border_color=COLOR_TEXT,
            border_width=1,
            text_color=COLOR_TEXT,
            hover_color=COLOR_BG,
            corner_radius=0
        )
        # Bind hover effects
        self.btn_record.bind("<Enter>", lambda e: self.btn_record.configure(text_color=COLOR_ACCENT_MAGENTA, border_color=COLOR_ACCENT_MAGENTA) if self.btn_record.cget("state") != "disabled" else None)
        self.btn_record.bind("<Leave>", lambda e: self.btn_record.configure(text_color=COLOR_TEXT, border_color=COLOR_TEXT) if self.btn_record.cget("state") != "disabled" else None)
        self.btn_record.pack(side="left", fill="x", expand=True)
        self.start_btn = self.btn_record

        self.stop_btn = line_button(
            button_row,
            "停止",
            command=self._stop_record,
            width=120,
        )
        self.stop_btn.pack(side="left", padx=(10, 0), fill="y")
        set_state(self.stop_btn, "disabled")

        # 进度与状态显示
        self.status_label = ctk.CTkLabel(act_frame, text="准备就绪", text_color=COLOR_TEXT, font=FONT_BODY_BOLD)
        self.status_label.pack(pady=(15, 5))
        
        self.progress_label = ctk.CTkLabel(act_frame, text="", text_color=COLOR_MUTED, font=FONT_BODY)
        self.progress_label.pack()

        self.status_text = textbox(act_frame, height=190, font=FONT_MONO)
        self.status_text.pack(fill="x", padx=10, pady=(12, 0))

    def _build_record_step_nav(self, parent):
        nav_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        nav_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkFrame(nav_frame, height=1, fg_color=COLOR_LINE).pack(
            fill="x", pady=(0, 10))

        controls = ctk.CTkFrame(nav_frame, fg_color="transparent", corner_radius=0)
        controls.pack(fill="x")

        self.record_prev_btn = line_button(
            controls,
            "← 上一步",
            command=lambda: self._move_record_step(-1),
            width=120,
        )
        self.record_prev_btn.pack(side="left")

        self.record_step_label = ctk.CTkLabel(
            controls,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
            anchor="center",
        )
        self.record_step_label.pack(side="left", fill="x", expand=True)

        self.record_next_btn = line_button(
            controls,
            "下一步 →",
            command=lambda: self._move_record_step(1),
            width=120,
        )
        self.record_next_btn.pack(side="right")

    def _move_record_step(self, delta):
        self._show_record_step(self._record_step_index + delta)

    def _show_record_step(self, index):
        if not hasattr(self, "_record_steps") or not self._record_steps:
            return
        bounded_index = max(0, min(index, len(self._record_steps) - 1))
        self._record_step_index = bounded_index

        for step_index, frame in enumerate(self._record_steps):
            if step_index == bounded_index:
                frame.grid()
            else:
                frame.grid_remove()

        step_count = len(self._record_steps)
        title = self._record_step_titles[bounded_index]
        try:
            self.record_step_label.configure(
                text=f"步骤 {bounded_index + 1} / {step_count} · {title}")
            set_state(self.record_prev_btn, "normal" if bounded_index > 0 else "disabled")
            set_state(
                self.record_next_btn,
                "normal" if bounded_index < step_count - 1 else "disabled",
            )
        except Exception:
            pass

    def _on_perf_change_ctk(self, val, _unused=None):
        """性能模式切换"""
        label_to_code = {label: code for label, code in self._perf_options}
        code = label_to_code.get(val)
        if code is not None:
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
        # 这样分析模块不用区分单/双 RC，老 CSV 兼容
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
        set_state(self.start_btn, "disabled")

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
            font=FONT_BODY_BOLD).pack(pady=(20, 5))
        ttk.Label(
            dlg,
            text="请把双摇杆完全松手放好，保持 3 秒不动\n"
                 "（用于记录摇杆静止时的微小波动）",
            justify="center",
            foreground=COLOR_MUTED).pack(pady=(0, 12))

        countdown_lbl = tk.Label(
            dlg, text="3", font=(FONT_BODY[0], 48, "bold"),
            fg=COLOR_ACCENT_MAGENTA)
        countdown_lbl.pack(pady=4)

        live_lbl = ttk.Label(
            dlg, text="正在采集…", foreground=COLOR_MUTED, font=FONT_SMALL)
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
                countdown_lbl.configure(
                    text=str(remaining), fg=COLOR_ACCENT_MAGENTA)
                # 实时显示当前采集到的样本数让用户安心
                live_lbl.configure(
                    text=f"已采集 {counting_reader.sample_count} 个样本…")
                self.after(1000, tick, remaining - 1)
            else:
                countdown_lbl.configure(text="完成", fg=COLOR_SUCCESS)
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
                set_state(self.start_btn, "normal")
                messagebox.showerror(
                    "校准失败",
                    f"校准期间无法读取手柄状态：\n{err_holder[0]}\n\n"
                    "请重新点'开始录制'再试。")
                return
            if not result_holder:
                dlg.destroy()
                set_state(self.start_btn, "normal")
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

        set_state(self.start_btn, "disabled")
        set_state(self.stop_btn, "normal")
        set_state(self.fire_combo, "disabled")
        set_state(self.ads_combo, "disabled")
        if hasattr(self, "mark_combo"):
            set_state(self.mark_combo, "disabled")
        set_state(self.perf_combo, "disabled")
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
        bar_fire = "FIRE" if s["fire"] else "----"
        bar_ads = "ADS" if s["ads"] else "---"
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
        cur = (f"状态 T={s['elapsed']:6.1f}s  {rate_str}  "
               f"L=({s['lx']:+.2f},{s['ly']:+.2f}) "
               f"R=({s['rx']:+.2f},{s['ry']:+.2f}) "
               f"FIRE={s['fire_pct']:.1f}% ADS={s['ads_pct']:.1f}% "
               f"{bar_fire} {bar_ads} {mark_str}")

        # 实时状态用独立标签刷新，避免反复重绘滚动文本框导致拖影。
        if hasattr(self, "progress_label"):
            self.progress_label.configure(text=cur)

    def _on_recorder_done(self, ok, info):
        set_state(self.start_btn, "normal")
        set_state(self.stop_btn, "disabled")
        set_state(self.fire_combo, "normal")
        set_state(self.ads_combo, "normal")
        if hasattr(self, "mark_combo"):
            set_state(self.mark_combo, "normal")
        set_state(self.perf_combo, "normal")
        # 恢复槽位选择
        self._refresh_slot_display()

        if not ok:
            if hasattr(self, "progress_label"):
                self.progress_label.configure(text="")
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
        if hasattr(self, "progress_label"):
            self.progress_label.configure(text="")
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
                self._show_page("analyze")
