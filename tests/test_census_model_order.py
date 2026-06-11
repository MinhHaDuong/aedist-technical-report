"""Tests for the shared census model-ordering function (ticket 0504).

`census_model_order` is the single source of truth for the 14-model census
order used by Figure 2 (plot_method_convergence) and the quality-floor
heatmap. Three guards:

1. A literal-order tripwire: the order, verified visually against the
   committed fig_direct_p1_base.pdf (PR #914, 2026-06-09). If the model set
   changes, update it by re-reading Figure 2 — never by copying the
   function's own output (that would make the test tautological).
2. A delegation check: heatmap_models must produce exactly the shared order.
3. A name-only resolution check: every census model resolves a size from its
   name alone (registry or regex), never the 500 "unknown" fallback that
   would collapse distinct models into one tie broken alphabetically.
"""

from pathlib import Path

from aedist.plot_method_convergence import _model_size_b, census_model_order
from aedist.plot_quality_floor_heatmap_exp1 import heatmap_models
from aedist.plot_quality_spider_exp1 import _load_rows

_CSV_PATH = Path("experiments/derived/exp1_cross_eval.csv")

# Verified visually against the committed fig_direct_p1_base.pdf (PR #914).
_FIGURE2_RENDER_ORDER = [
    "claude-opus-4.6",
    "claude-sonnet-4.6",
    "claude-haiku-4.5",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "gpt-5.5",
    "gpt-oss-120b",
    "gpt-oss-20b",
    "mistral-large-2512",
    "mistral-medium-3-5",
    "mistral-small-2603",
    "qwen3.7-max",
    "qwen3.6-35b-a3b",
    "qwen3.6-flash",
]


def _census_models() -> list[str]:
    rows = _load_rows(_CSV_PATH)
    return sorted({str(r.get("model", "")).strip() for r in rows if str(r.get("model", "")).strip()})


def test_census_order_matches_figure2_render():
    """The real guard: shared order equals the visually-verified literal."""
    assert census_model_order(_census_models()) == _FIGURE2_RENDER_ORDER


def test_heatmap_delegates_to_census_order():
    """Delegation, not coincidence: heatmap columns ARE the shared order."""
    rows = _load_rows(_CSV_PATH)
    assert heatmap_models(rows) == census_model_order(_census_models())


def test_census_sizes_resolve_from_name_alone():
    """Every census model resolves a size from its name (registry or regex),
    never the 500 size_class-unknown fallback — so the order needs no
    per-record size_class column (the heatmap CSV has none)."""
    for model in _FIGURE2_RENDER_ORDER:
        assert _model_size_b(model) != 500.0, f"{model} falls back to the 500 default"
