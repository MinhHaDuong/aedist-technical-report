"""Tests for aedist.plot_quality_floor_heatmap_exp1."""

from pathlib import Path

from aedist.plot_quality_floor_heatmap_exp1 import (
    _NON_SUBSCORE_COLS,
    _VETO_COL,
    COLUMN_LABELS,
    _cell_is_red_for_column,
    _scored_columns,
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


def test_capacity_label_uses_mathtext_geq():
    """The Capacity>=0 column label must use matplotlib mathtext (\\geq), not the
    bare U+2265 glyph, which the PDF backend's default font cannot render."""
    label = COLUMN_LABELS["coherence_capacity_nonnegative"]
    assert r"\geq" in label, label
    assert "≥" not in label, label


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


# ── Polarity-aware per-column red rule ─────────────────────────────────────────
# The coherence veto column (coherence_run_veto) has INVERTED polarity: 1.0 means
# the run was vetoed (bad), 0.0 means it passed the screen. It must NOT go through
# the value==0 majority path used by genuine 0–1 sub-scores.


def test_veto_column_red_when_majority_vetoed():
    """Veto column: majority of runs == 1.0 (vetoed) → RED (opposite of a sub-score)."""
    runs = [1.0, 1.0, 1.0, 0.0, 0.0]  # 3/5 vetoed
    assert _cell_is_red_for_column(_VETO_COL, runs)


def test_veto_column_green_when_majority_passed():
    """Veto column: majority of runs == 0.0 (passed screen) → GREEN.

    A normal sub-score with these same values would be RED (3/5 zeros); the veto
    column must invert that — this is the polarity bug the fix corrects.
    """
    runs = [0.0, 0.0, 0.0, 1.0, 1.0]  # 3/5 passed, 2/5 vetoed
    assert not _cell_is_red_for_column(_VETO_COL, runs)


def test_veto_column_all_vetoed_is_red():
    """Veto column: 5/5 vetoed (e.g. claude-haiku-4.5) → RED."""
    assert _cell_is_red_for_column(_VETO_COL, [1.0, 1.0, 1.0, 1.0, 1.0])


def test_veto_column_none_vetoed_is_green():
    """Veto column: 0/5 vetoed (e.g. claude-opus-4.6) → GREEN."""
    assert not _cell_is_red_for_column(_VETO_COL, [0.0, 0.0, 0.0, 0.0, 0.0])


def test_subscore_column_keeps_zero_majority_polarity():
    """A genuine sub-score column keeps the value==0 majority rule (not inverted)."""
    # 3/5 zeros → red for a normal sub-score.
    assert _cell_is_red_for_column("accuracy_coverage", [0.0, 0.0, 0.0, 0.4, 0.6])
    # 3/5 ones, 2/5 zeros → NOT a majority of zeros → green for a normal sub-score.
    assert not _cell_is_red_for_column("accuracy_coverage", [1.0, 1.0, 1.0, 0.0, 0.0])


def test_count_columns_excluded_from_rendered_columns():
    """The raw COUNT columns are diagnostic intermediates, not rendered sub-scores."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    cols = _scored_columns(csv_path)
    assert "coherence_capacity_distinct" not in cols
    assert "coherence_status_distinct" not in cols
    assert {"coherence_capacity_distinct", "coherence_status_distinct"} <= _NON_SUBSCORE_COLS


def test_veto_column_is_rendered():
    """The coherence veto column IS rendered (as a single disqualifying column)."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    cols = _scored_columns(csv_path)
    assert _VETO_COL in cols


def test_model_set_matches_spider_panels():
    """Heatmap rows == spider panel models (families claude/gpt/mistral/qwen)."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    rows = _load_rows(csv_path)
    assert set(heatmap_models(rows)) == set(_spider_panel_models_ref(rows))


def test_scored_columns_covers_all_five_criteria():
    """_scored_columns returns sub-scores from all five criteria groups."""
    from aedist.plot_quality_floor_heatmap_exp1 import _col_criterion

    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    cols = _scored_columns(csv_path)
    criteria = {_col_criterion(c) for c in cols}
    assert criteria == {"accuracy", "coherence", "field_completeness", "provenance", "temporality"}
    # The composite accuracy_f1 must be excluded (it double-counts accuracy).
    assert "accuracy_f1" not in cols


def test_scored_columns_excludes_bookkeeping():
    """_scored_columns does not include bookkeeping or annotation columns."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    cols = _scored_columns(csv_path)
    for col in cols:
        assert not col.endswith("_annotation"), f"annotation column leaked: {col}"
        assert col not in {"arm", "model", "run", "prompt_version", "reference", "n_rows"}


def test_make_figure_writes_pdf(tmp_path):
    """make_figure produces a non-empty PDF."""
    csv_path = Path("experiments/derived/exp1_cross_eval.csv")
    rows = _load_rows(csv_path)
    out = tmp_path / "fig_quality_floor_heatmap_exp1.pdf"
    make_figure(rows, csv_path, out)
    assert out.exists()
    assert out.stat().st_size > 1000
