from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
import numpy as np

# 关键：必须在 import pyplot 之前设置后端为 Agg（无 GUI）
# Agg 后端不会尝试创建窗口图标，避免 PyInstaller 打包后的 _tkinter.TclError
# 同时内存释放更彻底，性能更好（我们只需要保存图片，不需要交互式显示）
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


def _setup_chinese_font() -> None:
    """智能配置中文字体，兼容 PyInstaller 打包。"""
    candidates = [
        "Microsoft YaHei", "Microsoft YaHei UI", "SimHei",
        "SimSun", "NSimSun", "FangSong", "KaiTi",
        "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = [name for name in candidates if name in available]
    if not chosen:
        # PyInstaller 打包后可能找不到，强制扫描 Windows 字体目录
        win_fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        if os.path.isdir(win_fonts_dir):
            for fn in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"):
                fp = os.path.join(win_fonts_dir, fn)
                if os.path.exists(fp):
                    try:
                        font_manager.fontManager.addfont(fp)
                    except Exception:
                        pass
            available = {f.name for f in font_manager.fontManager.ttflist}
            chosen = [name for name in candidates if name in available]
    chosen.append("DejaVu Sans")
    matplotlib.rcParams["font.sans-serif"] = chosen
    matplotlib.rcParams["axes.unicode_minus"] = False


_setup_chinese_font()


class MatplotlibPlotter:
    def plot_burst(self, metrics: Mapping[str, Any], output_path: Path, title: str) -> None:
        """单个爆发的波形图。"""
        m = metrics
        win = m["data"]
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

        # 子图 1：右摇杆 X/Y
        axes[0].plot(win["rel_t"], win["rx"], label="RX 水平",
                     color="#E74C3C", linewidth=1.2)
        axes[0].plot(win["rel_t"], win["ry"], label="RY 垂直",
                     color="#3498DB", linewidth=1.2)
        axes[0].axvline(0, color="red", linestyle="--", alpha=0.7, label="开火起始")
        axes[0].axvline(m["duration"], color="orange", linestyle="--",
                        alpha=0.7, label="开火结束")
        axes[0].axhline(0, color="gray", linestyle=":", alpha=0.3)
        axes[0].axvspan(0, m["duration"], alpha=0.08, color="red",
                        label="开火持续期")
        axes[0].set_ylabel("右摇杆值")
        axes[0].set_title(title)
        axes[0].legend(loc="upper right", fontsize=8, framealpha=0.85)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_ylim(-1.05, 1.05)

        info = (
            f"开火前 100ms 稳定度: {m['pre_stability']:.4f}\n"
            f"开火中 300ms 稳定度: {m['during_stability']:.4f}\n"
            f"开火期方向反转: {m['total_reversals']} 次\n"
            f"主导推杆区间: X={m['dominant_input_low']:.0f}–"
            f"{m['dominant_input_high']:.0f}\n"
            f"开镜: {'是' if m['is_ads'] else '否'} | "
            f"走位: {'是' if m['is_moving'] else '否'}"
        )
        axes[0].text(0.02, 0.97, info, transform=axes[0].transAxes,
                     verticalalignment="top", fontsize=8,
                     bbox=dict(boxstyle="round,pad=0.4",
                               facecolor="white", edgecolor="gray", alpha=0.85))

        # 子图 2：推杆量
        magnitude = np.sqrt(win["rx"] ** 2 + win["ry"] ** 2)
        axes[1].plot(win["rel_t"], magnitude, color="#9B59B6", linewidth=1.5)
        axes[1].axvline(0, color="red", linestyle="--", alpha=0.7)
        axes[1].axvline(m["duration"], color="orange", linestyle="--", alpha=0.7)
        axes[1].axvspan(0, m["duration"], alpha=0.08, color="red")
        axes[1].fill_between(win["rel_t"], 0, magnitude, alpha=0.2, color="#9B59B6")
        axes[1].set_ylabel("右摇杆推杆量 |R|")
        axes[1].grid(True, alpha=0.3)
        axes[1].set_ylim(0, 1.05)

        # 子图 3：开火/开镜状态 + 左摇杆
        axes[2].plot(win["rel_t"], win["lx"], label="LX (左右走位)",
                     color="#16A085", linewidth=1.0, alpha=0.8)
        axes[2].plot(win["rel_t"], win["ly"], label="LY (前后走位)",
                     color="#F39C12", linewidth=1.0, alpha=0.8)
        axes[2].fill_between(win["rel_t"], -0.05,
                             win["fire"].astype(float) * 1.05,
                             alpha=0.25, color="red", label="开火中")
        axes[2].fill_between(win["rel_t"], -0.05,
                             win["ads"].astype(float) * (-1.05),
                             alpha=0.25, color="green", label="开镜中")
        axes[2].axvline(0, color="red", linestyle="--", alpha=0.7)
        axes[2].axvline(m["duration"], color="orange", linestyle="--", alpha=0.7)
        axes[2].set_ylabel("左摇杆 / 状态")
        axes[2].set_xlabel("相对开火时间 (秒)")
        axes[2].legend(loc="upper right", fontsize=8, framealpha=0.85, ncol=2)
        axes[2].grid(True, alpha=0.3)
        axes[2].set_ylim(-1.1, 1.1)

        plt.tight_layout()
        plt.savefig(output_path, dpi=110, bbox_inches="tight")
        plt.close(fig)
        # 显式释放 - 修复 v2.0 内存泄漏
        del fig, axes
        gc.collect()

    def plot_summary(self, events: Sequence[Mapping[str, Any]], output_path: Path) -> None:
        """统计总览。

        [T-1.1 紧急修复] 此前 pre_stabs / dur_stabs 用 if not np.isnan() 单独过滤，
        导致和 mags / revs 长度不一致，scatter 时报 "x and y must be the same size"。
        现在改为：用一次循环同步过滤所有指标，保证四个列表索引对齐。
        """
        metrics_list = [e["metrics"] for e in events if e["metrics"] is not None]
        if not metrics_list:
            return

        # 同步过滤：四个列表索引一一对应
        valid_metrics = [
            m for m in metrics_list
            if not np.isnan(m["pre_stability"])
            and not np.isnan(m["during_stability"])
        ]
        pre_stabs = [m["pre_stability"] for m in valid_metrics]
        dur_stabs = [m["during_stability"] for m in valid_metrics]
        revs = [m["total_reversals"] for m in valid_metrics]
        mags = [m["avg_magnitude"] for m in valid_metrics]
        centers = [(m["dominant_input_low"] + m["dominant_input_high"]) / 2
                   for m in valid_metrics]

        if not valid_metrics:
            # 全部事件都缺关键指标，没法画散点图
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        if pre_stabs:
            axes[0, 0].hist(pre_stabs, bins=20, color="#3498DB",
                            alpha=0.7, edgecolor="black")
            axes[0, 0].axvline(0.04, color="green", linestyle="--", label="稳定 (<0.04)")
            axes[0, 0].axvline(0.10, color="red", linestyle="--", label="抖动 (>0.10)")
        axes[0, 0].set_xlabel("开火前 100ms 稳定度")
        axes[0, 0].set_ylabel("事件数")
        axes[0, 0].set_title("开火前稳定度分布（瞄准是否稳）")
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        if dur_stabs:
            axes[0, 1].hist(dur_stabs, bins=20, color="#E67E22",
                            alpha=0.7, edgecolor="black")
            axes[0, 1].axvline(0.04, color="green", linestyle="--", label="稳定 (<0.04)")
            axes[0, 1].axvline(0.08, color="red", linestyle="--", label="抖动 (>0.08)")
        axes[0, 1].set_xlabel("开火中 300ms 稳定度（去趋势）")
        axes[0, 1].set_ylabel("事件数")
        axes[0, 1].set_title("开火中稳定度分布（压枪是否稳）")
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 散点图：mags 和 pre_stabs 现在长度一定相等
        colors = ["#27AE60" if m["is_ads"] else "#E67E22" for m in valid_metrics]
        axes[1, 0].scatter(mags, pre_stabs, c=colors, alpha=0.7, s=50)
        axes[1, 0].set_xlabel("平均推杆量")
        axes[1, 0].set_ylabel("开火前稳定度")
        axes[1, 0].set_title("推杆量 vs 稳定度（绿=开镜，橙=腰射）")
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].hist(centers, bins=20, color="#9B59B6",
                        alpha=0.7, edgecolor="black")
        axes[1, 1].set_xlabel("主导推杆量（百分比 0-100）")
        axes[1, 1].set_ylabel("事件数")
        axes[1, 1].set_title("你最常用的推杆区间（曲线调参核心依据）")
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=110, bbox_inches="tight")
        plt.close(fig)
        # 显式释放 - 修复 v2.0 内存泄漏
        del fig, axes
        gc.collect()


_DEFAULT_PLOTTER = MatplotlibPlotter()


def plot_burst(metrics: Mapping[str, Any], output_path: Path, title: str) -> None:
    _DEFAULT_PLOTTER.plot_burst(metrics, output_path, title)


def plot_summary(events: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    _DEFAULT_PLOTTER.plot_summary(events, output_path)
