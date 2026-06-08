"""Tests for aedist.plot_quality_floor_heatmap_exp1."""

from pathlib import Path

from aedist.plot_quality_floor_heatmap_exp1 import (
    cell_is_red,
    heatmap_models,
    make_figure,
)
from aedist.plot_quality_spider_exp1 import (
    _PANELS,
    _aggregate,
    _load_rows,
    _model_size_rank,
)
from aedist.util import model_family


def _spider_panel_models_ref(rows):
    """Reference implementation that mirrors plot_quality_spider_exp1.make_figure."""
    stats = _aggregate(rows)
    result = []
    for _panel_key, _panel_title, families in _PANELS:
        panel_models = [m for m in stats if model_family(m) in families]
        panel_models.sort(key=lambda m: (_model_size_rank(m), m))
        result.extend(panel_models)
    return result


def test_majority_zero_marks_red():
    """3 of 5 runs score zero → cell is red (majority)."""
    runs = [0.0, 0.0, 0.0, 0.4, 0.6]
    assert cell_is_red(runs)


def test_minority_zero_not_red():
    """2 of 5 runs score zero → not a majority → not red."""
    runs = [0.0, 0.0, 0.4, 0.5, 0.6]
    assert not cell_is_red(runs)


def test_all_zero_is_red():
    """All runs score zero → trivially red."""
    assert cell_is_red([0.0, 0.0, 0.0, 0.0, 0.0])


def test_no_zero_not_red():
    """No run scores zero → not red."""
    assert not cell_is_red([0.1, 0.2, 0.3, 0.4, 0.5])


def test_empty_runs_not_red():
    """Empty run list → conservative: not red."""
    assert not cell_is_red([])


def test_model_set_matches_spider_panels():
    """Heatmap rows == spider panel models (families claude/gpt/mistral/qwen)."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    rows = _load_rows(csv_path)
    assert set(heatmap_models(rows)) == set(_spider_panel_models_ref(rows))


def test_make_figure_writes_pdf(tmp_path):
    """make_figure produces a non-empty PDF."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    rows = _load_rows(csv_path)
    out = tmp_path / "fig_quality_floor_heatmap_exp1.pdf"
    make_figure(rows, out)
    assert out.exists()
    assert out.stat().st_size > 1000
