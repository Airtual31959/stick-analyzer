"""参考曲线收集标签页 mixin。"""
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from stick_analyzer.adapters.prompt import inject_reference_curves
except ModuleNotFoundError:
    from src.stick_analyzer.adapters.prompt import inject_reference_curves


class InverseTabMixin:
    """封装参考曲线收集标签页的 UI 与操作。"""

    def _build_inverse_tab(self, parent):
        # 上半：使用说明
        intro_frame = ttk.LabelFrame(parent, text="使用说明", padding=10)
        intro_frame.pack(fill="x", padx=10, pady=10)

        intro_text = (
            "本标签页提供「参考曲线收集」的工具和指南。\n"
            "\n"
            "💡 核心理念：\n"
            "  • 数学反函数不一定是体感最佳，比纯算法更可靠的是「别人调教过、被广泛验证的曲线」\n"
            "  • 把多份参考曲线一起交给 AI，让 AI 综合判断「业内共识 + 你的数据 + 你的痛点」\n"
            "  • 你的角色：收集 + 整理 + 描述体感；AI 的角色：综合分析 + 微调建议\n"
            "\n"
            "🔒 工具承诺：本工具不会向游戏发送任何输入、不读取游戏画面、不操作你的手柄。"
            "所有调整最终由你自己手动完成。"
        )
        ttk.Label(intro_frame, text=intro_text, justify="left",
                  foreground="#333", wraplength=900).pack(anchor="w")

        # 中部：左右分栏
        middle_frame = ttk.Frame(parent)
        middle_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ====== 左侧：去哪找参考曲线（指南）======
        left = ttk.LabelFrame(middle_frame, text="📚 去哪找参考曲线", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        guide_text = (
            "🎯 推荐渠道：\n"
            "\n"
            "1️⃣ 国内社区\n"
            "   • B站搜索：「Apex 曲线 调教」「Apex 手柄 配置」\n"
            "                「FPS 反曲线」「手柄 灵敏度 曲线」\n"
            "   • 抖音搜索：同上关键词\n"
            "   • 贴吧：APEX英雄吧、手柄吧、FPS游戏吧\n"
            "\n"
            "2️⃣ 国外社区\n"
            "   • Reddit：r/apexlegends、r/CompetitiveApex\n"
            "   • Discord：相关游戏的 controller-tips 频道\n"
            "   • YouTube：搜「Apex aim training」「stick curve」\n"
            "\n"
            "3️⃣ 调参 APP / 软件\n"
            "   • 北通宙斯系列、雷蛇飓兽 APP\n"
            "   • 飞智、莱仕达、八位堂的官方 APP\n"
            "   • 部分 APP 内置「社区曲线」分享功能\n"
            "\n"
            "4️⃣ 游戏内截图\n"
            "   • 进入游戏「灵敏度/手柄」设置\n"
            "   • 截图响应曲线图表\n"
            "   • 把截图丢给 AI（Claude / ChatGPT），让它\n"
            "     识别曲线节点的 (X, Y) 数值\n"
            "\n"
            "🌟 重点：找 3-5 条不同来源的曲线，对比共性，\n"
            "         共性部分往往就是业内共识的合理范围。"
        )
        ttk.Label(left, text=guide_text, justify="left",
                  font=("", 9), foreground="#333").pack(anchor="w", pady=(0, 8))

        # ====== 右侧：参考曲线收集区 ======
        right = ttk.LabelFrame(middle_frame,
            text="📝 把找到的参考曲线粘贴到这里", padding=10)
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))

        right_intro = (
            "格式建议（可自由发挥，不用严格遵守）：\n"
            "  来源：（B站某 UP / 朋友 / 截图识别 等）\n"
            "  曲线：[0,0, 6,5.5, 16,19.5, ...] 或描述\n"
            "  评价：（这条曲线的体感特点）"
        )
        ttk.Label(right, text=right_intro, justify="left",
                  foreground="#666", font=("", 8)).pack(anchor="w", pady=(0, 4))

        self.refs_text = scrolledtext.ScrolledText(
            right, font=("Consolas", 9), height=15, wrap="word")
        self.refs_text.pack(fill="both", expand=True)

        # 默认填充模板
        default_refs = (
            "=== 参考曲线 1 ===\n"
            "来源：（在这里填来源）\n"
            "曲线：（节点数据或描述）\n"
            "评价：（体感特点）\n"
            "\n"
            "=== 参考曲线 2 ===\n"
            "来源：\n"
            "曲线：\n"
            "评价：\n"
            "\n"
            "=== 参考曲线 3 ===\n"
            "来源：\n"
            "曲线：\n"
            "评价：\n"
        )
        self.refs_text.insert("1.0", default_refs)

        # 按钮区
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="🗑 清空",
                   command=self._clear_refs).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="💾 保存到文件",
                   command=self._save_refs).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="➕ 注入到 AI 提示词",
                   command=self._inject_refs_to_prompt).pack(side="left", padx=2)

        # 底部小贴士
        tip_frame = ttk.Frame(parent)
        tip_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(tip_frame,
            text="💡 小贴士：参考曲线收集得越全，AI 给出的建议越精准。"
                 "建议至少收集 3 条不同来源的曲线再做对比。",
            foreground="#0078D4", font=("", 9, "italic")).pack(anchor="w")

    def _clear_refs(self):
        if messagebox.askyesno("确认", "确定要清空所有内容吗？"):
            self.refs_text.delete("1.0", "end")

    def _save_refs(self):
        content = self.refs_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("提示", "内容为空，没什么可保存的")
            return
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt")],
            initialfile=f"reference_curves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        if f:
            try:
                Path(f).write_text(content, encoding="utf-8")
                messagebox.showinfo("成功", f"已保存到 {f}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    def _inject_refs_to_prompt(self):
        """把参考曲线追加到 AI 提示词中"""
        content = self.refs_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("提示", "请先在右侧填写参考曲线")
            return

        current = self.prompt_text.get("1.0", "end-1c")
        new_text = inject_reference_curves(current, content)

        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", new_text)
        self.notebook.select(2)
        messagebox.showinfo("成功",
            "参考曲线已注入到 AI 提示词中！\n"
            "已自动跳转到「③ 生成 AI 调参提示词」标签页。")
