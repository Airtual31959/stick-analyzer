from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.adapters.prompt.ai_prompt_builder import (
    EMPTY_REPORT_PLACEHOLDER,
    REFERENCE_CURVE_MARKER,
    build_ai_prompt,
    inject_reference_curves,
)


def test_build_ai_prompt_uses_placeholder_for_empty_report():
    prompt = build_ai_prompt("")

    assert EMPTY_REPORT_PLACEHOLDER in prompt
    assert "{REPORT_CONTENT}" not in prompt


def test_build_ai_prompt_inserts_report_content():
    report = "自定义分析报告"

    prompt = build_ai_prompt(report)

    assert report in prompt
    assert EMPTY_REPORT_PLACEHOLDER not in prompt
    assert "{REPORT_CONTENT}" not in prompt


def test_inject_reference_curves_appends_section_when_missing():
    prompt = "原始提示词"

    updated = inject_reference_curves(prompt, "参考曲线 A")

    assert updated.startswith(prompt)
    assert REFERENCE_CURVE_MARKER in updated
    assert "参考曲线 A" in updated
    assert updated.endswith("参考曲线 A\n")


def test_inject_reference_curves_replaces_existing_section_before_next_heading():
    prompt = (
        "原始提示词\n\n"
        "==================================================\n"
        "【我收集的参考曲线】\n"
        "==================================================\n"
        "旧参考曲线\n"
        "\n## 后续章节\n"
        "保留内容"
    )

    updated = inject_reference_curves(prompt, "新参考曲线")

    assert "旧参考曲线" not in updated
    assert "新参考曲线" in updated
    assert updated.count(REFERENCE_CURVE_MARKER) == 1
    assert "\n## 后续章节\n保留内容" in updated


def test_inject_reference_curves_replaces_existing_section_at_end():
    prompt = (
        "原始提示词\n\n"
        "==================================================\n"
        "【我收集的参考曲线】\n"
        "==================================================\n"
        "旧参考曲线\n"
    )

    updated = inject_reference_curves(prompt, "新参考曲线")

    assert "旧参考曲线" not in updated
    assert updated.endswith("新参考曲线\n")
    assert updated.count(REFERENCE_CURVE_MARKER) == 1
