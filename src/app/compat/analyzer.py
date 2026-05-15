"""
摇杆数据分析器 v2.1
================================
报告章节结构（v2.1）:
    一、开火前稳定度
    二、开火中稳定度
    三、过冲/反转统计 + 大幅过冲 vs 小抖动 细分（T3.3 新）
    四、行为分类 + 玩家直觉解释（T3.4 新）
    五、主导推杆区间（霍尔反死区补偿建议）
    六、自动化调参建议（针对性高/中/低段 + RC 澄清）
    七、腰射 vs 开镜 不对称分析（T3.1 新）
    八、走位 vs 站桩 模式对比（T3.2 新，1.3x 阈值放宽）
    九、今日状态一致性（CV 计算）
    十、玩家自评 vs 算法评分对照

变化：
- 自动检测所有"开火爆发"事件，无需外部击杀时间戳
- 兼容 v1.0 / v2.0 / v2.1 的 CSV 格式
- 完整爆发分析模式：分析每次开火从开始到结束的全过程

使用方法：
    # 自动分析所有开火爆发（推荐）
    python main.py -args cli stick_log_xxx.csv

    # 仅分析最新 N 个事件
    python main.py -args cli stick_log_xxx.csv --max_events 30

    # 想跳过太短的爆发（如误触）
    python main.py -args cli stick_log_xxx.csv --min_duration 0.2

输出文件（与 CSV 同目录）：
    <basename>_report.txt        : 文字报告 + 调参建议
    <basename>_event_NN.png      : 每次开火事件的波形图
    <basename>_summary.png       : 总览统计图
"""

import sys
from pathlib import Path

import pandas as pd

try:
    from app.application import (
        AnalysisResult,
        AnalyzeRecording,
        AnalyzeRecordingRequest,
    )
    from app.application.use_cases import (
        MissingFireColumnError,
        NoFireBurstsError,
    )
    from app.domain.constants import (
        CLASSIFICATION_EXPLANATIONS as DOMAIN_CLASSIFICATION_EXPLANATIONS,
        DEFAULT_MIN_DURATION_S as DOMAIN_DEFAULT_MIN_DURATION_S,
        DURING_FIRE_STABILITY_MS as DOMAIN_DURING_FIRE_STABILITY_MS,
        FIRE_GAP_THRESHOLD_S as DOMAIN_FIRE_GAP_THRESHOLD_S,
        PRE_FIRE_STABILITY_MS as DOMAIN_PRE_FIRE_STABILITY_MS,
        WEAPON_RPM as DOMAIN_WEAPON_RPM,
        WINDOW_AFTER_S as DOMAIN_WINDOW_AFTER_S,
        WINDOW_BEFORE_S as DOMAIN_WINDOW_BEFORE_S,
    )
    from app.domain.services.burst_analyzer import (
        analyze_burst as domain_analyze_burst,
    )
    from app.domain.services.burst_classifier import (
        classify_burst as domain_classify_burst,
    )
    from app.domain.services.fire_burst_detector import (
        detect_fire_bursts as domain_detect_fire_bursts,
    )
    from app.domain.services.threshold_policy import (
        get_stability_thresholds as domain_get_stability_thresholds,
    )
    from app.domain.services.weapon_policy import (
        detect_weapon_rpm as domain_detect_weapon_rpm,
        rpm_to_during_window_ms as domain_rpm_to_during_window_ms,
    )
except ModuleNotFoundError:
    from src.app.application import (
        AnalysisResult,
        AnalyzeRecording,
        AnalyzeRecordingRequest,
    )
    from src.app.application.use_cases import (
        MissingFireColumnError,
        NoFireBurstsError,
    )
    from src.app.domain.constants import (
        CLASSIFICATION_EXPLANATIONS as DOMAIN_CLASSIFICATION_EXPLANATIONS,
        DEFAULT_MIN_DURATION_S as DOMAIN_DEFAULT_MIN_DURATION_S,
        DURING_FIRE_STABILITY_MS as DOMAIN_DURING_FIRE_STABILITY_MS,
        FIRE_GAP_THRESHOLD_S as DOMAIN_FIRE_GAP_THRESHOLD_S,
        PRE_FIRE_STABILITY_MS as DOMAIN_PRE_FIRE_STABILITY_MS,
        WEAPON_RPM as DOMAIN_WEAPON_RPM,
        WINDOW_AFTER_S as DOMAIN_WINDOW_AFTER_S,
        WINDOW_BEFORE_S as DOMAIN_WINDOW_BEFORE_S,
    )
    from src.app.domain.services.burst_analyzer import (
        analyze_burst as domain_analyze_burst,
    )
    from src.app.domain.services.burst_classifier import (
        classify_burst as domain_classify_burst,
    )
    from src.app.domain.services.fire_burst_detector import (
        detect_fire_bursts as domain_detect_fire_bursts,
    )
    from src.app.domain.services.threshold_policy import (
        get_stability_thresholds as domain_get_stability_thresholds,
    )
    from src.app.domain.services.weapon_policy import (
        detect_weapon_rpm as domain_detect_weapon_rpm,
        rpm_to_during_window_ms as domain_rpm_to_during_window_ms,
    )

# ==================== 配置 ====================
WINDOW_BEFORE_S = DOMAIN_WINDOW_BEFORE_S
WINDOW_AFTER_S = DOMAIN_WINDOW_AFTER_S
FIRE_GAP_THRESHOLD_S = DOMAIN_FIRE_GAP_THRESHOLD_S
DEFAULT_MIN_DURATION_S = DOMAIN_DEFAULT_MIN_DURATION_S
PRE_FIRE_STABILITY_MS = DOMAIN_PRE_FIRE_STABILITY_MS
DURING_FIRE_STABILITY_MS = DOMAIN_DURING_FIRE_STABILITY_MS
# ===============================================


# ==================== [T2.3] 武器射速感知 ====================
WEAPON_RPM = DOMAIN_WEAPON_RPM
CLASSIFICATION_EXPLANATIONS = DOMAIN_CLASSIFICATION_EXPLANATIONS


def detect_weapon_rpm(weapons_str: str) -> int:
    """从用户填的武器字段里推断 RPM。识别不到返回 0（按默认处理）。"""
    return domain_detect_weapon_rpm(weapons_str)


def rpm_to_during_window_ms(rpm: int) -> int:
    """根据武器射速选择 during_stability 窗口长度。

    - 高射速（>900 RPM）：200ms（够看到 3-4 发节奏）
    - 中等射速：300ms（默认）
    - 低射速（<150 RPM，霰弹/狙击/单发）：返回 0 表示跳过分析
    """
    return domain_rpm_to_during_window_ms(rpm)


def load_csv(path: Path) -> tuple:
    """加载 CSV 数据，同时解析头部元数据。返回 (df, metadata)

    [T0.2] metadata 里会自动追加：
        effective_rate     : 实际有效采样率（排除底层重发的重复帧）
        duplicate_ratio    : 重复帧占比（0.0 ~ 1.0）
        nominal_rate       : 标称采样率（来自 CSV 头）
    [T0.3] 也会读取：
        noise_floor_x / noise_floor_y : 录制前校准得到的传感器本底
    """
    print(f"[*] 加载 {path}...")

    # 先读取元数据行（以 # 开头）
    metadata = {}
    skip_rows = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                skip_rows += 1
                # 解析 # meta: key=value
                if "meta:" in line:
                    try:
                        kv = line.split("meta:", 1)[1].strip()
                        k, v = kv.split("=", 1)
                        metadata[k.strip()] = v.strip()
                    except ValueError:
                        pass
            else:
                break

    df = pd.read_csv(path, skiprows=skip_rows)
    df["elapsed_s"] = df["elapsed_s"].astype(float)

    # [T0.2] 检测重复帧并算有效采样率
    # 连续两行 (rx, ry, lx, ly) 完全相同 = 底层未更新（HID 重发）
    if len(df) > 1 and all(c in df.columns for c in ("rx", "ry", "lx", "ly")):
        sig = (df["rx"].round(6).astype(str) + "|"
               + df["ry"].round(6).astype(str) + "|"
               + df["lx"].round(6).astype(str) + "|"
               + df["ly"].round(6).astype(str))
        dup_mask = sig.eq(sig.shift())
        dup_count = int(dup_mask.sum())
        dup_ratio = dup_count / len(df)
        duration_s = float(df["elapsed_s"].iloc[-1] - df["elapsed_s"].iloc[0])
        nominal_rate = len(df) / max(duration_s, 1e-6)
        effective_rate = nominal_rate * (1.0 - dup_ratio)
        metadata["nominal_rate"] = f"{nominal_rate:.1f}"
        metadata["effective_rate"] = f"{effective_rate:.1f}"
        metadata["duplicate_ratio"] = f"{dup_ratio:.4f}"

    print(f"[√] 加载完成：{len(df)} 帧，时长 {df['elapsed_s'].iloc[-1]:.1f} 秒")
    if "effective_rate" in metadata:
        print(f"[√] 标称采样率 {metadata['nominal_rate']}Hz，"
              f"有效 {metadata['effective_rate']}Hz "
              f"（重复帧 {float(metadata['duplicate_ratio'])*100:.1f}%）")
    if metadata:
        print(f"[√] 元数据：{metadata}")
    return df, metadata


def get_stability_thresholds(metadata: dict) -> dict:
    """根据 RC 动感强度等级 + 传感器类型调整稳定度阈值。

    [T1.3] 传感器类型放宽倍数：
        - TMR：×1.00（已接近碳膜的延迟与线性度，主流 FPS 手柄出厂默认）
        - 碳膜 ALPS：×1.00（传统线性高、中心灵敏、零延迟）
        - 霍尔：×1.25（中心钝、圆周率差、斜角信号缺失、ms 级延迟，
                       非 FPS 主流方案）
        - 不确定：按 TMR 处理（当前主流，最贴近实际）

    注: TMR 算法已经成熟，跟碳膜差异很小，不需要再单独放宽阈值；
        霍尔仍有显著的中心钝化、回中虚位、磁场干扰问题。

    优先用 rc_ads_intensity 字段（动感强度等级），向后兼容老格式 rc_ads（数值）。
    """
    return domain_get_stability_thresholds(metadata)


def detect_fire_bursts(df: pd.DataFrame,
                       min_duration_s: float = DEFAULT_MIN_DURATION_S) -> list:
    """检测开火爆发段，返回 [(start_s, end_s), ...]"""
    return domain_detect_fire_bursts(df, min_duration_s)


def analyze_burst(df: pd.DataFrame, burst_start: float, burst_end: float,
                  noise_floor_x: float = 0.0,
                  noise_floor_y: float = 0.0,
                  weapon_rpm: int = 0) -> dict:
    """分析单个开火爆发

    [T0.3] noise_floor_x / noise_floor_y 是录制前校准得到的传感器本底标准差。
    pre_stability / during_stability 会减去本底（按平方相减再开方），
    保证报告里看到的"抖动"是真正手部+曲线引起的，不混入硬件本身的噪声。

    [T2.3] weapon_rpm 是武器射速，用于动态调整 during_stability 窗口长度：
        - >900 RPM（高射速冲锋枪）：200ms 窗口
        - 150-900 RPM（中等射速）：300ms 窗口（默认）
        - <150 RPM（霰弹/狙击/单发）：跳过 during 分析（NaN）
    """
    return domain_analyze_burst(
        df,
        burst_start,
        burst_end,
        noise_floor_x=noise_floor_x,
        noise_floor_y=noise_floor_y,
        weapon_rpm=weapon_rpm,
    )


def classify_burst(m: dict) -> str:
    """根据指标分类射击行为
    [T3.4] 档位从粗到细: 完美稳定 ⭐ > 稳定射击 ✓ > 接近稳定 > 中等稳定 > 严重问题 ⚠
    """
    return domain_classify_burst(m)


def _load_matplotlib_plotter():
    try:
        from app.adapters.reporting import matplotlib_plotter
    except ModuleNotFoundError as exc:
        if not (exc.name or "").startswith("app"):
            raise
        from src.app.adapters.reporting import matplotlib_plotter
    return matplotlib_plotter


def _load_text_report_renderer():
    try:
        from app.adapters.reporting import text_report_renderer
    except ModuleNotFoundError as exc:
        if not (exc.name or "").startswith("app"):
            raise
        from src.app.adapters.reporting import text_report_renderer
    return text_report_renderer


def plot_burst(m: dict, output_path: Path, title: str):
    """单个爆发的波形图。"""
    return _load_matplotlib_plotter().plot_burst(m, output_path, title)


def plot_summary(events: list, output_path: Path):
    """统计总览。"""
    return _load_matplotlib_plotter().plot_summary(events, output_path)


def generate_report(events: list, csv_path: Path,
                    metadata: dict, thresholds: dict) -> str:
    """生成文字报告。"""
    return _load_text_report_renderer().generate_report(
        events, csv_path, metadata, thresholds)


def main(argv=None):
    """兼容旧 CLI 入口，真实命令编排位于 adapters.cli.analyze_command。"""
    try:
        from app.adapters.cli import analyze_command
    except ModuleNotFoundError as exc:
        if not (exc.name or "").startswith("app"):
            raise
        from src.app.adapters.cli import analyze_command

    # 显式传入当前模块，避免用例重复 import 分析模块。
    analyze_command.main(
        argv,
        analyzer_module=sys.modules[__name__],
        analyze_recording_cls=AnalyzeRecording,
    )


if __name__ == "__main__":
    main()
