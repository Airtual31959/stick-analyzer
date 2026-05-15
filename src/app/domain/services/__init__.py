"""领域服务集合。"""

from .burst_analyzer import BurstAnalyzer, analyze_burst
from .burst_classifier import (
    BurstClassifier,
    CLASSIFICATION_EXPLANATIONS,
    classify_burst,
)
from .fire_burst_detector import FireBurstDetector, detect_fire_bursts
from .threshold_policy import ThresholdPolicy, get_stability_thresholds
from .weapon_policy import WeaponPolicy, detect_weapon_rpm, rpm_to_during_window_ms

__all__ = [
    "BurstAnalyzer",
    "BurstClassifier",
    "CLASSIFICATION_EXPLANATIONS",
    "FireBurstDetector",
    "ThresholdPolicy",
    "WeaponPolicy",
    "analyze_burst",
    "classify_burst",
    "detect_fire_bursts",
    "detect_weapon_rpm",
    "get_stability_thresholds",
    "rpm_to_during_window_ms",
]

