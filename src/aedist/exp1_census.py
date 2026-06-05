"""Census summary derivation — shared by the slide macros (table layer).

Common-cause consistency (ticket 0436): the slide-macro table reads its census
summary (per-model median F1 + local flag, baseline models only) from this
shared library, not from a figure script's CSV side-output. Before 0436 the
derivation lived in ``plot_census.py`` (a figure script that emitted only a CSV
— a view-builder wearing a figure script's name) and was round-tripped through
``census_bars.csv`` into ``tabulate_macros``. That P3-to-P3 edge is gone:
``tabulate_macros`` now imports :func:`build_census_summary` directly.

The summary shape mirrors what ``tabulate_macros.load_census`` used to return
from the CSV — ``{slug: {median_f1, is_local, runs}}`` with ``runs == 1`` and
*no* ``f1_values`` key — so the downstream ``\\BestModelFOneCI`` macro keeps its
degenerate single-value bootstrap CI rather than widening to a real interval.
"""


from .measurements import SYNTHETIC_SUFFIXES
from .tabulate_macros import load_and_summarize


def build_census_summary(metrics: list[dict]) -> dict[str, dict]:
    """Build the per-model census summary (baseline models only).

    Filters out derived measurements (``derived/`` label prefix) and synthetic
    entries (union-vote, consolidated — :data:`SYNTHETIC_SUFFIXES`) so the
    summary shows single-shot baseline performance only, then keys each
    surviving model to ``{median_f1, is_local, runs}``.

    The dict shape matches the legacy ``census_bars.csv`` round-trip
    (``runs == 1``, no ``f1_values``) so the generated slide macros are
    byte-identical to the pre-refactor output.
    """
    metrics = [m for m in metrics if not m.get("label", "").startswith("derived/")]
    summary = load_and_summarize(metrics)
    return {
        slug.replace("_", "-"): {
            "median_f1": info["median_f1"],
            "is_local": info["is_local"],
            "runs": 1,
        }
        for slug, info in summary.items()
        if not any(slug.endswith(s) for s in SYNTHETIC_SUFFIXES)
    }
