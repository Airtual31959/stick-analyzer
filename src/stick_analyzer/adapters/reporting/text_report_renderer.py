from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ...domain.constants import CLASSIFICATION_EXPLANATIONS
from ...domain.services.burst_classifier import classify_burst
from ...domain.services.threshold_policy import get_stability_thresholds
from ...domain.services.weapon_policy import rpm_to_during_window_ms


class TextReportRenderer:
    def generate_report(
        self,
        events: Sequence[Mapping[str, Any]],
        csv_path: Path,
        metadata: Mapping[str, Any],
        thresholds: Mapping[str, Any],
    ) -> str:
        """生成文字报告。"""
        metrics_list = [e["metrics"] for e in events if e["metrics"] is not None]
        if not metrics_list:
            return "[!] 没有可分析的事件"

        n = len(metrics_list)
        pre_stabs = [m["pre_stability"] for m in metrics_list
                     if not np.isnan(m["pre_stability"])]
        dur_stabs = [m["during_stability"] for m in metrics_list
                     if not np.isnan(m["during_stability"])]
        revs = [m["total_reversals"] for m in metrics_list]
        mags = [m["avg_magnitude"] for m in metrics_list]
        durations = [m["duration"] for m in metrics_list]
        ads_count = sum(1 for m in metrics_list if m["is_ads"])
        moving_count = sum(1 for m in metrics_list if m["is_moving"])

        classifications = [classify_burst(m) for m in metrics_list]
        class_count = {}
        for c in classifications:
            class_count[c] = class_count.get(c, 0) + 1

        all_dom = [(m["dominant_input_low"] + m["dominant_input_high"]) / 2
                   for m in metrics_list]
        common_low = float(np.percentile(all_dom, 25))
        common_high = float(np.percentile(all_dom, 75))

        L = []
        L.append("=" * 70)
        L.append("           摇杆射击行为分析报告")
        L.append("=" * 70)
        L.append(f"源文件: {csv_path.name}")

        # 元数据展示
        if metadata:
            L.append("")
            L.append("配置元数据:")
            if "curve" in metadata:
                L.append(f"  曲线版本: {metadata['curve']}")
            if "rc_hipfire" in metadata:
                hip_int = metadata.get("rc_hipfire_intensity", "")
                int_str = f"（{hip_int}）" if hip_int and hip_int != "unknown" else ""
                L.append(f"  腰射 RC: {metadata['rc_hipfire']}{int_str}")
            if "rc_ads" in metadata:
                ads_int = metadata.get("rc_ads_intensity", "")
                int_str = f"（{ads_int}）" if ads_int and ads_int != "unknown" else ""
                L.append(f"  开镜 RC: {metadata['rc_ads']}{int_str}")
            if "weapons" in metadata:
                L.append(f"  使用武器: {metadata['weapons']}")
            if "scene" in metadata:
                L.append(f"  场景: {metadata['scene']}")

            # 显示阈值调整说明
            intensity_label = thresholds.get("intensity_label", "")
            if intensity_label and intensity_label not in ("无 RC / 中性", "无 RC 功能"):
                base = 0.04
                adjusted = thresholds["pre_stable"]
                pct = (adjusted / base - 1) * 100
                L.append(f"  [注] RC 强度: {intensity_label}，"
                         f"稳定度阈值已自动调整 {pct:+.0f}%")

            # [T1.3] 传感器类型说明
            sensor_label = thresholds.get("sensor_label", "")
            sensor_factor = thresholds.get("sensor_factor", 1.0)
            if sensor_label:
                if sensor_factor != 1.0:
                    pct = (sensor_factor - 1.0) * 100
                    L.append(f"  [注] 摇杆传感器: {sensor_label}，"
                             f"阈值额外放宽 {pct:+.0f}%（中心钝化补偿）")
                else:
                    L.append(f"  摇杆传感器: {sensor_label}")

            # [T0.2] 采样率诊断
            if "effective_rate" in metadata:
                try:
                    eff = float(metadata["effective_rate"])
                    nom = float(metadata.get("nominal_rate", "0") or 0)
                    dup = float(metadata.get("duplicate_ratio", "0") or 0)
                    rate_line = (f"  采样率: 标称 {nom:.0f} Hz，"
                                 f"实际有效 {eff:.0f} Hz "
                                 f"（重复帧 {dup*100:.1f}%）")
                    L.append(rate_line)

                    # 对比用户填的回报率
                    try:
                        polling = float(metadata.get("polling_rate", "0") or 0)
                    except (ValueError, TypeError):
                        polling = 0
                    if polling > 0:
                        L.append(f"  手柄回报率（用户填写）: {polling:.0f} Hz")

                    # 软件采样上限由 pygame/SDL 协议决定（通常 500-1000Hz），
                    # 与手柄回报率无关 —— 即使手柄是 1000/4000/8000Hz，
                    # 软件这层也只能拿到 SDL 协议范围内的数据。
                    # 这对压枪分析（关注 5-50Hz 频段）完全够用。
                    if eff >= 400:
                        L.append("  [说明] 软件采样上限由 pygame/SDL 协议决定（~500-1000Hz）。"
                                 "对压枪分析够用，")
                        L.append("         不必担心手柄回报率高（1000-8000Hz）"
                                 "的差异 —— SDL 这层无法区分。")
                    elif eff >= 200:
                        L.append("  [提示] 实际采样率一般。SDL 协议正常上限是 500-1000Hz，")
                        L.append("         你这次只到 {:.0f}Hz，可能是后台占用了"
                                 "CPU 或蓝牙连接不稳。".format(eff))
                        L.append("         分析结果基本可信，但建议下次有线连接重测。")
                    else:
                        L.append("  [警告] 实际有效采样率过低（<200Hz），"
                                 "稳定度数值可能偏乐观。")
                        L.append("         可能是蓝牙断连、CPU 占用过高、"
                                 "或第三方驱动限频。")
                        L.append("         建议改用有线 USB 直连 + 关闭其他占用程序后重测。")
                except (ValueError, TypeError):
                    pass

            # [T0.3] 硬件本底校准说明
            try:
                nfx = float(metadata.get("noise_floor_x", "0") or 0)
                nfy = float(metadata.get("noise_floor_y", "0") or 0)
            except (ValueError, TypeError):
                nfx = nfy = 0.0
            if nfx > 0 or nfy > 0:
                L.append(f"  传感器本底（已扣除）: X={nfx:.5f}  Y={nfy:.5f}")
                if max(nfx, nfy) > 0.015:
                    L.append("  [提示] 本底偏高，可能是回中虚位较大、摇杆有"
                             "漂移迹象，或周围磁场干扰（霍尔摇杆较常见）。")

            # [T2.3] 武器射速识别
            weapon_rpm = 0
            if metrics_list:
                weapon_rpm = metrics_list[0].get("weapon_rpm", 0)
            if weapon_rpm > 0:
                window_ms = rpm_to_during_window_ms(weapon_rpm)
                if window_ms <= 0:
                    L.append(f"  武器射速: {weapon_rpm} RPM "
                             f"（单发/拉栓武器 → 已跳过开火中稳定度分析）")
                else:
                    L.append(f"  武器射速: {weapon_rpm} RPM "
                             f"（开火中分析窗口已自动设为 {window_ms}ms）")

            L.append("")

        L.append(f"分析事件总数: {n}")
        L.append(f"  - 开镜射击: {ads_count} ({100*ads_count/n:.1f}%)")
        L.append(f"  - 腰射射击: {n - ads_count} ({100*(n-ads_count)/n:.1f}%)")
        L.append(f"  - 走位射击: {moving_count} ({100*moving_count/n:.1f}%)")
        L.append(f"开火持续: 平均 {np.mean(durations):.2f}s，"
                 f"中位 {np.median(durations):.2f}s")
        L.append("")

        L.append("-" * 70)
        L.append(" 一、开火前稳定度（瞄准是否稳停在敌人身上）")
        L.append("-" * 70)
        if pre_stabs:
            L.append(f"  平均: {np.mean(pre_stabs):.4f}  中位: {np.median(pre_stabs):.4f}")
            L.append(f"  最差: {np.max(pre_stabs):.4f}  最好: {np.min(pre_stabs):.4f}")
            L.append(f"  评级（已根据RC调整）: <{thresholds['pre_stable']:.3f}=稳，"
                     f"{thresholds['pre_stable']:.3f}-{thresholds['pre_unstable']:.3f}=一般，"
                     f">{thresholds['pre_unstable']:.3f}=抖")
        L.append("")

        L.append("-" * 70)
        L.append(" 二、开火中稳定度（压枪是否稳）")
        L.append("-" * 70)
        if dur_stabs:
            L.append(f"  平均: {np.mean(dur_stabs):.4f}  中位: {np.median(dur_stabs):.4f}")
            L.append(f"  最差: {np.max(dur_stabs):.4f}  最好: {np.min(dur_stabs):.4f}")
            L.append(f"  评级（已根据RC调整）: <{thresholds['during_stable']:.3f}=稳，"
                     f"{thresholds['during_stable']:.3f}-{thresholds['during_unstable']:.3f}=一般，"
                     f">{thresholds['during_unstable']:.3f}=抖")
        L.append("")

        L.append("-" * 70)
        L.append(" 三、过冲/反转统计")
        L.append("-" * 70)
        L.append(f"  平均反转次数: {np.mean(revs):.1f} 次/事件")
        L.append(f"  中位数: {np.median(revs):.0f} 次/事件")
        L.append(f"  最高: {np.max(revs):.0f} 次")
        L.append(f"  评级: <10=好，10-25=一般，>25=过冲严重")

        # [T3.3] 反转细分类型：大幅过冲（甩过头）vs 小抖动（手抖/曲线噪声）
        large_list = [m.get("large_overshoots", 0) for m in metrics_list]
        small_list = [m.get("small_jitters", 0) for m in metrics_list]
        max_amp_list = [m.get("max_reversal_amplitude", 0.0) for m in metrics_list]
        avg_large = float(np.mean(large_list)) if large_list else 0.0
        avg_small = float(np.mean(small_list)) if small_list else 0.0
        max_amp = float(np.max(max_amp_list)) if max_amp_list else 0.0

        L.append("")
        L.append(f"  细分类型（反转幅度分布）:")
        L.append(f"    大幅过冲（>0.15，甩过头）: 平均 {avg_large:.1f} 次/事件")
        L.append(f"    小抖动（0.05-0.15，微修正）: 平均 {avg_small:.1f} 次/事件")
        L.append(f"    单次最大反转幅度: {max_amp:.3f}")

        # 类型识别 + 倾向性提示
        total_classified = avg_large + avg_small
        if total_classified > 0.5:  # 至少有一些反转才下结论
            large_ratio = avg_large / total_classified
            if large_ratio > 0.50:
                L.append(f"    → 主要是大幅过冲（{large_ratio*100:.0f}%）：")
                L.append(f"      高段曲线斜率过高，准星甩过目标后回拉修正")
            elif large_ratio < 0.20:
                L.append(f"    → 主要是小抖动（{(1-large_ratio)*100:.0f}%）：")
                L.append(f"      可能原因: 低段曲线斜率过陡 / 硬件本底偏高 / 手部微抖")
                L.append(f"      / 高强度 RC 增抖（RC 越强摇杆越钝、内置噪声越大）")
                L.append("      （和『开火前抖动』成因接近，看二者是否同时高）")
            else:
                L.append(f"    → 大幅过冲与小抖动并存，需同时检查曲线高低段")
        L.append("")

        L.append("-" * 70)
        L.append(" 四、行为分类")
        L.append("-" * 70)
        for cls, cnt in sorted(class_count.items(), key=lambda x: -x[1]):
            pct = 100 * cnt / n
            bar = "█" * int(pct / 2)
            L.append(f"  {cls:18} | {cnt:4} 次 ({pct:5.1f}%) {bar}")

        # [T3.4] 列出本次出现的分类的玩家直觉解释（按从好到差顺序）
        seen_classes = set(class_count.keys())
        L.append("")
        L.append("  分类说明（玩家直觉对照）:")
        for cls, exp in CLASSIFICATION_EXPLANATIONS.items():
            if cls in seen_classes:
                L.append(f"    {cls:14} = {exp}")
        L.append("")

        L.append("-" * 70)
        L.append(" 五、关键发现：你的主导推杆区间")
        L.append("-" * 70)
        L.append(f"  你开火时最常用的推杆量: X={common_low:.0f}–{common_high:.0f}")
        L.append("  → 曲线这段的设计对你影响最大")

        # [T1.4] 霍尔玩家若主导区间在中心钝化区，自动给反死区补偿建议
        # （TMR 已接近碳膜响应，不再需要这条建议）
        sensor = metadata.get("sensor_type", "unknown").strip().lower()
        if sensor == "hall" and common_low < 10:
            L.append("")
            L.append(f"  [⚠ 重要] 你是霍尔摇杆且主导推杆区间在 X<10 中心钝化区。")
            L.append(f"        霍尔摇杆中心响应钝（圆周率差、斜角信号缺失），")
            L.append(f"        建议曲线第一个非零点设在 X=4, Y=20 附近做反死区补偿。")
            L.append(f"        这是 TheFinals 玩家社区在 ALC 拟合实验中验证的经验值。")

        L.append("")

        L.append("-" * 70)
        L.append(" 六、自动化调参建议")
        L.append("-" * 70)

        avg_pre = np.mean(pre_stabs) if pre_stabs else 0
        avg_dur = np.mean(dur_stabs) if dur_stabs else 0
        avg_rev = np.mean(revs)

        issues = []
        if avg_pre > thresholds["pre_unstable"]:
            issues.append("瞄准抖动")
            L.append(f"  [警] 开火前抖动严重（{avg_pre:.4f} > {thresholds['pre_unstable']:.3f}）：")
            L.append(f"     瞄准时准星无法稳定停在敌人身上")
            L.append(f"     原因: X={common_low:.0f}–{common_high:.0f} 段曲线斜率过高")
            L.append(f"     → 把这段对应节点的 Y 值降低 1.5-2.5 单位")
        elif avg_pre > thresholds["pre_stable"] * 1.5:
            L.append(f"  [提示] 瞄准稳定度中等（{avg_pre:.4f}）")
            L.append(f"     → X={common_low:.0f}–{common_high:.0f} 段 Y 值降低 0.5-1 单位")
        elif pre_stabs:
            L.append(f"  [√] 瞄准稳定度良好（{avg_pre:.4f} < {thresholds['pre_stable']:.3f}）")
        L.append("")

        if avg_dur > thresholds["during_unstable"]:
            issues.append("压枪抖动")
            L.append(f"  [警] 开火中压枪抖动（{avg_dur:.4f} > {thresholds['during_unstable']:.3f}）：")
            L.append(f"     压枪过程不稳，子弹散布严重")
            L.append(f"     原因: 压枪时落在的推杆区间斜率过高")
            L.append(f"     → 检查 ADS 曲线 X={common_low:.0f}–{common_high:.0f} 段是否过陡")
        elif avg_dur > thresholds["during_stable"] * 1.5:
            L.append(f"  [提示] 压枪稳定度中等（{avg_dur:.4f}）")
        elif dur_stabs:
            L.append(f"  [√] 压枪稳定度良好（{avg_dur:.4f}）")
        L.append("")

        # [T3.3] 过冲建议根据细分类型给针对性方案
        _total_cl = avg_large + avg_small
        _large_ratio = (avg_large / _total_cl) if _total_cl > 0.5 else 0.5

        if avg_rev > thresholds["rev_bad"]:
            issues.append("过冲")
            L.append(f"  [警] 过冲严重（{avg_rev:.1f} 次/事件）：")
            if _large_ratio > 0.50:
                # 主要是大幅过冲 → 高段斜率问题（跟 RC 无关，RC 反而是钝化）
                L.append(f"     类型: 大幅过冲为主"
                         f"（{avg_large:.1f}/事件 > 0.15 幅度）")
                L.append(f"     原因: 高段曲线斜率过高，准星甩过目标后回拉")
                L.append(f"     → 降低高段（X=70-100）输出，"
                         f"节点 6、7 的 Y 值降低 1.5-2 单位")
                L.append(f"     注: 大幅过冲跟 RC 无关 —— RC 增抖是钝化操作，"
                         f"不会让你甩过头")
            elif _large_ratio < 0.20:
                # 主要是小抖动 → 低段过激 / 本底 / RC 噪声
                L.append(f"     类型: 高频小抖动为主"
                         f"（{avg_small:.1f}/事件 在 0.05-0.15 幅度）")
                L.append(f"     可能原因: 低段曲线斜率过陡 / 硬件本底偏高 / "
                         f"高强度 RC 增抖")
                L.append(f"     → 降低低段（X=10-30）输出，"
                         f"节点 1、2 的 Y 值降低 1-1.5 单位")
                L.append(f"     → 也检查死区是否设过小（中心钝化区噪声会被放大），"
                         f"以及当前 RC 强度是否过高")
            else:
                # 混合
                L.append(f"     类型: 大幅过冲（{avg_large:.1f}/事件）"
                         f"+ 小抖动（{avg_small:.1f}/事件）并存")
                L.append(f"     → 同时降低低段（X=10-30）1 单位"
                         f"和高段（X=70-100）1.5 单位")
        elif avg_rev > 12:
            L.append(f"  [提示] 有一定过冲（{avg_rev:.1f} 次/事件）")
            if _large_ratio > 0.50:
                L.append(f"     倾向大幅过冲（{avg_large:.1f}/事件）"
                         f"→ 适度降低高段斜率")
            elif _large_ratio < 0.20:
                L.append(f"     倾向小抖动（{avg_small:.1f}/事件）"
                         f"→ 适度降低低段斜率")
            else:
                L.append(f"     可适度降低中段斜率")
        else:
            L.append(f"  [√] 过冲控制良好（{avg_rev:.1f} 次/事件）")
        L.append("")

        # （腰射 vs 开镜 详细不对称分析见 第七节）
        # （走位 vs 站桩 详细对比见 第八节）

        if not issues:
            L.append("  [总结] 所有指标良好，曲线匹配度很高")
        else:
            L.append(f"  [总结] 主要问题: {', '.join(issues)}")
        L.append("")

        # ===== [T3.1] 腰射 vs 开镜 模式不对称分析 =====
        # 给两种模式各算一套独立等级，差异 > 30% 时给针对性曲线建议
        if ads_count > 0 and ads_count < n:
            L.append("-" * 70)
            L.append(" 七、腰射 vs 开镜 模式不对称分析")
            L.append("-" * 70)

            ads_only = [m for m in metrics_list if m["is_ads"]]
            hip_only = [m for m in metrics_list if not m["is_ads"]]

            def _safe_avg(metrics, key):
                vals = [m[key] for m in metrics
                        if m.get(key) is not None
                        and not (isinstance(m.get(key), float) and np.isnan(m[key]))]
                return float(np.mean(vals)) if vals else float("nan")

            hip_pre_v = _safe_avg(hip_only, "pre_stability")
            hip_dur_v = _safe_avg(hip_only, "during_stability")
            hip_rev_v = _safe_avg(hip_only, "total_reversals")
            hip_dlow = _safe_avg(hip_only, "dominant_input_low")
            hip_dhigh = _safe_avg(hip_only, "dominant_input_high")

            ads_pre_v = _safe_avg(ads_only, "pre_stability")
            ads_dur_v = _safe_avg(ads_only, "during_stability")
            ads_rev_v = _safe_avg(ads_only, "total_reversals")
            ads_dlow = _safe_avg(ads_only, "dominant_input_low")
            ads_dhigh = _safe_avg(ads_only, "dominant_input_high")

            # 各自模式专属阈值（腰射用 rc_hipfire_intensity，开镜复用主阈值）
            hip_md = dict(metadata)
            hip_intensity = (metadata.get("rc_hipfire_intensity", "")
                             or "").strip()
            if hip_intensity:
                hip_md["rc_ads_intensity"] = hip_intensity
                hip_md.pop("rc_ads", None)  # 防止老格式数值字段冲突
            hip_th = get_stability_thresholds(hip_md)
            ads_th = thresholds  # 主阈值已基于 rc_ads_intensity

            def _grade_stab(val, t_stable, t_unstable):
                if np.isnan(val):
                    return "—"
                if val <= t_stable:
                    return "稳"
                if val <= t_unstable:
                    return "一般"
                return "抖"

            def _grade_rev(val, good, bad):
                if np.isnan(val):
                    return "—"
                if val <= good:
                    return "好"
                if val <= bad:
                    return "一般"
                return "过冲"

            def _diff_pct(a, b):
                """a 相对 b 的差异百分比；正数 = a 更差（指标本身越大越差）"""
                if np.isnan(a) or np.isnan(b) or b <= 0:
                    return float("nan"), "—"
                d = (a - b) / b * 100
                return d, f"{d:+.0f}%"

            n_hip = len(hip_only)
            n_ads = len(ads_only)
            L.append(f"  样本量: 腰射 N={n_hip}, 开镜 N={n_ads}")
            if min(n_hip, n_ads) < 3:
                L.append("  [提示] 单边样本量较少（<3），不对称结论仅供参考")

            # RC 强度对比（仅当腰射/开镜分别填写时显示）
            hip_label = hip_th.get("intensity_label", "")
            ads_label = ads_th.get("intensity_label", "")
            if hip_label and ads_label and hip_label != ads_label:
                L.append(f"  RC 强度: 腰射={hip_label}，开镜={ads_label}"
                         f"（已分别校准阈值）")

            L.append("")
            L.append("  指标         | 腰射             | 开镜             | 差异")
            L.append("  " + "-" * 64)

            pre_d, pre_s = _diff_pct(ads_pre_v, hip_pre_v)
            dur_d, dur_s = _diff_pct(ads_dur_v, hip_dur_v)
            rev_d, rev_s = _diff_pct(ads_rev_v, hip_rev_v)

            if not (np.isnan(hip_pre_v) and np.isnan(ads_pre_v)):
                hg = _grade_stab(hip_pre_v, hip_th["pre_stable"],
                                 hip_th["pre_unstable"])
                ag = _grade_stab(ads_pre_v, ads_th["pre_stable"],
                                 ads_th["pre_unstable"])
                hp = "—" if np.isnan(hip_pre_v) else f"{hip_pre_v:.4f}"
                ap = "—" if np.isnan(ads_pre_v) else f"{ads_pre_v:.4f}"
                L.append(f"  开火前稳定度 | {hp:<8} ({hg:<2})  | "
                         f"{ap:<8} ({ag:<2})  | {pre_s}")
            if not (np.isnan(hip_dur_v) and np.isnan(ads_dur_v)):
                hg = _grade_stab(hip_dur_v, hip_th["during_stable"],
                                 hip_th["during_unstable"])
                ag = _grade_stab(ads_dur_v, ads_th["during_stable"],
                                 ads_th["during_unstable"])
                hd = "—" if np.isnan(hip_dur_v) else f"{hip_dur_v:.4f}"
                ad_ = "—" if np.isnan(ads_dur_v) else f"{ads_dur_v:.4f}"
                L.append(f"  开火中稳定度 | {hd:<8} ({hg:<2})  | "
                         f"{ad_:<8} ({ag:<2})  | {dur_s}")
            if not (np.isnan(hip_rev_v) and np.isnan(ads_rev_v)):
                hg = _grade_rev(hip_rev_v, hip_th["rev_good"], hip_th["rev_bad"])
                ag = _grade_rev(ads_rev_v, ads_th["rev_good"], ads_th["rev_bad"])
                hr = "—" if np.isnan(hip_rev_v) else f"{hip_rev_v:5.1f}"
                ar = "—" if np.isnan(ads_rev_v) else f"{ads_rev_v:5.1f}"
                L.append(f"  反转次数     | {hr:<8} ({hg:<4}) | "
                         f"{ar:<8} ({ag:<4}) | {rev_s}")
            if not (np.isnan(hip_dlow) or np.isnan(ads_dlow)):
                L.append(f"  主导推杆区间 | X={hip_dlow:>4.0f}-{hip_dhigh:<4.0f}"
                         f"        | X={ads_dlow:>4.0f}-{ads_dhigh:<4.0f}"
                         f"        | —")

            # 不对称结论 + 针对性建议
            L.append("")
            ASYMMETRY_THRESHOLD = 30.0  # 差异百分比阈值（%）
            asymmetries = []
            if not np.isnan(pre_d) and abs(pre_d) > ASYMMETRY_THRESHOLD:
                asymmetries.append(("pre", pre_d))
            if not np.isnan(dur_d) and abs(dur_d) > ASYMMETRY_THRESHOLD:
                asymmetries.append(("dur", dur_d))
            if not np.isnan(rev_d) and abs(rev_d) > ASYMMETRY_THRESHOLD:
                asymmetries.append(("rev", rev_d))

            if not asymmetries:
                L.append("  [√] 两种模式表现对称（差异均 < 30%），")
                L.append("      腰射/开镜曲线匹配度良好，无明显不对称问题。")
            else:
                L.append("  [⚠ 不对称问题]")
                for kind, d in asymmetries:
                    if kind == "pre":
                        if d > 0:
                            L.append(f"  • 开镜瞄准抖动比腰射高 {d:+.0f}%")
                            L.append("    → ADS 曲线低段过激: 开镜后小幅修正被放大成抖动")
                            ads_low = ads_dlow if not np.isnan(ads_dlow) else 20
                            ads_high = ads_dhigh if not np.isnan(ads_dhigh) else 40
                            L.append(f"    → 建议: ADS 曲线 X={ads_low:.0f}-"
                                     f"{ads_high:.0f} 段对应节点 Y 值降低 1.5-2 单位")
                        else:
                            L.append(f"  • 腰射瞄准抖动比开镜高 {-d:.0f}%")
                            L.append("    → 腰射曲线低段微控不足: 慢推不响应导致猛推追枪")
                            hip_low = hip_dlow if not np.isnan(hip_dlow) else 10
                            hip_high = hip_dhigh if not np.isnan(hip_dhigh) else 30
                            L.append(f"    → 建议: 腰射曲线 X={hip_low:.0f}-"
                                     f"{hip_high:.0f} 段提升斜率（Y 升高 1-1.5 单位）")
                            L.append("           或检查死区是否设过大")
                    elif kind == "dur":
                        if d > 0:
                            L.append(f"  • 开镜压枪抖动比腰射高 {d:+.0f}%")
                            L.append("    → ADS 曲线中段（压枪所在区间）斜率过高")
                            L.append("    → 建议: ADS 曲线 X=40-70 段 Y 值降低 1-2 单位")
                        else:
                            L.append(f"  • 腰射压枪抖动比开镜高 {-d:.0f}%")
                            L.append("    → 腰射模式抖动反常，可能是腰射曲线高段")
                            L.append("      过陡或腰射 RC 强度设置过激")
                    elif kind == "rev":
                        if d > 0:
                            L.append(f"  • 开镜过冲比腰射高 {d:+.0f}%")
                            L.append("    → 开镜下准星反复修正、越过目标后回拉")
                            L.append("    → 建议: ADS 曲线中段（X=40-70）适度降低斜率")
                        else:
                            L.append(f"  • 腰射过冲比开镜高 {-d:.0f}%")
                            L.append("    → 腰射跟枪甩过头，可能是腰射高段灵敏度过高")

            L.append("")

        # ===== [T3.2] 走位 vs 站桩 模式对比 =====
        # 走位时左右手协调难度增加，pre/during 阈值放宽 1.3x 给走位组，
        # 避免把『走位本身的劣化』误判成曲线问题
        if moving_count > 0:
            L.append("-" * 70)
            L.append(" 八、走位 vs 站桩 模式对比")
            L.append("-" * 70)

            move_only = [m for m in metrics_list if m.get("is_moving")]
            stat_only = [m for m in metrics_list if not m.get("is_moving")]
            n_move = len(move_only)
            n_stat = len(stat_only)

            def _t32_avg(metrics, key):
                vals = [m[key] for m in metrics
                        if m.get(key) is not None
                        and not (isinstance(m.get(key), float)
                                 and np.isnan(m[key]))]
                return float(np.mean(vals)) if vals else float("nan")

            move_pre = _t32_avg(move_only, "pre_stability")
            move_dur = _t32_avg(move_only, "during_stability")
            move_rev = _t32_avg(move_only, "total_reversals")
            stat_pre = _t32_avg(stat_only, "pre_stability")
            stat_dur = _t32_avg(stat_only, "during_stability")
            stat_rev = _t32_avg(stat_only, "total_reversals")

            # 走位放宽阈值
            MOVE_RELAX = 1.3
            m_th_pre_s = thresholds["pre_stable"] * MOVE_RELAX
            m_th_pre_u = thresholds["pre_unstable"] * MOVE_RELAX
            m_th_dur_s = thresholds["during_stable"] * MOVE_RELAX
            m_th_dur_u = thresholds["during_unstable"] * MOVE_RELAX

            def _t32_grade(val, t_s, t_u):
                if np.isnan(val):
                    return "—"
                if val <= t_s:
                    return "稳"
                if val <= t_u:
                    return "一般"
                return "抖"

            def _t32_diff(a, b, min_baseline=0.005):
                """返回 (相对差异%, 显示字符串, 是否可信)。
                基线 < min_baseline 时百分比失真（除以接近零），
                改输出绝对差 + 不可信标记。
                """
                if np.isnan(a) or np.isnan(b):
                    return float("nan"), "—", False
                if b < min_baseline:
                    abs_d = a - b
                    if abs(abs_d) < 0.01:
                        return float("nan"), "≈ 同(基线过小)", False
                    return float("nan"), f"+{abs_d:.3f}(基线过小)", False
                d = (a - b) / b * 100
                return d, f"{d:+.0f}%", True

            L.append(f"  样本量: 走位 N={n_move}, 站桩 N={n_stat}")
            L.append(f"  评级阈值: 走位组 ×{MOVE_RELAX} 放宽（左右手协调更难），"
                     f"站桩组用标准阈值")
            L.append("")
            L.append("  指标         | 走位 (放宽)      | 站桩 (标准)      | 走位劣化")
            L.append("  " + "-" * 64)

            pre_d, pre_s_str, pre_reliable = _t32_diff(move_pre, stat_pre)
            dur_d, dur_s_str, dur_reliable = _t32_diff(move_dur, stat_dur)

            # 反转次数用绝对差显示（整数差异更直观）
            if np.isnan(move_rev) or np.isnan(stat_rev):
                rev_s_str = "—"
            else:
                rev_s_str = f"{move_rev - stat_rev:+.1f} 次"

            if not (np.isnan(move_pre) and np.isnan(stat_pre)):
                mg = _t32_grade(move_pre, m_th_pre_s, m_th_pre_u)
                sg = _t32_grade(stat_pre, thresholds["pre_stable"],
                                thresholds["pre_unstable"])
                ms = "—" if np.isnan(move_pre) else f"{move_pre:.4f}"
                ss = "—" if np.isnan(stat_pre) else f"{stat_pre:.4f}"
                L.append(f"  开火前稳定度 | {ms:<8} ({mg:<2}) | "
                         f"{ss:<8} ({sg:<2}) | {pre_s_str}")

            if not (np.isnan(move_dur) and np.isnan(stat_dur)):
                mg = _t32_grade(move_dur, m_th_dur_s, m_th_dur_u)
                sg = _t32_grade(stat_dur, thresholds["during_stable"],
                                thresholds["during_unstable"])
                ms = "—" if np.isnan(move_dur) else f"{move_dur:.4f}"
                ss = "—" if np.isnan(stat_dur) else f"{stat_dur:.4f}"
                L.append(f"  开火中稳定度 | {ms:<8} ({mg:<2}) | "
                         f"{ss:<8} ({sg:<2}) | {dur_s_str}")

            if not (np.isnan(move_rev) and np.isnan(stat_rev)):
                ms = "—" if np.isnan(move_rev) else f"{move_rev:5.1f}"
                ss = "—" if np.isnan(stat_rev) else f"{stat_rev:5.1f}"
                L.append(f"  反转次数     | {ms:<8}       | {ss:<8}       "
                         f"| {rev_s_str}")

            L.append("")

            # 结论 + 建议
            if n_stat == 0:
                # 全走位（用户的真实情况，实战常态）
                L.append(f"  [说明] 本次录制全部为走位射击（实战常态，无静止对比）。")
                L.append(f"        走位组放宽阈值: pre<={m_th_pre_s:.3f}=稳，"
                         f"during<={m_th_dur_s:.3f}=稳。")
                L.append(f"        建议下次录一段纯站桩对比，"
                         f"看走位本身贡献了多少劣化。")
            elif n_move == 0:
                # 全站桩 — 不会进入这个分支（moving_count > 0 已保证）
                pass
            else:
                # 双边都有，给针对性结论
                ASYMM_THRESHOLD = 30.0
                findings = []
                # 不可信差异（基线过小）不算劣化
                if pre_reliable and pre_d > ASYMM_THRESHOLD:
                    findings.append(("pre", pre_d))
                if dur_reliable and dur_d > ASYMM_THRESHOLD:
                    findings.append(("dur", dur_d))

                # 基线过小时单独提示（站桩样本里右摇杆几乎没动）
                baseline_too_small = (not pre_reliable and not dur_reliable
                                      and not np.isnan(move_pre)
                                      and not np.isnan(stat_pre))

                if baseline_too_small:
                    L.append(f"  [说明] 站桩组基线偏低"
                             f"（pre={stat_pre:.4f}, dur={stat_dur:.4f}）：")
                    L.append(f"        站桩时右摇杆几乎没动，无法形成可信对照。")
                    L.append(f"        建议下次站桩时也做些瞄准微调，"
                             f"让数据有可比性。")
                elif not findings:
                    if pre_reliable and pre_d < -10:
                        L.append(f"  [！] 走位反而比站桩稳（{pre_d:+.0f}%），")
                        L.append(f"      可能是站桩样本少/偶然，参考价值有限")
                    else:
                        L.append(f"  [√] 走位与站桩表现接近"
                                 f"（pre 差异 {pre_s_str}），")
                        L.append(f"      左右摇杆曲线协调良好")
                else:
                    L.append("  [⚠ 走位明显劣化]")
                    for kind, d in findings:
                        if kind == "pre":
                            if d > 50:
                                L.append(f"  • 走位瞄准抖动比站桩高 +{d:.0f}%（严重）")
                                L.append("    → 左摇杆推动时干扰右摇杆，"
                                         "怀疑是左右摇杆曲线不协调")
                                L.append("    → 检查左摇杆死区是否设过小（导致")
                                L.append("      走位时无意带动右摇杆产生噪声）")
                                L.append("    → 或检查手柄是否有摇杆交叉串扰"
                                         "（硬件问题）")
                            else:
                                L.append(f"  • 走位瞄准抖动比站桩高 +{d:.0f}%")
                                L.append("    → 左右手协调能力不足，"
                                         "练习走位射击的肌肉记忆")
                                L.append("    → 或检查左摇杆死区设置")
                        elif kind == "dur":
                            L.append(f"  • 走位压枪抖动比站桩高 +{d:.0f}%")
                            L.append("    → 走位时压枪手感不稳，"
                                     "可能是左摇杆持续输入分散了精力")
                            L.append("    → 实战中先练『站桩压枪稳』，"
                                     "再叠加『走位』")

            L.append("")

        # ===== [T2.2] 状态一致性（"心流代理"指标）=====
        # 算所有事件的 pre/dur 稳定度变异系数 CV = std/mean
        # CV 越小 = 表现越稳定（每次都差不多）；CV 越大 = 表现飘
        if len(pre_stabs) >= 4 or len(dur_stabs) >= 4:
            L.append("-" * 70)
            L.append(" 九、今日状态一致性（看你今天发挥稳不稳）")
            L.append("-" * 70)

            def _cv(arr):
                if len(arr) < 2:
                    return None
                mean = float(np.mean(arr))
                if mean <= 0:
                    return None
                return float(np.std(arr) / mean)

            cv_pre = _cv(pre_stabs)
            cv_dur = _cv(dur_stabs)
            if cv_pre is not None:
                L.append(f"  开火前稳定度 CV: {cv_pre:.2f}"
                         f"（每次的瞄准稳定度差异）")
            if cv_dur is not None:
                L.append(f"  开火中稳定度 CV: {cv_dur:.2f}"
                         f"（每次的压枪稳定度差异）")

            # 综合判断
            cv_max = max(filter(lambda x: x is not None, [cv_pre, cv_dur]),
                         default=None)
            if cv_max is not None:
                if cv_max < 0.30:
                    L.append("  → 表现非常一致 ✓ 今天手感稳，"
                             "数据反映的是你的真实水平")
                elif cv_max < 0.60:
                    L.append("  → 表现基本一致，可作为可靠参考")
                else:
                    L.append("  → ⚠ 表现飘，今天状态可能不在线")
                    L.append("    建议：今天数据仅供参考，先休息或简单训练几局再分析；")
                    L.append("    或者过两天再录一次对比，看是状态问题还是曲线问题。")
            L.append("")

        # ===== [T2.1] 玩家自评事件对照 =====
        # 找 mark="good" 的时间点，匹配到最近的 burst，对比"自评好"和"非自评"的算法评分
        marked_events = []
        unmarked_events = []
        if "mark" in metrics_list[0]["data"].columns:
            # 找全数据里所有 mark=good 的时间戳
            import pandas as pd

            all_data = pd.concat([m["data"] for m in metrics_list],
                                 ignore_index=True).drop_duplicates("elapsed_s")
            good_marks_ts = (all_data[all_data["mark"] == "good"]["elapsed_s"]
                             .tolist() if "mark" in all_data.columns else [])

            # 每个 mark 关联到最近的开火事件（在 burst 期间或 burst 后 2 秒内）
            marked_burst_indices = set()
            for ts in good_marks_ts:
                best_idx = None
                best_dist = 2.0  # 最多向前找 2 秒
                for i, m in enumerate(metrics_list):
                    bs = m["burst_start"]
                    be = m["burst_end"]
                    if bs <= ts <= be + 2.0:
                        dist = max(0, ts - be)
                        if dist < best_dist:
                            best_dist = dist
                            best_idx = i
                if best_idx is not None:
                    marked_burst_indices.add(best_idx)

            marked_events = [metrics_list[i] for i in marked_burst_indices]
            unmarked_events = [m for i, m in enumerate(metrics_list)
                               if i not in marked_burst_indices]

        if marked_events:
            L.append("-" * 70)
            L.append(" 十、玩家自评 vs 算法评分对照")
            L.append("-" * 70)
            L.append(f"  你标记了 {len(marked_events)} 次"
                     f"（认为'压得好'）")
            L.append(f"  其余 {len(unmarked_events)} 次未标记")
            L.append("")

            def _safe_mean(arr, key):
                vals = [m[key] for m in arr
                        if not np.isnan(m.get(key, float("nan")))]
                return float(np.mean(vals)) if vals else None

            marked_pre = _safe_mean(marked_events, "pre_stability")
            unmarked_pre = _safe_mean(unmarked_events, "pre_stability")
            marked_dur = _safe_mean(marked_events, "during_stability")
            unmarked_dur = _safe_mean(unmarked_events, "during_stability")

            L.append("  指标         | 你认为压得好  | 其余事件     | 算法是否同意")
            L.append("  " + "-" * 60)
            if marked_pre is not None and unmarked_pre is not None:
                agree = "✓ 同意" if marked_pre < unmarked_pre else "✗ 不同意"
                L.append(f"  开火前稳定度 | {marked_pre:.4f}      "
                         f"| {unmarked_pre:.4f}     | {agree}")
            if marked_dur is not None and unmarked_dur is not None:
                agree = "✓ 同意" if marked_dur < unmarked_dur else "✗ 不同意"
                L.append(f"  开火中稳定度 | {marked_dur:.4f}      "
                         f"| {unmarked_dur:.4f}     | {agree}")

            # 判断算法和直觉的一致性
            agreements = []
            if marked_pre is not None and unmarked_pre is not None:
                agreements.append(marked_pre < unmarked_pre)
            if marked_dur is not None and unmarked_dur is not None:
                agreements.append(marked_dur < unmarked_dur)
            if agreements:
                L.append("")
                if all(agreements):
                    L.append("  → 算法评分和你的直觉完全一致 ✓")
                    L.append("    说明算法的稳定度阈值校准得当，可以放心参考。")
                elif not any(agreements):
                    L.append("  → ⚠ 算法和你的直觉相反")
                    L.append("    可能原因：")
                    L.append("    1) 你的直觉关注的是命中率/速度，而算法看的是稳定度")
                    L.append("    2) 你按标记键时延迟了，标到了下一次事件")
                    L.append("    3) 当前阈值可能不适合你的硬件，建议手动调校")
                else:
                    L.append("  → 算法和你的直觉部分一致，混合判断")
            L.append("")
        elif "mark" in getattr(metrics_list[0].get("data"), "columns", ()):
            # 有 mark 列但用户没按 → 给个温和提示
            L.append("-" * 70)
            L.append(" 十、玩家自评 vs 算法评分对照")
            L.append("-" * 70)
            L.append("  这次录制没有打标记。下次录制时按一下'标记键'就能标记")
            L.append("  '这次压得好'，分析时会和算法评分对照，")
            L.append("  能帮你判断算法的稳定度阈值是否符合你的直觉。")
            L.append("")

        L.append("=" * 70)
        L.append("  详细每次开火波形见 _event_*.png")
        L.append("  统计总览见 _summary.png")
        L.append("=" * 70)

        return "\n".join(L)


_DEFAULT_RENDERER = TextReportRenderer()


def generate_report(
    events: Sequence[Mapping[str, Any]],
    csv_path: Path,
    metadata: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> str:
    return _DEFAULT_RENDERER.generate_report(events, csv_path, metadata, thresholds)
