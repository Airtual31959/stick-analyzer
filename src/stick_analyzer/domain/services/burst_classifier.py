from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from ..constants import CLASSIFICATION_EXPLANATIONS


class BurstClassifier:
    """根据爆发指标分类射击行为。"""

    def classify_burst(self, metrics: Mapping[str, Any] | None) -> str:
        if metrics is None:
            return "数据不足"
        pre = metrics["pre_stability"]
        dur = metrics["during_stability"]
        rev = metrics["total_reversals"]
        avg_mag = metrics.get("avg_magnitude", 0.0)

        if not np.isnan(pre) and pre > 0.10:
            return "开火前抖动 ⚠"
        if not np.isnan(dur) and dur > 0.08:
            return "开火中抖动 ⚠"
        if rev > 25:
            return "频繁过冲 ⚠"

        if avg_mag < 0.10:
            return "微调跟枪"

        if not np.isnan(pre):
            if pre < 0.025 and rev < 5:
                return "完美稳定 ⭐"
            if pre < 0.04 and rev < 10:
                return "稳定射击 ✓"
            if pre < 0.06 and rev < 15:
                return "接近稳定"

        return "中等稳定"


_DEFAULT_CLASSIFIER = BurstClassifier()


def classify_burst(metrics: Mapping[str, Any] | None) -> str:
    return _DEFAULT_CLASSIFIER.classify_burst(metrics)

