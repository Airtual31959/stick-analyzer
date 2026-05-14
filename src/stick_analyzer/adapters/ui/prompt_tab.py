"""AI 提示词标签页 mixin。"""
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from stick_analyzer.adapters.prompt import build_ai_prompt
except ModuleNotFoundError:
    from src.stick_analyzer.adapters.prompt import build_ai_prompt


class PromptTabMixin:
    """封装 AI 提示词标签页的 UI 与操作。"""

    def _build_ai_tab(self, parent):
        intro_frame = ttk.LabelFrame(parent, text="使用说明", padding=10)
        intro_frame.pack(fill="x", padx=10, pady=10)

        intro_text = (
            "完成分析后，本工具会自动把数据报告嵌入到提示词模板中。\n\n"
            "你需要在下方文本框中填写三处内容（已用【】标记）：\n"
            "  1. 你的手柄型号 + 曲线编辑方式 + 可调节点数\n"
            "     ⚠ 不同手柄支持的曲线点数不一样（2/4/6/8 点常见），\n"
            "       不能直接照搬别人的 JSON，否则会因为点数不对导入失败。\n"
            "     ⚠ 部分手柄不支持 JSON 导入，只能在 APP 里手动拖动节点，\n"
            "       这种情况要让 AI 给出每个节点的具体 X、Y 数值。\n\n"
            "  2. 你当前的曲线坐标（按你手柄实际的点数填）\n"
            "  3. 你的体感痛点（越具体越好）\n\n"
            "填完后点 [📋 复制全部到剪贴板]，粘贴给 AI（推荐 Claude / ChatGPT），\n"
            "AI 会综合数据 + 你的痛点 + 你的手柄限制，给出针对性的调整方案。"
        )
        ttk.Label(intro_frame, text=intro_text,
                  justify="left", foreground="#333").pack(anchor="w")

        # 提示词编辑区
        prompt_frame = ttk.LabelFrame(parent, text="提示词内容（可编辑）", padding=10)
        prompt_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame, font=("Consolas", 9), wrap="word")
        self.prompt_text.pack(fill="both", expand=True)

        self._refresh_prompt_template()

        # 按钮区
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="🔄 刷新（用最新分析报告）",
                   command=self._refresh_prompt_template).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 复制全部到剪贴板",
                   command=self._copy_prompt).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="💾 保存为文件",
                   command=self._save_prompt).pack(side="left", padx=5)

    def _refresh_prompt_template(self):
        content = build_ai_prompt(self.last_report_content)
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", content)

    def _copy_prompt(self):
        content = self.prompt_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        messagebox.showinfo("成功", "提示词已复制到剪贴板！\n粘贴给 AI 即可。")

    def _save_prompt(self):
        content = self.prompt_text.get("1.0", "end-1c")
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")],
            initialfile=f"ai_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if f:
            try:
                Path(f).write_text(content, encoding="utf-8")
                messagebox.showinfo("成功", f"已保存到 {f}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
