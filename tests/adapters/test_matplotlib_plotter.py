from __future__ import annotations

import numpy as np
import pandas as pd

from app.adapters.reporting import matplotlib_plotter


def _metrics() -> dict:
    rel_t = np.linspace(-0.2, 0.5, 24)
    fire = (rel_t >= 0) & (rel_t <= 0.35)
    ads = rel_t >= -0.05
    return {
        "data": pd.DataFrame(
            {
                "rel_t": rel_t,
                "rx": np.sin(rel_t * 10) * 0.08,
                "ry": np.cos(rel_t * 8) * 0.05,
                "lx": np.zeros_like(rel_t),
                "ly": np.linspace(0, 0.2, len(rel_t)),
                "fire": fire,
                "ads": ads,
            }
        ),
        "duration": 0.35,
        "pre_stability": 0.024,
        "during_stability": 0.031,
        "total_reversals": 3,
        "dominant_input_low": 12.0,
        "dominant_input_high": 18.0,
        "is_ads": True,
        "is_moving": False,
        "avg_magnitude": 0.12,
    }


def test_plot_burst_writes_png(tmp_path):
    output_path = tmp_path / "burst.png"

    matplotlib_plotter.plot_burst(_metrics(), output_path, "测试波形")

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_summary_writes_png_and_skips_nan_metrics(tmp_path):
    valid = {"metrics": _metrics()}
    skipped = {"metrics": {**_metrics(), "during_stability": np.nan}}
    output_path = tmp_path / "summary.png"

    matplotlib_plotter.plot_summary([valid, skipped], output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_summary_returns_without_file_when_no_valid_metrics(tmp_path):
    output_path = tmp_path / "empty.png"

    matplotlib_plotter.plot_summary(
        [{"metrics": {**_metrics(), "pre_stability": np.nan}}],
        output_path,
    )

    assert not output_path.exists()
