"""控制器选择和键位映射面板 mixin。"""
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk

try:
    from app.adapters import controller as cb
    from app.adapters.ui.theme import (
        COLOR_ACCENT_MAGENTA,
        COLOR_ACCENT_MAGENTA_HOVER,
        COLOR_DANGER,
        COLOR_HOVER_BG,
        COLOR_LINE,
        COLOR_LINE_DARK,
        COLOR_MUTED,
        COLOR_SUCCESS,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_MONO,
        FONT_SMALL,
        configure_notice,
        line_button,
        outline_option_menu,
        section,
    )
except ModuleNotFoundError:
    try:
        from src.app.adapters import controller as cb
        from src.app.adapters.ui.theme import (
            COLOR_ACCENT_MAGENTA,
            COLOR_ACCENT_MAGENTA_HOVER,
            COLOR_DANGER,
            COLOR_HOVER_BG,
            COLOR_LINE,
            COLOR_LINE_DARK,
            COLOR_MUTED,
            COLOR_SUCCESS,
            COLOR_TEXT,
            FONT_BODY,
            FONT_BODY_BOLD,
            FONT_MONO,
            FONT_SMALL,
            configure_notice,
            line_button,
            outline_option_menu,
            section,
        )
    except ModuleNotFoundError:
        cb = None

DEFAULT_FIRE_BUTTON = "RIGHT_SHOULDER"
DEFAULT_ADS_BUTTON = "TRIGGER_LEFT"
DEFAULT_MARK_BUTTON = "BACK"


def _get_runtime_attr(name, default):
    for module_name in (
        "app.adapters.ui.tkinter_app",
        "src.app.adapters.ui.tkinter_app",
    ):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return default


def _runtime_cb():
    return _get_runtime_attr("cb", cb)


class ControllerPanelMixin:
    """封装录制页的控制器选择和键位映射 UI。"""

    def _build_controller_panel(self, parent):
        """构建控制器槽位选择区。"""
        ctrl_frame = section(parent, "1. 选择控制器")

        # 4 个槽位（动态填充）
        self.slot_widgets = []
        for slot_idx in range(4):
            row_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            rb = ctk.CTkRadioButton(
                row_frame, text=f"槽位 {slot_idx + 1}:",
                variable=self.slot_var, value=slot_idx,
                command=self._on_slot_changed,
                width=10,
                text_color=COLOR_TEXT,
                border_color=COLOR_LINE_DARK,
                hover_color=COLOR_ACCENT_MAGENTA_HOVER,
                fg_color=COLOR_ACCENT_MAGENTA,
                font=FONT_BODY,
            )
            rb.pack(side="left", padx=(0, 10))

            label = ctk.CTkLabel(row_frame, text="[空]",
                                 font=FONT_BODY, text_color=COLOR_MUTED,
                                 anchor="w")
            label.pack(side="left", fill="x", expand=True, padx=5)

            self.slot_widgets.append({"radio": rb, "label": label})

        # 扫描按钮
        scan_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        scan_frame.pack(fill="x", pady=(12, 2))
        line_button(
            scan_frame,
            "刷新设备列表",
            command=self._scan_controllers,
            width=130,
        ).pack(side="left")

        self.scan_status_label = ctk.CTkLabel(
            scan_frame, text="", text_color=COLOR_MUTED, font=FONT_BODY)
        self.scan_status_label.pack(side="left", padx=10)

        # 提示信息
        ctk.CTkLabel(ctrl_frame,
                     text="插入新手柄后刷新列表；同一设备被多协议识别时会优先使用更准确的协议。",
                     text_color=COLOR_MUTED, font=FONT_BODY,
                     wraplength=900, justify="left").pack(anchor="w", pady=(8, 0))

    def _build_key_mapping_panel(self, parent):
        """构建开火、开镜和标记键映射区。"""
        key_frame = section(parent, "2. 键位映射")

        # Helper method for creating consistent dropdowns
        def create_option_menu(row, label_text, var_name, default_val, cmd_handler):
            ctk.CTkLabel(key_frame, text=label_text, width=120, anchor="e", text_color=COLOR_TEXT, font=FONT_BODY).grid(
                row=row, column=0, sticky="e", padx=(0, 10), pady=8)
            
            var = tk.StringVar(value=self.config.get(var_name, default_val))
            setattr(self, f"{var_name}_var", var)
            
            button_type = var_name.replace("_button", "")
            border_wrapper, combo = outline_option_menu(
                key_frame,
                variable=var,
                values=[default_val],
                command=lambda val, current_type=button_type: cmd_handler(
                    val, current_type),
                width=240,
            )
            border_wrapper.grid(row=row, column=1, sticky="w", pady=8)
            
            setattr(self, f"{button_type}_combo", combo)
            return combo

        create_option_menu(0, "开火键 (FIRE):", "fire_button", DEFAULT_FIRE_BUTTON, self._on_button_change)
        create_option_menu(1, "开镜键 (ADS):", "ads_button", DEFAULT_ADS_BUTTON, self._on_button_change)
        
        # [T2.1] 标记键
        create_option_menu(2, "标记键 (MARK):", "mark_button", DEFAULT_MARK_BUTTON, self._on_button_change)
        
        ctk.CTkLabel(key_frame, text_color=COLOR_MUTED, font=FONT_BODY,
                  text="标记键用于记录一次你认为压得好的片段，分析时会和算法评分对照。",
                  wraplength=900, justify="left").grid(
            row=3, column=1, sticky="w", pady=(0, 10))

        # 按键提示文本（动态更新）
        self.key_hint_label = ctk.CTkLabel(
            key_frame,
            text="按键标签会根据上方选中的控制器自动调整。",
            text_color=COLOR_MUTED, font=FONT_BODY, justify="left")
        self.key_hint_label.grid(
            row=4, column=0, columnspan=2, sticky="w", pady=5)

        # [Bug 修复] 测试键位按钮 —— 弹窗实时显示按键映射
        test_btn = line_button(
            key_frame,
            "测试键位映射",
            command=self._open_button_test_dialog,
            border_color=COLOR_TEXT,
            width=130,
        )
        # Bind hover to change text color
        test_btn.bind("<Enter>", lambda e: test_btn.configure(text_color=COLOR_ACCENT_MAGENTA, border_color=COLOR_ACCENT_MAGENTA))
        test_btn.bind("<Leave>", lambda e: test_btn.configure(text_color=COLOR_TEXT, border_color=COLOR_TEXT))
        test_btn.grid(row=0, column=2, rowspan=3, sticky="n", padx=(30, 0), pady=8)

        # 初次填充按键下拉（先按默认 XBOX 布局，扫描后会更新）
        cb_mod = _runtime_cb()
        self._refresh_button_combos(cb_mod.LAYOUT_XBOX if cb_mod else "xbox")

    def _on_button_change(self, combo, btn_type):
        """根据下拉框当前选项更新按键变量"""
        # For CTkOptionMenu, we have to find the logical code corresponding to the selected string
        val = combo.get() if hasattr(combo, 'get') else combo
        
        logical_code = None
        for display_name, l_code in getattr(self, '_current_button_options', []):
            if display_name == val:
                logical_code = l_code
                break
                
        if logical_code:
            if btn_type == "fire":
                self.fire_button_var.set(logical_code)
            elif btn_type == "ads":
                self.ads_button_var.set(logical_code)
            elif btn_type == "mark":
                self.mark_button_var.set(logical_code)
            self._persist_user_config()

    # ========== [Bug 修复] 键位映射实时测试 ==========
    def _open_button_test_dialog(self):
        """弹窗实时显示当前手柄按键状态。

        让用户能直观看到"我按 RT 软件认到了什么"，自检键位选错没。
        """
        if self.controller_mgr is None:
            messagebox.showinfo("请稍候", "控制器管理器还没初始化，等几秒再点。")
            return
        ctrl = self.controller_mgr.get_current_controller()
        if ctrl is None:
            messagebox.showwarning(
                "未选择手柄",
                "请先在「① 选择控制器」里选定一个手柄，然后再点测试。")
            return
        # 录制中不让开测试窗（同时读 controller 会冲突）
        if self.recorder is not None and getattr(
                self.recorder, "_thread", None) is not None and self.recorder._thread.is_alive():
            messagebox.showinfo("正在录制", "正在录制中，请先停止录制再测试键位。")
            return

        dlg = tk.Toplevel(self)
        dlg.title("🎯 键位映射实时测试")
        dlg.geometry("520x520")
        dlg.transient(self)
        # 居中
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 520) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 520) // 2
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        ttk.Label(dlg, text="按手柄上的任意键，看软件识别成什么",
                  font=FONT_BODY_BOLD).pack(pady=(15, 4))
        ttk.Label(
            dlg,
            text=f"当前手柄: {ctrl.display_string()}（布局: {ctrl.layout}）\n"
                 f"如果你按 RT 但下面显示的不是 'RT 右扳机'，说明按键映射有 bug，"
                 f"请反馈给作者。",
            foreground=COLOR_MUTED, justify="center",
            font=FONT_SMALL).pack(pady=(0, 10))

        # 三块显示区
        # 1. 当前按下的键（高亮）
        pressed_frame = ttk.LabelFrame(dlg, text="当前按下的键", padding=8)
        pressed_frame.pack(fill="x", padx=15, pady=4)
        pressed_lbl = tk.Label(
            pressed_frame, text="（无）", font=FONT_BODY_BOLD,
            foreground=COLOR_SUCCESS, height=2,
            wraplength=470, justify="center")
        pressed_lbl.pack(fill="x")

        # 2. 扳机数值
        trig_frame = ttk.LabelFrame(dlg, text="扳机模拟值", padding=8)
        trig_frame.pack(fill="x", padx=15, pady=4)
        lt_lbl = ttk.Label(trig_frame, text="左扳机 LT: 0.00",
                           font=FONT_BODY)
        lt_lbl.pack(anchor="w")
        rt_lbl = ttk.Label(trig_frame, text="右扳机 RT: 0.00",
                           font=FONT_BODY)
        rt_lbl.pack(anchor="w")

        # 3. 摇杆值
        stick_frame = ttk.LabelFrame(dlg, text="摇杆值", padding=8)
        stick_frame.pack(fill="x", padx=15, pady=4)
        ls_lbl = ttk.Label(stick_frame, text="左摇杆 L: ( 0.00,  0.00)",
                           font=FONT_MONO)
        ls_lbl.pack(anchor="w")
        rs_lbl = ttk.Label(stick_frame, text="右摇杆 R: ( 0.00,  0.00)",
                           font=FONT_MONO)
        rs_lbl.pack(anchor="w")

        # 4. 当前选定的开火/开镜键状态
        sel_frame = ttk.LabelFrame(
            dlg, text="你当前选定的键 / 实时状态", padding=8)
        sel_frame.pack(fill="x", padx=15, pady=4)

        fire_btn = self.fire_button_var.get()
        ads_btn = self.ads_button_var.get()
        mark_btn = (self.mark_button_var.get()
                    if hasattr(self, "mark_button_var") else "")
        cb_mod = _runtime_cb()
        if cb_mod is not None:
            fire_disp = cb_mod.get_button_display_name(ctrl.layout, fire_btn)
            ads_disp = cb_mod.get_button_display_name(ctrl.layout, ads_btn)
            mark_disp = (cb_mod.get_button_display_name(ctrl.layout, mark_btn)
                         if mark_btn else "")
        else:
            fire_disp = fire_btn
            ads_disp = ads_btn
            mark_disp = mark_btn

        fire_status = ttk.Label(
            sel_frame,
            text=f"🔫 开火键: {fire_disp}（{fire_btn}） — 状态: 未按",
            font=FONT_BODY)
        fire_status.pack(anchor="w", pady=2)
        ads_status = ttk.Label(
            sel_frame,
            text=f"🎯 开镜键: {ads_disp}（{ads_btn}） — 状态: 未按",
            font=FONT_BODY)
        ads_status.pack(anchor="w", pady=2)
        if mark_btn:
            mark_status = ttk.Label(
                sel_frame,
                text=f"⭐ 标记键: {mark_disp}（{mark_btn}） — 状态: 未按",
                font=FONT_BODY)
            mark_status.pack(anchor="w", pady=2)
        else:
            mark_status = None

        # 关闭按钮
        ttk.Button(dlg, text="关闭", command=dlg.destroy).pack(pady=8)

        # 后台线程读取手柄状态
        stop_evt = _get_runtime_attr("threading", threading).Event()
        dlg.protocol("WM_DELETE_WINDOW",
                     lambda: (stop_evt.set(), dlg.destroy()))

        def _poll():
            while not stop_evt.is_set():
                try:
                    state = self.controller_mgr.read_state(ctrl)
                except Exception:
                    time.sleep(0.1)
                    continue
                # 在主线程更新 UI
                try:
                    self.after(0, _update_ui, state)
                except tk.TclError:
                    return
                time.sleep(0.05)  # 20 Hz 更新

        def _update_ui(state):
            try:
                # 当前按下的键
                pressed = []
                cb_mod = _runtime_cb()
                if cb_mod is not None:
                    for logical, val in state.buttons.items():
                        if val:
                            disp = cb_mod.get_button_display_name(ctrl.layout, logical)
                            if disp.startswith("(") and disp.endswith(")"):
                                continue  # 跳过 "(无)"
                            pressed.append(f"{disp} [{logical}]")
                # 扳机
                if state.lt > 0.05:
                    pressed.append(f"LT 扳机 ({state.lt:.2f})")
                if state.rt > 0.05:
                    pressed.append(f"RT 扳机 ({state.rt:.2f})")

                pressed_lbl.configure(
                    text="\n".join(pressed) if pressed else "（无 — 按一下手柄按键试试）",
                    foreground=COLOR_SUCCESS if pressed else COLOR_MUTED)

                lt_lbl.configure(text=f"左扳机 LT: {state.lt:.2f}")
                rt_lbl.configure(text=f"右扳机 RT: {state.rt:.2f}")
                ls_lbl.configure(
                    text=f"左摇杆 L: ({state.lx:+.2f}, {state.ly:+.2f})")
                rs_lbl.configure(
                    text=f"右摇杆 R: ({state.rx:+.2f}, {state.ry:+.2f})")

                # 当前选定键的状态
                fire_pressed = bool(state.buttons.get(fire_btn, False))
                if fire_btn == "TRIGGER_RIGHT":
                    fire_pressed = state.rt > 0.5
                elif fire_btn == "TRIGGER_LEFT":
                    fire_pressed = state.lt > 0.5
                fire_status.configure(
                    text=f"🔫 开火键: {fire_disp}（{fire_btn}） — "
                         f"状态: {'✅ 按下' if fire_pressed else '未按'}",
                    foreground=COLOR_SUCCESS if fire_pressed else COLOR_TEXT)

                ads_pressed = bool(state.buttons.get(ads_btn, False))
                if ads_btn == "TRIGGER_RIGHT":
                    ads_pressed = state.rt > 0.5
                elif ads_btn == "TRIGGER_LEFT":
                    ads_pressed = state.lt > 0.5
                ads_status.configure(
                    text=f"🎯 开镜键: {ads_disp}（{ads_btn}） — "
                         f"状态: {'✅ 按下' if ads_pressed else '未按'}",
                    foreground=COLOR_SUCCESS if ads_pressed else COLOR_TEXT)

                if mark_status is not None:
                    mark_pressed = bool(state.buttons.get(mark_btn, False))
                    mark_status.configure(
                        text=f"⭐ 标记键: {mark_disp}（{mark_btn}） — "
                             f"状态: {'✅ 按下' if mark_pressed else '未按'}",
                        foreground=COLOR_SUCCESS if mark_pressed else COLOR_TEXT)
            except tk.TclError:
                pass

        _get_runtime_attr("threading", threading).Thread(target=_poll, daemon=True,
                         name="button-test-poll").start()

    # ========== 控制器槽位管理 ==========
    def _scan_controllers(self):
        """[T-1.2] 异步扫描手柄并刷新槽位显示。

        用户手动点"扫描"按钮也可能因为 pygame.joystick.quit/init 而短暂卡顿，
        所以同样放后台线程跑，主线程只负责更新 UI。
        """
        if self.controller_mgr is None:
            if self._init_pending:
                # 初始化还在进行，按钮被点了：忽略，让初始化完成后自然刷新
                try:
                    configure_notice(self.scan_status_label, "正在初始化手柄驱动，请稍候…")
                except Exception:
                    pass
            return

        # 立刻给用户视觉反馈
        try:
            configure_notice(self.scan_status_label, "正在扫描…")
        except Exception:
            pass

        def _scan_worker():
            try:
                msg = self.controller_mgr.scan_and_assign()
                err = None
            except Exception as e:
                msg = ""
                err = str(e)
            self.after(0, self._on_scan_done, msg, err)

        _get_runtime_attr("threading", threading).Thread(
            target=_scan_worker, daemon=True, name="controller-scan"
        ).start()

    def _on_scan_done(self, msg: str, err):
        """[T-1.2] 扫描完成回调，主线程刷新 UI。"""
        try:
            if err is not None:
                configure_notice(self.scan_status_label, f"扫描失败：{err}", "error")
                return
            configure_notice(self.scan_status_label, msg)
            self._refresh_slot_display()
            self._refresh_button_combos_for_current_slot()
        except Exception as e:
            print(f"[警告] 扫描完成回调失败: {e}")

    def _refresh_slot_display(self):
        """根据当前槽位状态刷新 GUI"""
        if self.controller_mgr is None:
            return
        for i, widget in enumerate(self.slot_widgets):
            slot = self.controller_mgr.slots[i]
            if slot is None:
                widget["label"].configure(text="[空]", text_color=COLOR_MUTED)
                widget["radio"].configure(state="disabled")
            else:
                widget["label"].configure(
                    text=slot.display_string(),
                    text_color=COLOR_TEXT)
                widget["radio"].configure(state="normal")

        # 同步 slot_var 和 ControllerManager 的当前槽位
        cur = self.controller_mgr.get_current_slot()
        if cur is not None:
            self.slot_var.set(cur)

    def _on_slot_changed(self):
        """用户切换槽位时调用"""
        if self.controller_mgr is None:
            return
        new_slot = self.slot_var.get()
        if self.controller_mgr.slots[new_slot] is not None:
            self.controller_mgr.set_current_slot(new_slot)
            self._refresh_button_combos_for_current_slot()

    def _refresh_button_combos_for_current_slot(self):
        """根据当前选中槽位的手柄布局，刷新键位下拉框"""
        cb_mod = _runtime_cb()
        if self.controller_mgr is None or cb_mod is None:
            return
        ctrl = self.controller_mgr.get_current_controller()
        if ctrl is None:
            self._refresh_button_combos(cb_mod.LAYOUT_XBOX)
        else:
            self._refresh_button_combos(ctrl.layout)

    def _refresh_button_combos(self, layout: str):
        """根据按键布局，重新填充开火键和开镜键的下拉框选项"""
        cb_mod = _runtime_cb()
        if cb_mod is None:
            return
        options = cb_mod.get_button_options_for_layout(layout)
        self._current_button_options = options  # 保存供 _on_button_change 用

        display_labels = [opt[0] for opt in options]
        logical_codes = [opt[1] for opt in options]

        # Helper method for setting up values for CTkOptionMenu
        def update_combo(combo, var, old_val, default_val):
            combo.configure(values=display_labels)
            if old_val in logical_codes:
                combo.set(display_labels[logical_codes.index(old_val)])
                var.set(old_val)
            elif default_val in logical_codes:
                combo.set(display_labels[logical_codes.index(default_val)])
                var.set(default_val)
            elif display_labels:
                combo.set(display_labels[0])
                var.set(logical_codes[0])

        # 更新开火键下拉
        update_combo(self.fire_combo, self.fire_button_var, self.fire_button_var.get(), DEFAULT_FIRE_BUTTON)

        # 更新开镜键下拉
        update_combo(self.ads_combo, self.ads_button_var, self.ads_button_var.get(), DEFAULT_ADS_BUTTON)

        # [T2.1] 更新标记键下拉
        if hasattr(self, "mark_combo"):
            update_combo(self.mark_combo, self.mark_button_var, self.mark_button_var.get(), DEFAULT_MARK_BUTTON)

        # 更新提示文字
        layout_label_map = {
            cb_mod.LAYOUT_XBOX: "XBOX 风格",
            cb_mod.LAYOUT_PS: "PlayStation 风格",
            cb_mod.LAYOUT_PS_EDGE: "DualSense Edge 风格（含背键 FN1/FN2/RB1/RB2）",
            cb_mod.LAYOUT_SWITCH: "Switch 风格",
            cb_mod.LAYOUT_GENERIC: "通用 / 未识别",
        }
        layout_name = layout_label_map.get(layout, layout)
        self.key_hint_label.configure(
            text=f"当前布局: {layout_name}。按键标签会根据控制器协议自动适配。"
                 "选错键位会导致 FIRE/ADS 标记不亮。")
        self._persist_user_config()
