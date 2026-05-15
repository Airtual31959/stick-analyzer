"""参考曲线收集标签页 mixin。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

try:
    from app.adapters.prompt import inject_reference_curves
    from app.adapters.ui.theme import (
        COLOR_LINE,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        hint_label,
        line_button,
        section,
        show_message,
        solid_button,
        textbox,
    )
except ModuleNotFoundError:
    from src.app.adapters.prompt import inject_reference_curves
    from src.app.adapters.ui.theme import (
        COLOR_LINE,
        COLOR_MUTED,
        COLOR_PANEL,
        COLOR_TEXT,
        FONT_BODY,
        FONT_BODY_BOLD,
        hint_label,
        line_button,
        section,
        show_message,
        solid_button,
        textbox,
    )


class InverseTabMixin:
    """封装参考曲线收集标签页的 UI 与操作。"""

    def _build_inverse_tab(self, parent):
        intro_body = section(parent, "1. 收集参考曲线")
        hint_label(
            intro_body,
            "把社区、朋友或游戏截图识别出的曲线整理到右侧文本区。建议至少收集 3 条不同来源，再注入到 AI 提示词。",
            wraplength=980,
        ).pack(anchor="w")

        middle = ctk.CTkFrame(parent, fg_color="transparent")
        middle.pack(fill="both", expand=True, padx=10, pady=(18, 8))
        middle.grid_columnconfigure(0, weight=1)
        middle.grid_columnconfigure(1, weight=2)
        middle.grid_rowconfigure(0, weight=1)

        guide = ctk.CTkFrame(
            middle,
            fg_color=COLOR_PANEL,
            border_width=1,
            border_color=COLOR_LINE,
            corner_radius=0,
        )
        guide.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(
            guide,
            text="推荐来源",
            text_color=COLOR_TEXT,
            font=FONT_BODY_BOLD,
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(14, 6))
        guide_text = (
            "B站 / 抖音：Apex 曲线、FPS 手柄配置\n"
            "贴吧 / Reddit / Discord：手柄灵敏度分享\n"
            "调参 APP：官方或社区曲线\n"
            "游戏截图：让 AI 识别曲线节点"
        )
        ctk.CTkLabel(
            guide,
            text=guide_text,
            text_color=COLOR_MUTED,
            font=FONT_BODY,
            justify="left",
            anchor="nw",
        ).pack(fill="x", padx=14, pady=(0, 14))

        editor = ctk.CTkFrame(middle, fg_color="transparent")
        editor.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            editor,
            text="参考曲线内容",
            text_color=COLOR_TEXT,
            font=FONT_BODY_BOLD,
            anchor="w",
        ).pack(anchor="w", pady=(0, 6))
        self.refs_text = textbox(editor, height=360)
        self.refs_text.pack(fill="both", expand=True)

        default_refs = (
            "=== 参考曲线 1 ===\n"
            "来源：\n"
            "曲线：\n"
            "评价：\n\n"
            "=== 参考曲线 2 ===\n"
            "来源：\n"
            "曲线：\n"
            "评价：\n\n"
            "=== 参考曲线 3 ===\n"
            "来源：\n"
            "曲线：\n"
            "评价：\n"
        )
        self.refs_text.insert("1.0", default_refs)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(8, 8))
        line_button(btn_frame, "清空", command=self._clear_refs, width=110).pack(
            side="left")
        line_button(btn_frame, "保存到文件", command=self._save_refs, width=130).pack(
            side="left", padx=(10, 0))
        solid_button(
            btn_frame,
            "注入到 AI 提示词",
            command=self._inject_refs_to_prompt,
            width=180,
        ).pack(side="right")

    def _clear_refs(self):
        if show_message("question", "确认清空", "确定要清空所有参考曲线吗？", parent=self):
            self.refs_text.delete("1.0", "end")

    def _save_refs(self):
        content = self.refs_text.get("1.0", "end-1c").strip()
        if not content:
            show_message("warning", "无法保存", "参考曲线内容为空。", parent=self)
            return
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")],
            initialfile=f"reference_curves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if f:
            try:
                Path(f).write_text(content, encoding="utf-8")
                show_message("info", "保存完成", f"已保存到 {f}", parent=self)
            except Exception as e:
                show_message("error", "保存失败", str(e), parent=self)

    def _inject_refs_to_prompt(self):
        """把参考曲线追加到 AI 提示词中。"""
        content = self.refs_text.get("1.0", "end-1c").strip()
        if not content:
            show_message("warning", "无法注入", "请先填写参考曲线。", parent=self)
            return

        current = self.prompt_text.get("1.0", "end-1c")
        new_text = inject_reference_curves(current, content)

        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", new_text)
        self._show_page("prompt")
        show_message("info", "注入完成", "参考曲线已添加到 AI 提示词。", parent=self)
