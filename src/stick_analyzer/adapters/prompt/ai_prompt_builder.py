from __future__ import annotations

from .ai_prompt_template import AI_PROMPT_TEMPLATE

EMPTY_REPORT_PLACEHOLDER = "【请先在 ② 分析数据 标签页完成一次分析，再回来这里】"
REFERENCE_CURVE_MARKER = "【我收集的参考曲线】"
REFERENCE_CURVE_SEPARATOR = "=" * 50


def build_ai_prompt(report_content: str | None) -> str:
    """根据分析报告生成完整 AI 提示词。"""
    report = report_content or EMPTY_REPORT_PLACEHOLDER
    return AI_PROMPT_TEMPLATE.replace("{REPORT_CONTENT}", report)


def build_reference_curve_section(reference_text: str) -> str:
    """生成与旧 GUI 完全一致的参考曲线注入区块。"""
    return (
        "\n\n" + REFERENCE_CURVE_SEPARATOR + "\n"
        f"{REFERENCE_CURVE_MARKER}\n"
        + REFERENCE_CURVE_SEPARATOR + "\n"
        + reference_text + "\n"
    )


def inject_reference_curves(prompt_text: str, reference_text: str) -> str:
    """将参考曲线注入提示词，重复注入时替换旧区块。"""
    injection = build_reference_curve_section(reference_text)

    if REFERENCE_CURVE_MARKER not in prompt_text:
        return prompt_text + injection

    start = prompt_text.find(
        REFERENCE_CURVE_SEPARATOR + "\n" + REFERENCE_CURVE_MARKER
    )
    if start == -1:
        start = prompt_text.find(REFERENCE_CURVE_MARKER)

    end = prompt_text.find("\n## ", start)
    if end == -1:
        end = prompt_text.find("\n请", start)

    if end == -1:
        return prompt_text[:start].rstrip() + injection
    return prompt_text[:start].rstrip() + injection + prompt_text[end:]
