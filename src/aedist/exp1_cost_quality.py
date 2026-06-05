"""Exp1 cost × quality derivation — shared library for the cost figure and table.

Common-cause consistency (ticket 0436): the Exp1 cost × quality scatter
(``plot_cost_quality``), its audit CSV (``tabulate_cost_quality``), and the
Exp2 split figures' E1 baseline bars (``plot_exp2_arms_split``) all derive the
per-model cost/quality summary from this one helper. No side-output chaining:
each consumer imports this library and builds its own view of the mart, never
reading another figure/table script's output file.

The single entry point :func:`load_cost_quality_rows` reconciles Experiment 1
records once (``experiments/outputs/exp1_batch2/``) and returns the per-model
summary rows; :func:`summary_by_slug` reshapes them into the keyed dict the
Exp2 split figures need.

Precedent: :mod:`aedist.exp1_recognition` (the recognition-matrix figure 0373
and status-difficulty table 0434 share their derivation the same way).
"""

import statistics
from pathlib import Path

from .evaluate import reference_plant_count
from .tabulate_utils import strip_label as slug_from_label
from .util import model_family

# Experiment 1 == the batch-2 parametric baseline sweep. Rows are selected at
# the measurements boundary by their result_file prefix; pilot runs are already
# excluded upstream because they never landed under exp1_batch2/.
EXP1_BATCH2_DIR = "experiments/outputs/exp1_batch2/"

# Vietnam thermal reference inventory size — derived from the adopted release
# (single source of truth, ticket 0413). v1 = 163, v2 = 170. Kept as a
# module-level name because plot_cost_quality and plot_exp2_arms_split import it.
N_REFERENCE_PLANTS = reference_plant_count()

# CSV/handoff column order — the audit artifact and any consumer reading it must
# agree on this schema. ``cost_usd`` is an alias for ``mean_cost`` kept for CSV
# stability.
CSV_FIELDNAMES = [
    "model",
    "family",
    "median_tp",
    "min_tp",
    "max_tp",
    "median_fp",
    "min_fp",
    "max_fp",
    "median_cost",
    "mean_cost",
    "median_f1",
    "min_f1",
    "max_f1",
    "cost_usd",
]


def _is_exp1_row(result_file: str) -> bool:
    """Return True for direct-baseline rows that count toward Experiment 1."""
    return result_file.startswith(EXP1_BATCH2_DIR)


def build_cost_quality_rows(
    metrics: list[dict],
    source_by_label: dict[str, str] | None = None,
) -> list[dict]:
    """Build rows for the cost × quality chart.

    Returns list of dicts. Each row carries per-rep ``(tp, cost, source)``
    tuples under ``reps`` so the figure can plot each rep at its own cost
    rather than collapsing all reps onto a single x-coordinate. Per-model
    summary statistics (median, min, max for TP and cost) are also
    surfaced for the median marker and the min-max range line.

    Schema: model, family, reps (list of ``{tp, cost, source}``),
    median_tp, min_tp, max_tp, tp_values, base_tp_values, topup_tp_values,
    median_cost, mean_cost, median_f1, min_f1, max_f1, cost_usd
    (alias for mean_cost, kept for CSV stability).
    Sorted by median_tp descending — the plotted Y axis.

    *source_by_label* maps each metric's ``label`` to either ``"base"``
    (original sweep) or ``"topup"`` (post-2026-05-21 reasoning-token
    top-up reps, ticket 0198). Labels not in the map default to
    ``"base"``.
    """
    if source_by_label is None:
        source_by_label = {}

    reps_by_model: dict[str, list[dict]] = {}
    f1_by_model: dict[str, list[float]] = {}
    fp_by_model: dict[str, list[int]] = {}

    for entry in metrics:
        slug = slug_from_label(entry["label"])
        source = source_by_label.get(entry["label"], "base")
        tp = entry.get("n_matched")
        cost = entry.get("cost_usd")
        if tp is not None and cost is not None and cost > 0:
            reps_by_model.setdefault(slug, []).append(
                {"tp": int(tp), "cost": float(cost), "source": source}
            )
        fp = entry.get("n_hallucinated")
        if fp is not None:
            fp_by_model.setdefault(slug, []).append(int(fp))
        f1 = entry.get("f1")
        if f1 is not None:
            f1_by_model.setdefault(slug, []).append(f1)

    rows = []
    for slug, reps in reps_by_model.items():
        tp_values = [rep["tp"] for rep in reps]
        costs = [rep["cost"] for rep in reps]
        base_tp_values = [rep["tp"] for rep in reps if rep["source"] == "base"]
        topup_tp_values = [rep["tp"] for rep in reps if rep["source"] == "topup"]
        fp_values = fp_by_model.get(slug, [])
        f1_values = f1_by_model.get(slug, [])
        mean_cost = round(sum(costs) / len(costs), 6) if costs else 0.0
        row = {
            "model": slug,
            "family": model_family(slug),
            "reps": list(reps),
            "median_tp": int(statistics.median(tp_values)),
            "min_tp": min(tp_values),
            "max_tp": max(tp_values),
            "median_fp": int(statistics.median(fp_values)) if fp_values else 0,
            "min_fp": min(fp_values) if fp_values else 0,
            "max_fp": max(fp_values) if fp_values else 0,
            "tp_values": list(tp_values),
            "base_tp_values": base_tp_values,
            "topup_tp_values": topup_tp_values,
            "median_cost": round(statistics.median(costs), 6) if costs else 0.0,
            "mean_cost": mean_cost,
            "median_f1": round(statistics.median(f1_values), 4) if f1_values else 0.0,
            "min_f1": round(min(f1_values), 4) if f1_values else 0.0,
            "max_f1": round(max(f1_values), 4) if f1_values else 0.0,
            "cost_usd": mean_cost,
        }
        rows.append(row)
    rows.sort(key=lambda r: r["median_tp"], reverse=True)
    return rows


def load_cost_quality_rows() -> list[dict]:
    """Reconcile Experiment 1 records from the mart once; return summary rows.

    Filters ``measurements.jsonl`` to Experiment 1 (the exp1_batch2 baseline),
    builds the per-(model, rep) source map (base vs reasoning-token top-up), and
    returns the rows from :func:`build_cost_quality_rows`. This is the single
    derivation both the figure and the audit CSV project.
    """
    from .measurements import load, records_to_metrics

    records = [r for r in load() if r.result_file and _is_exp1_row(r.result_file)]
    metrics = records_to_metrics(records)

    # Build label → "base" | "topup" map so the plotter can render the two
    # cohorts with different glyphs. Label format matches records_to_metrics:
    # f"{prompt_version}/{stem}" (or just the stem when prompt_version is empty).
    source_by_label: dict[str, str] = {}
    for r in records:
        if not r.result_file:
            continue
        stem = Path(r.result_file).stem
        prompt_version = r.method_params.prompt_version or ""
        label = f"{prompt_version}/{stem}" if prompt_version else stem
        source_by_label[label] = "topup" if ".topup" in r.result_file else "base"

    return build_cost_quality_rows(metrics, source_by_label=source_by_label)


def summary_by_slug(rows: list[dict]) -> dict[str, dict]:
    """Reshape cost-quality rows into the per-slug summary the Exp2 bars need.

    Returns ``{slug: {median_tp, min_tp, max_tp, median_fp, min_fp, max_fp,
    mean_cost, min_cost, max_cost}}``. ``min_cost``/``max_cost`` are pinned to
    ``mean_cost`` — the cost figure's E1 whiskers were always degenerate (the
    historical audit CSV never carried per-rep cost spread), so the shared
    derivation reproduces that exactly rather than widening them.
    """
    summary: dict[str, dict] = {}
    for row in rows:
        mean_cost = float(row["mean_cost"])
        summary[row["model"]] = {
            "median_tp": int(row["median_tp"]),
            "min_tp": int(row["min_tp"]),
            "max_tp": int(row["max_tp"]),
            "median_fp": int(row.get("median_fp") or 0),
            "min_fp": int(row.get("min_fp") or 0),
            "max_fp": int(row.get("max_fp") or 0),
            "mean_cost": mean_cost,
            "min_cost": mean_cost,
            "max_cost": mean_cost,
        }
    return summary
