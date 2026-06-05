"""Tests for the shared P3 derivation libraries (ticket 0436).

aedist.exp1_census and aedist.exp1_cost_quality replace figure-script
side-outputs: figures and tables now import these helpers and each build their
own view of the mart (common cause), instead of one P3 script consuming
another's CSV. These tests pin the behaviour that keeps the committed handoff
artifacts byte-stable across the refactor.
"""

from aedist.exp1_census import build_census_summary
from aedist.exp1_cost_quality import build_cost_quality_rows, summary_by_slug
from aedist.tabulate_macros import generate_macros

CENSUS_METRICS = [
    {"label": "census/gpt-5.4-run1", "f1": 0.70},
    {"label": "census/gpt-5.4-run2", "f1": 0.60},
    {"label": "census/gpt-5.4-run3", "f1": 0.72},
    {"label": "census/padme-qwen3.5-27b-run1", "f1": 0.50},
    {"label": "census/padme-qwen3.5-27b-run2", "f1": 0.52},
    {"label": "census/padme-qwen3.5-27b-run3", "f1": 0.48},
    # Synthetic (-union suffix) + derived/ entries must be filtered from the
    # baseline census — same filters as the legacy plot_census derivation.
    {"label": "census/gpt-5.4-union-run1", "f1": 0.99},
    {"label": "derived/matching_sensitivity-run1", "f1": 0.91},
]


def test_build_census_summary_shape_matches_legacy_csv_roundtrip():
    """Summary keys mirror the old census_bars.csv → load_census shape.

    Each surviving model maps to ``{median_f1, is_local, runs}`` with
    ``runs == 1`` and NO ``f1_values`` key — so the downstream
    ``\\BestModelFOneCI`` macro stays degenerate rather than widening to a real
    bootstrap interval (byte-stability of macros_slides.tex).
    """
    summary = build_census_summary(CENSUS_METRICS)
    # Underscore slugs render as dashes (gpt-5.4 stays, padme keeps its dashes).
    assert set(summary) == {"gpt-5.4", "padme-qwen3.5-27b"}
    for info in summary.values():
        assert set(info) == {"median_f1", "is_local", "runs"}
        assert info["runs"] == 1
        assert "f1_values" not in info
    assert summary["padme-qwen3.5-27b"]["is_local"] is True
    assert summary["gpt-5.4"]["is_local"] is False


def test_build_census_summary_filters_synthetic_and_derived():
    """-union (synthetic) and derived/ entries never reach the census."""
    summary = build_census_summary(CENSUS_METRICS)
    assert not any(k.endswith("-union") for k in summary)
    assert all(not k.startswith("derived") for k in summary)


def test_census_summary_yields_degenerate_best_ci():
    """generate_macros over the census summary emits a degenerate CI.

    With ``runs == 1`` and no ``f1_values`` the best model's bootstrap CI
    collapses to [f1, f1] — the historical census behaviour.
    """
    summary = build_census_summary(CENSUS_METRICS)
    tex = generate_macros(summary)
    best_f1 = round(max(v["median_f1"] for v in summary.values()) * 100, 1)
    assert f"\\newcommand{{\\BestModelFOneCI}}{{[{best_f1}, {best_f1}]}}" in tex


# ---------------------------------------------------------------------------
# cost × quality shared derivation
# ---------------------------------------------------------------------------

COST_METRICS = [
    {"label": "claude-opus-4.6-run1", "n_matched": 80, "n_hallucinated": 16, "f1": 0.62, "cost_usd": 0.40},
    {"label": "claude-opus-4.6-run2", "n_matched": 82, "n_hallucinated": 9, "f1": 0.63, "cost_usd": 0.43},
    {"label": "gpt-5.5-run1", "n_matched": 73, "n_hallucinated": 12, "f1": 0.58, "cost_usd": 0.24},
]


def test_summary_by_slug_pins_cost_whiskers_degenerate():
    """min_cost == max_cost == mean_cost — E1 cost whiskers stay degenerate.

    The historical cost_quality.csv never carried per-rep cost spread, so the
    Exp2 split figures' E1 cost bars had degenerate whiskers. The shared
    derivation must reproduce that, not widen them (byte-stability of
    fig_exp2_cost.pdf).
    """
    rows = build_cost_quality_rows(COST_METRICS)
    summary = summary_by_slug(rows)
    for info in summary.values():
        assert info["min_cost"] == info["mean_cost"]
        assert info["max_cost"] == info["mean_cost"]


def test_summary_by_slug_carries_tp_and_fp_ranges():
    """The Exp2 E1 baseline bars need median/min/max TP and FP per model."""
    rows = build_cost_quality_rows(COST_METRICS)
    summary = summary_by_slug(rows)
    claude = summary["claude-opus-4.6"]
    assert claude["min_tp"] == 80
    assert claude["max_tp"] == 82
    # FP range is carried through; median of [16, 9] = 12.5 → int() = 12.
    assert claude["min_fp"] == 9
    assert claude["max_fp"] == 16
    assert claude["median_fp"] == 12
