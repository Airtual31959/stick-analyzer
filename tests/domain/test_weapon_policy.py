from __future__ import annotations

import pytest

from stick_analyzer.domain.constants import DURING_FIRE_STABILITY_MS
from stick_analyzer.domain.services.weapon_policy import WeaponPolicy


@pytest.mark.parametrize(
    ("weapons", "expected_rpm"),
    [
        ("R-99", 1080),
        ("r301", 810),
        ("冲锋枪", 800),
        ("unknown weapon", 0),
    ],
)
def test_detect_weapon_rpm_matches_known_names_and_fallback(weapons, expected_rpm):
    assert WeaponPolicy().detect_weapon_rpm(weapons) == expected_rpm


@pytest.mark.parametrize(
    ("rpm", "expected_window_ms"),
    [
        (1080, 200),
        (600, 300),
        (30, 0),
        (0, DURING_FIRE_STABILITY_MS),
    ],
)
def test_rpm_to_during_window_ms_selects_expected_window(
    rpm,
    expected_window_ms,
):
    assert WeaponPolicy().rpm_to_during_window_ms(rpm) == expected_window_ms

