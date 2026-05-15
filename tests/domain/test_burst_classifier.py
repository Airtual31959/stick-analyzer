from __future__ import annotations

import numpy as np

from app.domain.constants import CLASSIFICATION_EXPLANATIONS
from app.domain.services.burst_classifier import BurstClassifier


def _metrics(**overrides):
    metrics = {
        "pre_stability": 0.02,
        "during_stability": 0.02,
        "total_reversals": 4,
        "avg_magnitude": 0.25,
    }
    metrics.update(overrides)
    return metrics


def test_classify_burst_handles_missing_metrics():
    assert BurstClassifier().classify_burst(None) == "数据不足"


def test_classify_burst_keeps_severe_issue_priority():
    assert BurstClassifier().classify_burst(
        _metrics(pre_stability=0.11, avg_magnitude=0.01)
    ) == "开火前抖动 ⚠"
    assert BurstClassifier().classify_burst(
        _metrics(during_stability=0.09)
    ) == "开火中抖动 ⚠"
    assert BurstClassifier().classify_burst(
        _metrics(total_reversals=26)
    ) == "频繁过冲 ⚠"


def test_classify_burst_keeps_stable_and_micro_tracking_branches():
    classifier = BurstClassifier()

    assert classifier.classify_burst(_metrics()) == "完美稳定 ⭐"
    assert classifier.classify_burst(
        _metrics(pre_stability=0.035, total_reversals=8)
    ) == "稳定射击 ✓"
    assert classifier.classify_burst(
        _metrics(pre_stability=0.05, total_reversals=12)
    ) == "接近稳定"
    assert classifier.classify_burst(
        _metrics(pre_stability=np.nan, avg_magnitude=0.05)
    ) == "微调跟枪"


def test_classification_explanations_keep_report_text():
    assert CLASSIFICATION_EXPLANATIONS["完美稳定 ⭐"] == "教科书级压枪，准星几乎纹丝不动"
    assert CLASSIFICATION_EXPLANATIONS["数据不足"] == "burst 时长太短或采样不足"

