"""Tests for aedist.plot_quality_floor_heatmap_exp1."""

from pathlib import Path

from aedist.plot_quality_floor_heatmap_exp1 import (
    _NON_SUBSCORE_COLS,
    _VETO_COL,
    COLUMN_LABELS,
    _col_criterion,
    _collect_runs,
    _scored_columns,
    _subscore_value,
    discriminating_columns,
    heatmap_models,
    make_figure,
    mean_score,
)
from aedist.plot_quality_spider_exp1 import _load_rows, _model_size_rank
from aedist.util import model_family

_CSV_PATH = Path("experiments/derived/exp1_cross_eval.csv")


def test_capacity_label_uses_mathtext_geq():
    """The Capacity>=0 row label must use matplotlib mathtext (\\geq), not the
    bare U+2265 glyph, which the PDF backend's default font cannot render."""
    label = COLUMN_LABELS["coherence_capacity_nonnegative"]
    assert r"\geq" in label, label
    assert "≥" not in label, label


# ── Continuous mean aggregation (replaces the old boolean red-cell rule) ──────


def test_mean_score_is_plain_mean_for_subscore():
    """A genuine sub-score aggregates to the plain mean of its run values."""
    assert mean_score("accuracy_coverage", [0.0, 0.0, 0.0, 0.4, 0.6]) == 0.2


def test_mean_score_zero_when_all_runs_zero():
    """A model that zeros a criterion on every run aggregates to 0 (dark red)."""
    assert mean_score("accuracy_coverage", [0.0, 0.0, 0.0, 0.0, 0.0]) == 0.0


def test_mean_score_empty_is_none():
    """No data → None (rendered as a no-data cell, not 0)."""
    assert mean_score("accuracy_coverage", []) is None


# ── Internal-coherence veto merged into Coherence as its positive complement ──


def test_veto_value_is_inverted_to_quality():
    """A vetoed run (1.0) maps to 0 quality; a passed run (0.0) maps to 1."""
    assert _subscore_value(_VETO_COL, 1.0) == 0.0
    assert _subscore_value(_VETO_COL, 0.0) == 1.0


def test_subscore_value_passes_through_genuine_scores():
    """Genuine sub-scores are already higher-is-better and pass through."""
    assert _subscore_value("accuracy_coverage", 0.4) == 0.4


def test_veto_mean_is_fraction_passing():
    """The merged Internal-coherence score is the fraction of runs that passed.

    3/5 vetoed → 2/5 passed → mean quality 0.4 (opposite polarity to a raw
    zero-majority sub-score, which would read 0.4 of a different quantity).
    """
    assert mean_score(_VETO_COL, [1.0, 1.0, 1.0, 0.0, 0.0]) == 0.4


def test_veto_all_vetoed_is_zero():
    """5/5 vetoed (e.g. claude-haiku-4.5) → Internal coherence 0 (dark red)."""
    assert mean_score(_VETO_COL, [1.0, 1.0, 1.0, 1.0, 1.0]) == 0.0


def test_veto_none_vetoed_is_one():
    """0/5 vetoed (e.g. claude-opus-4.6) → Internal coherence 1 (green)."""
    assert mean_score(_VETO_COL, [0.0, 0.0, 0.0, 0.0, 0.0]) == 1.0


def test_veto_label_says_internal_coherence():
    """The veto sub-score is labelled as merged into Coherence, not as a veto column."""
    assert COLUMN_LABELS[_VETO_COL] == "Internal coherence"


def test_veto_is_in_coherence_dimension():
    """The veto sub-score is grouped under the Coherence criterion, not standalone."""
    assert _col_criterion(_VETO_COL) == "coherence"


# ── Column (sub-score) selection from the CSV header ──────────────────────────


def test_count_columns_excluded_from_rendered_columns():
    """The raw COUNT columns are diagnostic intermediates, not rendered sub-scores."""
    cols = _scored_columns(_CSV_PATH)
    assert "coherence_capacity_distinct" not in cols
    assert "coherence_status_distinct" not in cols
    assert {"coherence_capacity_distinct", "coherence_status_distinct"} <= _NON_SUBSCORE_COLS


def test_veto_subscore_is_rendered():
    """The coherence veto IS rendered (as the merged Internal-coherence sub-score)."""
    cols = _scored_columns(_CSV_PATH)
    assert _VETO_COL in cols


def test_scored_columns_covers_all_five_criteria():
    """_scored_columns returns sub-scores from all five criteria groups."""
    cols = _scored_columns(_CSV_PATH)
    criteria = {_col_criterion(c) for c in cols}
    assert criteria == {"accuracy", "coherence", "field_completeness", "provenance", "temporality"}
    # The composite accuracy_f1 must be excluded (it double-counts accuracy).
    assert "accuracy_f1" not in cols


def test_scored_columns_excludes_bookkeeping():
    """_scored_columns does not include bookkeeping or annotation columns."""
    cols = _scored_columns(_CSV_PATH)
    for col in cols:
        assert not col.endswith("_annotation"), f"annotation column leaked: {col}"
        assert col not in {"arm", "model", "run", "prompt_version", "reference", "n_rows"}


# ── Model column order: identical to Figure 2, DeepSeek included ──────────────


def _figure2_order_ref(rows):
    """Reference: family alphabetical, size-rank descending, name (mirrors Fig 2)."""
    models = sorted({str(r.get("model", "")).strip() for r in rows if str(r.get("model", "")).strip()})
    models.sort(key=lambda m: (model_family(m), -_model_size_rank(m), m))
    return models


def test_model_order_matches_figure2_ordering():
    """Heatmap columns follow the same ordering rule as Figure 2's census."""
    rows = _load_rows(_CSV_PATH)
    assert heatmap_models(rows) == _figure2_order_ref(rows)


def test_deepseek_included_in_columns():
    """DeepSeek is part of the fourteen census models and must appear as columns."""
    rows = _load_rows(_CSV_PATH)
    models = heatmap_models(rows)
    assert any(model_family(m) == "deepseek" for m in models), models


def test_families_are_contiguous_and_alphabetical():
    """Models are grouped by family in alphabetical family order (as Figure 2)."""
    rows = _load_rows(_CSV_PATH)
    families = [model_family(m) for m in heatmap_models(rows)]
    # First occurrence order of families is alphabetical.
    first_seen = list(dict.fromkeys(families))
    assert first_seen == sorted(first_seen), first_seen
    # Each family occupies one contiguous block.
    assert len(first_seen) == len({*families}) == sum(
        1 for i, f in enumerate(families) if i == 0 or families[i - 1] != f
    )


# ── Non-discriminating (all-green) sub-scores are dropped ─────────────────────


def test_discriminating_drops_constant_subscore():
    """A sub-score every model clears uniformly is dropped (spread below floor)."""
    models = ["a", "b", "c"]
    run_values = {m: {"x": [1.0, 1.0], "y": [0.0, 0.2]} for m in models}
    # x is constant 1.0 across models (no spread); y varies enough between models?
    run_values["a"]["y"] = [1.0, 1.0]
    run_values["c"]["y"] = [0.0, 0.0]
    kept = discriminating_columns(["x", "y"], run_values, models, min_spread=0.10)
    assert "x" not in kept  # constant → dropped
    assert "y" in kept  # spans 0..1 across models → kept


def test_real_data_drops_uniform_field_completeness():
    """On the real CSV the all-green criteria (incl. all of Field completeness)
    are dropped, leaving only criteria that separate the models."""
    rows = _load_rows(_CSV_PATH)
    models = heatmap_models(rows)
    candidates = _scored_columns(_CSV_PATH)
    run_values = _collect_runs(rows, models, candidates)
    kept = discriminating_columns(candidates, run_values, models)
    # The uniform ≈1.0 criteria are gone.
    for dropped in (
        "coherence_capacity_nonnegative",
        "field_completeness_core",
        "field_completeness_capacity",
        "provenance_source_presence",
        "provenance_high_conf_dual_source",
        "temporality_asof_presence",
    ):
        assert dropped not in kept, dropped
    # The whole Field-completeness dimension drops out.
    assert all(_col_criterion(c) != "field_completeness" for c in kept)
    # Discriminating criteria survive, including the merged internal-coherence.
    for survives in ("accuracy_coverage", "coherence_vocab_adherence", _VETO_COL):
        assert survives in kept, survives


# ── Rendering smoke test ──────────────────────────────────────────────────────


def test_make_figure_writes_pdf(tmp_path):
    """make_figure produces a non-empty PDF."""
    rows = _load_rows(_CSV_PATH)
    out = tmp_path / "fig_quality_floor_heatmap_exp1.pdf"
    make_figure(rows, _CSV_PATH, out)
    assert out.exists()
    assert out.stat().st_size > 1000
