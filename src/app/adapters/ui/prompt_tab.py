"""AI 提示词标签页 mixin。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

try:
    from app.adapters.prompt import build_ai_prompt
    from app.adapters.ui.theme import (
        COLOR_MUTED,
        COLOR_TEXT,
        FONT_BODY,
        hint_label,
        line_button,
        section,
        show_message,
        solid_button,
        textbox,
    )
except ModuleNotFoundError:
    from src.app.adapters.prompt import build_ai_prompt
    from src.app.adapters.ui.theme import (
        COLOR_MUTED,
        COLOR_TEXT,
        FONT_BODY,
        hint_label,
        line_button,
        section,
        show_message,
        solid_button,
        textbox,
    )


class PromptTabMixin:
    """封装 AI 提示词标签页的 UI 与操作。"""

    def _build_ai_tab(self, parent):
        intro_body = section(parent, "1. 使用方式")
        hint_label(
            intro_body,
            "分析完成后会自动带入报告。你只需要补齐手柄型号、曲线节点和体感痛点，然后复制给 AI。",
            wraplength=980,
        ).pack(anchor="w", pady=(0, 6))

        prompt_body = section(parent, "2. 提示词内容", "可直接编辑")
        self.prompt_text = textbox(prompt_body, height=420)
        self.prompt_text.pack(fill="both", expand=True)
        self._refresh_prompt_template()

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(14, 8))
        line_button(
            btn_frame,
            "刷新内容",
            command=self._refresh_prompt_template,
            width=130,
        ).pack(side="left")
        line_button(
            btn_frame,
            "保存为文件",
            command=self._save_prompt,
            width=130,
        ).pack(side="left", padx=(10, 0))
        solid_button(
            btn_frame,
            "复制全部",
            command=self._copy_prompt,
            width=140,
        ).pack(side="right")

    def _refresh_prompt_template(self):
        content = build_ai_prompt(self.last_report_content)
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", content)

    def _copy_prompt(self):
        content = self.prompt_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        show_message("info", "复制完成", "提示词已复制到剪贴板。", parent=self)

    def _save_prompt(self):
        content = self.prompt_text.get("1.0", "end-1c")
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")],
            initialfile=f"ai_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if f:
            try:
                Path(f).write_text(content, encoding="utf-8")
                show_message("info", "保存完成", f"已保存到 {f}", parent=self)
            except Exception as e:
                show_message("error", "保存失败", str(e), parent=self)
