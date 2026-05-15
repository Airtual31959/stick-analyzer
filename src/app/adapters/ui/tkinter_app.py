"""
摇杆射击行为分析工具 v2.1 - GUI 主程序
功能：录制 → 分析 → 生成 AI 调参提示词 → 参考曲线收集

v2.1 新增/改进:
- 第七节：腰射 vs 开镜 不对称分析（差异 > 30% 给针对性曲线建议）
- 第八节：走位 vs 站桩 模式对比（走位组 ×1.3 阈值放宽）
- 过冲细分类型：大幅过冲（>0.15）vs 小抖动（0.05-0.15），调参建议精确到高/中/低段
- 行为分类细化：完美稳定 ⭐ / 稳定射击 ✓ / 接近稳定 / 中等稳定 等档位
  + 每档玩家直觉解释
- TMR 传感器措辞修正：从「霍尔阵营」改为「接近碳膜」（已是主流 FPS 默认）
- AI 提示词模板加入新章节解读规则 + 关键澄清"RC 是钝化操作不会导致过冲"
- 关键 bug 修复：SDL 跨线程 button 状态读不到（SDL_JOYSTICK_THREAD）
- XBOX 风格手柄优先 XInput（避免 pygame/SDL 在第三方控制器上的兼容性问题）
- 高回报率手柄（4000-8000Hz）卡顿优化（屏蔽 SDL joystick events）
- 采样率说明改为协议上限解释（不再误导成"链路瓶颈"）

v2.0 既有功能：
- 双驱动控制器支持：pygame（PS / Switch / 通用 HID）+ XInput（XBOX 系列）
- 4 槽位手柄管理（按插入顺序）
- 按键标签自动适配（PS 显示 × ○ □ △，XBOX 显示 A B X Y）
- DualSense Edge 背键 FN1/FN2/RB1/RB2 支持
- 三步式工作流：录制 → 分析 → AI 提示词
- 参考曲线收集指南（纯文字引导，不操作游戏）
"""
import threading
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import customtkinter as ctk

try:
    from app.app_paths import (
        get_app_data_dir,
        get_config_path,
        get_default_output_dir,
        resolve_output_dir,
    )
    from app.application import (
        CalibrationRequest,
        CalibrateController,
        RecordSession,
        RecordingInputError,
        RecordSessionRequest,
    )
    from app.adapters.storage import CsvRecordingWriter
    from app.adapters.ui.analyze_tab import (
        AnalyzeRecording,
        AnalyzeRecordingRequest,
        AnalyzeTabMixin,
        _import_analyzer,
    )
    from app.adapters.ui.inverse_tab import InverseTabMixin
    from app.adapters.ui.prompt_tab import PromptTabMixin
    from app.adapters.ui.record_tab import RecordTabMixin
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
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_FAMILY,
        FONT_SECTION,
        FONT_SMALL,
        FONT_TITLE,
        configure_notice,
        line_button,
        show_message,
        solid_button,
        textbox,
    )
except ModuleNotFoundError:
    from src.app.app_paths import (
        get_app_data_dir,
        get_config_path,
        get_default_output_dir,
        resolve_output_dir,
    )
    from src.app.application import (
        CalibrationRequest,
        CalibrateController,
        RecordSession,
        RecordingInputError,
        RecordSessionRequest,
    )
    from src.app.adapters.storage import CsvRecordingWriter
    from src.app.adapters.ui.analyze_tab import (
        AnalyzeRecording,
        AnalyzeRecordingRequest,
        AnalyzeTabMixin,
        _import_analyzer,
    )
    from src.app.adapters.ui.inverse_tab import InverseTabMixin
    from src.app.adapters.ui.prompt_tab import PromptTabMixin
    from src.app.adapters.ui.record_tab import RecordTabMixin
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
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        FONT_FAMILY,
        FONT_SECTION,
        FONT_SMALL,
        FONT_TITLE,
        configure_notice,
        line_button,
        show_message,
        solid_button,
        textbox,
    )

try:
    from app.adapters import controller as cb
    from app.adapters.ui import error_reporter
except ModuleNotFoundError:
    try:
        from src.app.adapters import controller as cb
        from src.app.adapters.ui import error_reporter
    except ModuleNotFoundError:
        cb = None
        error_reporter = None

# ==================== 默认配置 ====================
DEFAULT_FIRE_BUTTON = "RIGHT_SHOULDER"   # 逻辑代码（RB / R1 / R 等等）
DEFAULT_ADS_BUTTON = "TRIGGER_LEFT"      # LT / L2，FPS 玩家最常用的开镜键
DEFAULT_MARK_BUTTON = "BACK"             # 玩家手动标记键
TARGET_RATE_HZ = 500   # pygame 实际能力 ~500Hz；XInput 也用同值确保 GUI 流畅

APP_VERSION = "v2.1"
# ===================================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(1.08)

NAV_ITEMS = (
    ("record", "01", "录制摇杆数据", "RECORD"),
    ("analyze", "02", "分析数据", "ANALYZE"),
    ("prompt", "03", "生成 AI 调参提示词", "PROMPT"),
    ("inverse", "04", "参考曲线收集", "REFERENCE"),
)


class _SystemClock:
    def time_ns(self):
        return time.time_ns()

    def sleep(self, duration_s):
        time.sleep(duration_s)


class _CountingControllerReader:
    def __init__(self, reader):
        self._reader = reader
        self.sample_count = 0

    def read_state(self, controller_info):
        state = self._reader.read_state(controller_info)
        self.sample_count += 1
        return state


def _recording_progress_to_dict(progress):
    return asdict(progress)


def _recording_summary_to_dict(summary):
    data = asdict(summary)
    data["output"] = str(summary.output)
    return data


class StickRecorder:
    """GUI 后台线程包装器，录制业务委托给 RecordSession。"""

    PERF_PROFILES = {
        "high":   {"rate": 500, "gui_interval": 0.1, "label": "高精度（默认）"},
        "normal": {"rate": 250, "gui_interval": 0.2, "label": "平衡"},
        "low":    {"rate": 125, "gui_interval": 0.5, "label": "低性能（旧电脑）"},
    }

    def __init__(self, output_path, metadata, fire_button, ads_button,
                 controller_info, controller_manager,
                 on_update, on_done,
                 perf_profile="high",
                 noise_floor_x=0.0, noise_floor_y=0.0,
                 mark_button=None,
                 session_factory=None,
                 writer_factory=None,
                 clock=None):
        self.output_path = Path(output_path)
        self.metadata = dict(metadata)
        self.fire_button = fire_button       # 逻辑代码（如 RIGHT_SHOULDER）
        self.ads_button = ads_button
        self.controller_info = controller_info  # ControllerInfo
        self.controller_manager = controller_manager  # ControllerManager
        self.on_update = on_update
        self.on_done = on_done
        self.perf_profile = perf_profile
        # [T0.3] 录制前校准得到的传感器本底（rx/ry 的标准差）
        self.noise_floor_x = float(noise_floor_x)
        self.noise_floor_y = float(noise_floor_y)
        # [T2.1] 玩家手动标记按键（按一下打一个 "good" 标记到 CSV）
        self.mark_button = mark_button       # 逻辑代码或 None
        self._session_factory = session_factory or RecordSession
        self._writer_factory = writer_factory or CsvRecordingWriter
        self._clock = clock or _SystemClock()
        self._session = None
        self._stop_requested = False
        self._thread = None

    def start(self):
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_requested = True
        if self._session is not None:
            self._session.stop()

    def _run(self):
        if cb is None:
            self.on_done(False,
                "控制器模块未找到，请确认程序文件完整")
            return

        if self.controller_info is None:
            self.on_done(False, "未选择手柄，请先在控制器选择区选定一个手柄")
            return

        try:
            writer = self._writer_factory()
            self._session = self._session_factory(
                self.controller_manager, self._clock, writer)
            if self._stop_requested:
                self._session.stop()
            done_called = False

            def handle_done(summary):
                nonlocal done_called
                done_called = True
                self._handle_done(summary)

            summary = self._session.execute(
                self._build_request(),
                progress=self._handle_progress,
                done=handle_done)
            if not done_called:
                self._handle_done(summary)
        except RecordingInputError as e:
            self.on_done(False, str(e))
        except OSError as e:
            self.on_done(False, f"无法创建文件: {e}")
        except Exception as e:
            self.on_done(False, f"录制过程中发生异常: {e}")

    def _build_request(self):
        return RecordSessionRequest(
            output_path=self.output_path,
            metadata=self.metadata,
            fire_button=self.fire_button,
            ads_button=self.ads_button,
            mark_button=self.mark_button,
            controller_info=self.controller_info,
            perf_profile=self.perf_profile,
            noise_floor_x=self.noise_floor_x,
            noise_floor_y=self.noise_floor_y,
            logical_buttons=cb.LOGICAL_BUTTONS,
        )

    def _handle_progress(self, progress):
        self.on_update(_recording_progress_to_dict(progress))

    def _handle_done(self, summary):
        self.on_done(True, _recording_summary_to_dict(summary))


class App(RecordTabMixin, AnalyzeTabMixin, PromptTabMixin, InverseTabMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"摇杆射击行为分析工具 {APP_VERSION}")
        self.geometry("1180x920")
        self.minsize(1040, 720)
        self.configure(fg_color=COLOR_BG)
        self.recorder = None
        self.csv_path_var = tk.StringVar()
        self.last_report_content = ""
        self.config = self._load_config()
        self._config_ready = False

        # 安装全局异常钩子（捕获所有未处理异常，弹出反馈窗口）
        if error_reporter is not None:
            try:
                error_reporter.install_exception_hook(self)
            except Exception as e:
                print(f"[警告] 异常钩子安装失败: {e}")

        # [T-1.2 紧急修复] 控制器管理器改为异步初始化
        # 此前在 __init__ 里同步创建 ControllerManager()，会调用 pygame.init()，
        # 在某些 Windows 系统上会阻塞数秒（扫描音视频子系统、HID 设备），
        # 导致窗口建好但 mainloop 未启动 → 窗口不显示，进程在跑但 hwnd=0。
        # 现在改为：__init__ 里只搭 UI 框架，异步线程后台跑重型初始化。
        self.controller_mgr = None
        self._init_pending = True   # UI 上有 controller_mgr 检查的地方据此判断

        # 槽位选择变量（4 个槽位）
        self.slot_var = tk.IntVar(value=0)
        self.slot_radio_buttons = []  # GUI Radiobutton 引用，用于动态更新

        self._build_ui()
        self._config_ready = True
        self._persist_user_config()

        # UI 搭好后立即让窗口可见，再异步启动重型初始化
        # update_idletasks 会把所有挂起的几何计算执行掉，update 会让窗口实际显示
        self.update_idletasks()
        self.update()

        # 异步启动控制器后端：mainloop 启动后 50ms 触发，确保窗口已渲染
        self.after(50, self._async_bootstrap_controllers)

    def _is_window_alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _schedule_bootstrap_done(self, mgr, scan_msg: str, err_msg) -> None:
        """窗口已关闭时丢弃后台初始化结果，避免 Tk 回调访问失效控件。"""
        if not self._is_window_alive():
            return
        try:
            self.after(0, self._on_bootstrap_done, mgr, scan_msg, err_msg)
        except tk.TclError:
            return

    def _async_bootstrap_controllers(self):
        """[T-1.2] 在后台线程里创建 ControllerManager 并扫描手柄。

        流程：
          1. 主线程调用本方法 → 立刻在 scan_status_label 显示"正在初始化…"
          2. 启动 daemon 线程跑 _bootstrap_worker（创建 ControllerManager + scan）
          3. 工作线程完成后用 self.after(0, _on_bootstrap_done, ...) 回主线程
          4. 主线程更新 self.controller_mgr 并刷新 UI
        如果 cb 模块本身缺失，本方法会立即在主线程报错（不需要后台线程）。
        """
        if cb is None:
            show_message(
                "error",
                "缺少模块",
                "找不到控制器模块，请确认程序文件完整",
                parent=self,
            )
            self._init_pending = False
            try:
                configure_notice(
                    self.scan_status_label,
                    "后端模块缺失，无法识别手柄",
                    "error",
                )
            except Exception:
                pass
            return

        # 显示"初始化中"
        try:
            configure_notice(self.scan_status_label, "正在初始化手柄驱动…")
        except Exception:
            pass

        def _bootstrap_worker():
            """后台线程：创建 ControllerManager 并完成首次扫描。"""
            err_msg = None
            mgr = None
            scan_msg = ""
            try:
                mgr = cb.ControllerManager()
                # 首次扫描，把结果一并带回主线程
                try:
                    scan_msg = mgr.scan_and_assign()
                except Exception as e:
                    scan_msg = f"扫描出错: {e}"
            except Exception as e:
                import traceback
                err_msg = f"{e}\n\n{traceback.format_exc()}"

            # 切回主线程更新 UI；窗口可能已经被用户关闭。
            self._schedule_bootstrap_done(mgr, scan_msg, err_msg)

        threading.Thread(
            target=_bootstrap_worker,
            daemon=True,
            name="controller-bootstrap",
        ).start()

    def _on_bootstrap_done(self, mgr, scan_msg: str, err_msg):
        """[T-1.2] 异步初始化完成回调，运行在主线程。"""
        if not self._is_window_alive():
            return

        self._init_pending = False

        if err_msg is not None:
            show_message(
                "error",
                "驱动初始化失败",
                "控制器驱动初始化时出错：\n\n" + err_msg,
                parent=self,
            )
            try:
                configure_notice(
                    self.scan_status_label,
                    "驱动初始化失败，请重启程序",
                    "error",
                )
            except Exception:
                pass
            return

        self.controller_mgr = mgr

        # 检查驱动可用性（迁移自原 __init__）
        if mgr is not None and not mgr.has_pygame() and not mgr.has_xinput():
            show_message(
                "error",
                "缺少驱动库",
                "未检测到 pygame 或 XInput-Python 库。\n"
                "请运行：pip install pygame XInput-Python",
                parent=self,
            )

        # 把首次扫描的结果显示出来 + 刷新 UI
        try:
            if scan_msg:
                configure_notice(self.scan_status_label, scan_msg)
            self._refresh_slot_display()
            self._refresh_button_combos_for_current_slot()
        except tk.TclError:
            return
        except Exception as e:
            print(f"[警告] 初始扫描后刷新 UI 失败: {e}")

        # [T0.1] 首次启动显示欢迎面板（用 after 让 UI 先渲染）
        if self._is_window_alive():
            self.after(300, self._show_welcome_if_needed)

    # ========== [T0.1] 欢迎面板 ==========
    def _config_path(self) -> Path:
        """用户配置文件路径：~/.stickanalyzer/config.json"""
        return get_config_path()

    def _load_config(self) -> dict:
        path = self._config_path()
        if not path.exists():
            return {}
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _save_config(self, cfg: dict):
        path = self._config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self.config = dict(cfg)
        except Exception as e:
            print(f"[警告] 保存配置失败: {e}")

    def _persist_user_config(self):
        """持久化会影响下次启动体验的用户设置。"""
        if not getattr(self, "_config_ready", False):
            return

        cfg = dict(getattr(self, "config", {}) or {})
        if hasattr(self, "fire_button_var"):
            cfg["fire_button"] = self.fire_button_var.get()
        if hasattr(self, "ads_button_var"):
            cfg["ads_button"] = self.ads_button_var.get()
        if hasattr(self, "mark_button_var"):
            cfg["mark_button"] = self.mark_button_var.get()
        if hasattr(self, "perf_profile_var"):
            cfg["perf_profile"] = self.perf_profile_var.get()
        if hasattr(self, "out_dir_var"):
            cfg["out_dir"] = self.out_dir_var.get()
        self._save_config(cfg)

    def _show_welcome_if_needed(self):
        """首次启动显示欢迎面板，介绍工具用途和 3 步工作流。"""
        cfg = self._load_config()
        if cfg.get("welcome_seen") is True:
            return

        dlg = ctk.CTkToplevel(self, fg_color=COLOR_BG)
        dlg.title("欢迎使用摇杆射击行为分析工具")
        dlg.geometry("660x430")
        dlg.transient(self)
        dlg.resizable(False, False)
        # 居中
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 660) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 430) // 2
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        ctk.CTkLabel(
            dlg,
            text="欢迎使用 摇杆射击行为分析工具",
            font=FONT_SECTION,
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=28, pady=(24, 4))
        ctk.CTkLabel(
            dlg,
            text="录制手柄摇杆轨迹，分析压枪稳定度，再生成可复制的调参提示词。",
            font=FONT_BODY,
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=28, pady=(0, 18))
        ctk.CTkFrame(dlg, height=1, fg_color=COLOR_LINE).pack(
            fill="x", padx=28, pady=(0, 16))

        body_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=28, pady=0)

        what_text = (
            "1. 录制：连接手柄，完成 3 秒静止校准后开始采集。\n"
            "2. 分析：选择刚生成的 CSV，查看稳定度、采样率和报告。\n"
            "3. 调参：复制提示词给 AI，结合你的曲线节点和体感痛点调整。\n\n"
            "本工具只读取手柄输入，不向游戏发送操作，也不读取游戏画面。"
        )
        text_widget = textbox(body_frame, height=180)
        text_widget.insert("1.0", what_text)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True)

        bottom = ctk.CTkFrame(dlg, fg_color="transparent")
        bottom.pack(fill="x", padx=28, pady=18)

        dont_show_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bottom, text="不再显示这个欢迎信息",
            variable=dont_show_var,
            fg_color=COLOR_ACCENT_MAGENTA,
            hover_color=COLOR_ACCENT_MAGENTA_HOVER,
            border_color=COLOR_LINE_DARK,
            text_color=COLOR_TEXT,
            font=FONT_BODY,
        ).pack(side="left")

        def _close():
            if dont_show_var.get():
                cfg["welcome_seen"] = True
                self._save_config(cfg)
            dlg.destroy()

        solid_button(bottom, "开始使用", command=_close, width=120).pack(side="right")
        dlg.protocol("WM_DELETE_WINDOW", _close)

    # ========== [T1.1] RC 强度自动计算 ==========
    def _recompute_rc_intensity(self):
        """监听 RC 范围/数值/方向变化，自动算百分比和等级码，刷新 UI 标签。

        计算结果同时写入 self.meta_vars[f"{prefix}_intensity"]，录制时直接用。
        """
        if not hasattr(self, "_rc_auto_labels"):
            return
        for prefix, lbl in self._rc_auto_labels.items():
            try:
                rmin = float(self.meta_vars[f"{prefix}_range_min"].get() or 0)
                rmax = float(self.meta_vars[f"{prefix}_range_max"].get() or 0)
                value = float(self.meta_vars[prefix].get() or 0)
                direction = self.meta_vars[f"{prefix}_direction"].get()
            except (ValueError, KeyError, AttributeError):
                continue

            pct, code, display = self._calc_rc_intensity(
                rmin, rmax, value, direction)
            intensity_var = self.meta_vars.get(f"{prefix}_intensity")
            if intensity_var is not None:
                intensity_var.set(code)
            try:
                lbl.configure(text=display)
            except tk.TclError:
                # 控件已销毁
                pass

    @staticmethod
    def _calc_rc_intensity(rmin, rmax, value, direction):
        """根据 RC 范围、当前值、方向算出强度。

        返回 (pct: float, code: str, display: str)
            code ∈ {"none", "antishake", "light", "medium", "strong", "extreme"}
            display 是给 UI 显示的中文标签
        """
        if rmin == 0 and rmax == 0:
            return 0.0, "none", "→ 无 RC 功能"
        if direction == "neutral" or value == 0:
            return 0.0, "none", "→ 0% 中性"

        max_abs = max(abs(rmin), abs(rmax))
        if max_abs == 0:
            return 0.0, "none", "→ 范围无效"
        pct = min(100.0, abs(value) / max_abs * 100.0)

        if direction == "antishake":
            # 防抖方向不细分等级，统一归到 antishake
            return pct, "antishake", f"→ {pct:.0f}% 防抖"

        # 动感方向按百分比分级（边界值含在下界，与 GUI 描述"0-30% 轻度"一致）
        if pct <= 30:
            code, name = "light", "轻度"
        elif pct <= 60:
            code, name = "medium", "中度"
        elif pct <= 90:
            code, name = "strong", "强"
        else:
            code, name = "extreme", "极限"
        return pct, code, f"→ {pct:.0f}% {name}增抖"

    def _on_rc_dual_toggle(self):
        """[T1.1] 单 RC / 双 RC 模式切换显示。"""
        if not hasattr(self, "_rc_single_frame"):
            return
        if self.meta_vars["rc_dual"].get():
            # 切到双 RC：隐藏单 RC，显示双 RC
            self._rc_single_frame.pack_forget()
            self._rc_dual_frame.pack(fill="x")
        else:
            # 切到单 RC：隐藏双 RC，显示单 RC
            self._rc_dual_frame.pack_forget()
            self._rc_single_frame.pack(fill="x")
        self._recompute_rc_intensity()

    def _build_ui(self):
        self._configure_ttk_style()

        shell = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        shell.pack(fill="both", expand=True)

        self._build_sidebar(shell)

        content = ctk.CTkFrame(shell, fg_color=COLOR_BG, corner_radius=0)
        content.pack(side="left", fill="both", expand=True)

        self._build_banner(content)
        self._build_page_host(content)

        self._show_page("record")

    def _configure_ttk_style(self):
        """让尚未迁移的 ttk 内容融入新的深色 CTk 外壳。"""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure(
            "TLabelframe",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_LINE,
            lightcolor=COLOR_LINE,
            darkcolor=COLOR_LINE,
        )
        style.configure(
            "TLabelframe.Label",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            font=FONT_BODY_BOLD,
        )
        style.configure(
            "TButton",
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_LINE,
            focusthickness=1,
            focuscolor=COLOR_ACCENT_MAGENTA,
            padding=(10, 6),
            font=FONT_BODY_BOLD,
        )
        style.map(
            "TButton",
            background=[("active", COLOR_HOVER_BG), ("disabled", "#E5E7EB")],
            foreground=[("disabled", "#9CA3AF")],
        )
        style.configure(
            "TRadiobutton",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            indicatorcolor=COLOR_PANEL,
            font=FONT_BODY,
        )
        style.configure(
            "TCheckbutton",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            indicatorcolor=COLOR_PANEL,
            font=FONT_BODY,
        )
        style.configure(
            "TEntry",
            fieldbackground=COLOR_PANEL,
            foreground=COLOR_TEXT,
            insertcolor=COLOR_TEXT,
            bordercolor=COLOR_LINE,
            font=FONT_BODY,
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLOR_PANEL,
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            arrowcolor=COLOR_TEXT,
            bordercolor=COLOR_LINE,
            font=FONT_BODY,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=COLOR_PANEL,
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            arrowcolor=COLOR_TEXT,
            bordercolor=COLOR_LINE,
            font=FONT_BODY,
        )

    def _build_sidebar(self, parent):
        sidebar = ctk.CTkFrame(
            parent,
            width=248,
            fg_color=COLOR_PANEL,
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="STICK\nANALYZER",
            font=FONT_TITLE,
            text_color=COLOR_TEXT,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(28, 4))
        ctk.CTkLabel(
            sidebar,
            text=APP_VERSION,
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=26, pady=(0, 28))

        ctk.CTkFrame(sidebar, height=1, fg_color=COLOR_LINE).pack(
            fill="x", padx=24, pady=(0, 20))

        self._nav_buttons = {}
        self._nav_indicators = {}
        for page_key, index, label, watermark in NAV_ITEMS:
            row = ctk.CTkFrame(sidebar, fg_color="transparent", corner_radius=0)
            row.pack(fill="x", padx=12, pady=3)
            indicator = ctk.CTkFrame(
                row,
                width=3,
                height=38,
                fg_color="transparent",
                corner_radius=0,
            )
            indicator.pack(side="left", fill="y", padx=(0, 8))
            button = ctk.CTkButton(
                row,
                text=watermark,
                anchor="w",
                fg_color="transparent",
                hover_color=COLOR_HOVER_BG,
                text_color=COLOR_MUTED,
                border_width=0,
                corner_radius=0,
                height=42,
                font=FONT_BODY_BOLD,
                command=lambda key=page_key: self._show_page(key),
            )
            button.pack(side="left", fill="x", expand=True)
            self._nav_buttons[page_key] = button
            self._nav_indicators[page_key] = indicator

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(
            fill="both", expand=True)
        ctk.CTkLabel(
            sidebar,
            text="完全免费 · 谨防付费转卖",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 24))

    def _build_banner(self, parent):
        banner = ctk.CTkFrame(
            parent,
            fg_color="#FEF3C7", # Light yellow warning bg
            border_color="#F59E0B", # Orange border
            border_width=1,
            corner_radius=0,
        )
        banner.pack(fill="x", padx=24, pady=(18, 0))

        ctk.CTkLabel(
            banner,
            text="本软件完全免费",
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=(14, 20), pady=9)
        ctk.CTkLabel(
            banner,
            text="作者：B站 / 抖音 josef_0464    反馈交流 QQ 群：611624374",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(side="left", pady=9)
        ctk.CTkLabel(
            banner,
            text="如果你是付费获得的，说明你被骗了",
            font=FONT_BODY_BOLD,
            text_color=COLOR_ACCENT_MAGENTA,
        ).pack(side="right", padx=14, pady=9)

    def _build_page_host(self, parent):
        self._page_host = ctk.CTkFrame(parent, fg_color=COLOR_BG, corner_radius=0)
        self._page_host.pack(fill="both", expand=True, padx=24, pady=18)
        self._page_frames = {}

        builders = {
            "record": self._build_record_tab,
            "analyze": self._build_analyze_tab,
            "prompt": self._build_ai_tab,
            "inverse": self._build_inverse_tab,
        }
        for page_key, index, _label, watermark in NAV_ITEMS:
            page = self._build_page(page_key, index, watermark)
            builders[page_key](page)

    def _build_page(self, page_key, index, watermark):
        if page_key == "record":
            page = ctk.CTkFrame(
                self._page_host,
                fg_color="transparent",
                corner_radius=0,
            )
        else:
            page = ctk.CTkScrollableFrame(
                self._page_host,
                fg_color="transparent",
                corner_radius=0,
                scrollbar_button_color=COLOR_LINE,
                scrollbar_button_hover_color=COLOR_ACCENT_MAGENTA,
            )
        page.grid(row=0, column=0, sticky="nsew")
        self._page_host.grid_rowconfigure(0, weight=1)
        self._page_host.grid_columnconfigure(0, weight=1)
        self._page_frames[page_key] = page

        header = ctk.CTkFrame(page, fg_color="transparent", corner_radius=0)
        header.pack(fill="x", padx=10, pady=(2, 8))
        ctk.CTkLabel(
            header,
            text=watermark,
            font=FONT_TITLE,
            text_color=COLOR_TEXT,
        ).pack(side="left", padx=(14, 0))
        ctk.CTkFrame(page, height=1, fg_color=COLOR_LINE).pack(
            fill="x", padx=10, pady=(0, 12))
        return page

    def _show_page(self, page_key):
        if page_key not in self._page_frames:
            return
        for key, frame in self._page_frames.items():
            if key == page_key:
                frame.grid()
            else:
                frame.grid_remove()
        for key, button in self._nav_buttons.items():
            indicator = self._nav_indicators.get(key)
            if key == page_key:
                button.configure(
                    text_color=COLOR_TEXT,
                    fg_color="transparent",
                    border_width=0,
                )
                if indicator is not None:
                    indicator.configure(fg_color=COLOR_ACCENT_MAGENTA)
            else:
                button.configure(
                    text_color=COLOR_MUTED,
                    fg_color="transparent",
                    border_width=0,
                )
                if indicator is not None:
                    indicator.configure(fg_color="transparent")


def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # 程序启动失败的最后一道防线
        import traceback
        tb = traceback.format_exc()
        # 尝试用错误反馈窗口
        try:
            if error_reporter is not None:
                # 创建一个临时 root 来承载错误窗口
                temp_root = tk.Tk()
                temp_root.withdraw()
                error_reporter.show_error_dialog(
                    temp_root, "程序启动失败", str(e), e,
                    "程序无法正常启动")
                temp_root.mainloop()
            else:
                # 退化到原生 messagebox
                tk.Tk().withdraw()
                messagebox.showerror(
                    "启动失败",
                    f"程序无法启动:\n\n{e}\n\n"
                    f"请把错误信息发给 B站/抖音 josef_0464 或 QQ 群 611624374\n\n"
                    f"详细堆栈:\n{tb}")
        except Exception:
            # 连 tkinter 都用不了，就只能 print 了
            print("=" * 60)
            print("程序启动失败")
            print("=" * 60)
            print(tb)
            print("=" * 60)
            print("请把以上错误信息发给：")
            print("  B站 / 抖音: josef_0464")
            print("  QQ 群: 611624374 (星辰不妙屋)")
            print("=" * 60)
            input("按回车键退出...")


if __name__ == "__main__":
    main()
