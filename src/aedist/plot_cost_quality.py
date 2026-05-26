"""Generate cost × quality CSV and scatter PDF from measurements.jsonl.

Scope: **Experiment 1 only** (the parametric baseline sweep,
``experiments/outputs/ablation/direct/p1_base/``). Pilot rows under
``p1_base.pilot/`` are excluded. The figure is descriptive — no
Pareto-efficient envelope is drawn.

Y axis: per-model **count of correctly identified plants** (true positives,
``n_matched`` in measurements) plotted as median with min/max whiskers
across the 5 reps. A horizontal reference line marks the full reference
inventory size (163 thermal plants).

Writes a CSV with columns:
    model, family, median_tp, min_tp, max_tp,
    median_f1, min_f1, max_f1, cost_usd
sorted by median TP descending. Optionally writes a PDF scatter plot.

Family colouring: per-model colour comes from
``aedist.util.model_family_color()`` (palette.toml, architectural-family
axis: Claude / GPT / Mistral / Qwen / DeepSeek). Single marker per
model; colour conveys family.

x-axis: cost per call in **USD cents** (``cost_usd × 100``), displayed
in decimal (not scientific) notation. Scale controlled by
``--xscale {linear,log}`` (default log). For log mode, models reporting
``cost_usd <= 0`` are dropped with a warning — clamping to an ε or
pinning to a dedicated "\\$0" tick would mis-represent the scale. All
Experiment 1 models are cloud and carry non-zero costs, so this branch
does not fire on current data; it becomes relevant when the script is
reused for Experiments 2/3.

Usage::

    uv run python -m aedist.plot_cost_quality \\
        --output report/inputs/generated/cost_quality.csv \\
        --figure report/inputs/generated/fig_direct_cost_quality.pdf \\
        --xscale log
"""

import argparse
import csv
import logging
from pathlib import Path

from .tabulate_utils import strip_label as slug_from_label
from .util import (
    COLOR_REFERENCE,
    SLIDE_FIGSIZE_WIDE,
    glyph_for_method,
    glyph_scatter_kwargs,
    model_family,
    model_family_color,
)

log = logging.getLogger(__name__)

# Experiment 1 lives under outputs/ablation/direct/. The journal sweep wrote
# to p1_base/ on 2026-05-20; the reasoning-token top-up (ticket 0198) added
# reps to p1_base.topup_canary/ and p1_base.topup/. We pool all three
# directories into the Exp 1 distribution unconditionally — no canary gate,
# intra-day variability is absorbed into the reported within-model variance.
# Pilot runs (p1_base.pilot/) remain excluded.
P1_BASE_DIR = "experiments/outputs/ablation/direct/"
P1_INCLUDED_SUBDIRS = (
    "p1_base/",
    "p1_base.topup/",
    "p1_base.topup_canary/",
)
P1_PILOT_MARKER = "/p1_base.pilot/"
EXP1_BATCH2_DIR = "experiments/outputs/exp1_batch2/"

# Vietnam thermal reference inventory size (Annex A, line 72).
N_REFERENCE_PLANTS = 163


def _is_p1_base_row(result_file: str) -> bool:
    """Return True for direct-baseline rows that count toward Experiment 1.

    Pools the original journal sweep with the post-PR-#379 top-up reps
    (ticket 0198). Excludes pilot runs.
    """
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
    import statistics

    if source_by_label is None:
        source_by_label = {}

    reps_by_model: dict[str, list[dict]] = {}
    f1_by_model: dict[str, list[float]] = {}

    for entry in metrics:
        slug = slug_from_label(entry["label"])
        source = source_by_label.get(entry["label"], "base")
        tp = entry.get("n_matched")
        cost = entry.get("cost_usd")
        fp = int(entry.get("n_hallucinated") or 0)
        if tp is not None and cost is not None and cost > 0:
            reps_by_model.setdefault(slug, []).append(
                {"tp": int(tp), "fp": fp, "cost": float(cost), "source": source}
            )
        f1 = entry.get("f1")
        if f1 is not None:
            f1_by_model.setdefault(slug, []).append(f1)

    rows = []
    for slug, reps in reps_by_model.items():
        tp_values = [rep["tp"] for rep in reps]
        fp_values = [rep["fp"] for rep in reps]
        costs = [rep["cost"] for rep in reps]
        base_tp_values = [rep["tp"] for rep in reps if rep["source"] == "base"]
        topup_tp_values = [rep["tp"] for rep in reps if rep["source"] == "topup"]
        f1_values = f1_by_model.get(slug, [])
        mean_cost = round(sum(costs) / len(costs), 6) if costs else 0.0
        row = {
            "model": slug,
            "family": model_family(slug),
            "reps": list(reps),
            "median_tp": int(statistics.median(tp_values)),
            "min_tp": min(tp_values),
            "max_tp": max(tp_values),
            "tp_values": list(tp_values),
            "fp_values": fp_values,
            "base_tp_values": base_tp_values,
            "topup_tp_values": topup_tp_values,
            "median_fp": int(statistics.median(fp_values)),
            "min_fp": min(fp_values),
            "max_fp": max(fp_values),
            "median_cost": round(statistics.median(costs), 6) if costs else 0.0,
            "min_cost": round(min(costs), 6) if costs else 0.0,
            "max_cost": round(max(costs), 6) if costs else 0.0,
            "mean_cost": mean_cost,
            "median_f1": round(statistics.median(f1_values), 4) if f1_values else 0.0,
            "min_f1": round(min(f1_values), 4) if f1_values else 0.0,
            "max_f1": round(max(f1_values), 4) if f1_values else 0.0,
            "cost_usd": mean_cost,
        }
        rows.append(row)
    rows.sort(key=lambda r: r["median_tp"], reverse=True)
    return rows


# Family assignment for the 2-panel split. Panel A holds Western families
# (Claude / GPT / Mistral); panel B holds Chinese families (Qwen / DeepSeek).
# Note: gpt-oss-* are open-weight but still routed to panel A by family.
_PANEL_A_FAMILIES = {"claude", "gpt", "mistral"}
_PANEL_B_FAMILIES = {"qwen", "deepseek"}


def _plot_one_row(ax, row: dict) -> None:
    """Render a single model's reps as uniform filled disks with a trajectory line."""
    colour = model_family_color(row["model"])
    reps = row.get("reps") or []
    pts = sorted([(rep["cost"] * 100.0, rep["tp"]) for rep in reps], key=lambda p: p[0])
    if len(pts) >= 2:
        ax.plot(
            [c for c, _ in pts],
            [t for _, t in pts],
            color=colour,
            linewidth=0.6,
            alpha=0.6,
            zorder=1,
        )
    if pts:
        glyph = glyph_scatter_kwargs("parametric", colour)
        ax.scatter(
            [c for c, _ in pts],
            [t for _, t in pts],
            **glyph,
            zorder=2,
        )


def _configure_axes(ax, xscale: str, xmax: float) -> None:
    """Apply shared cosmetic settings (reference line, scale, ticks, grid) to *ax*."""
    ax.axhline(
        N_REFERENCE_PLANTS,
        color=COLOR_REFERENCE,
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        zorder=1,
    )
    if xscale == "log":
        from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

        ax.set_xscale("log")
        ticks = [0.1, 0.5, 1, 5, 10, 20, 30]
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"{x:g}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
    else:
        ax.set_xlim(-0.05, xmax * 1.05)
    ax.grid(True, alpha=0.3)


def write_pdf(rows: list[dict], output: Path, xscale: str = "log") -> None:
    """Write the cost × quality scatter (correctly-identified plants vs cost) to *output*.

    Two-panel layout: panel (a) holds Claude / GPT / Mistral; panel (b)
    holds Qwen / DeepSeek. Both panels share the X and Y axes so the
    cost gap between Western and Chinese families is visible at a
    glance. Each model gets a filled square at its median (TP, cost),
    unfilled circles for journal-sweep reps, and ✕ markers for the
    reasoning-token top-up reps. A horizontal reference line marks
    ``N_REFERENCE_PLANTS`` on each panel. Y axis runs from -5 so
    refusal markers at TP=0 sit above the axis line. ``xscale``
    accepts ``"linear"`` or ``"log"``; log mode drops zero-cost models
    with a warning.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    filtered = [r for r in rows if r["cost_usd"] > 0]
    if xscale == "log":
        dropped = [r["model"] for r in rows if r["cost_usd"] <= 0]
        if dropped:
            log.warning(
                "--xscale log: dropping %d zero-cost model(s) (%s); "
                "log axes cannot represent cost = 0.",
                len(dropped),
                ", ".join(dropped),
            )

    panel_a = [r for r in filtered if r["family"] in _PANEL_A_FAMILIES]
    panel_b = [r for r in filtered if r["family"] in _PANEL_B_FAMILIES]
    unassigned = [
        r for r in filtered if r["family"] not in (_PANEL_A_FAMILIES | _PANEL_B_FAMILIES)
    ]
    if unassigned:
        log.warning(
            "Unassigned family for %d model(s) (%s); rendered in panel (a) by default.",
            len(unassigned),
            ", ".join(r["model"] for r in unassigned),
        )
        panel_a = panel_a + unassigned

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=SLIDE_FIGSIZE_WIDE, sharex=True, sharey=True)

    for r in panel_a:
        _plot_one_row(ax_a, r)
    for r in panel_b:
        _plot_one_row(ax_b, r)

    xmax = max((r["cost_usd"] * 100.0 for r in filtered), default=30.0)
    _configure_axes(ax_a, xscale, xmax)
    _configure_axes(ax_b, xscale, xmax)

    # sharey=True propagates the limit; setting on ax_a is enough.
    ax_a.set_ylim(-5, N_REFERENCE_PLANTS * 1.05)

    ax_a.set_title("(a) Western labs", loc="left", fontsize=11, fontweight="bold")
    ax_b.set_title("(b) Asian labs", loc="left", fontsize=11, fontweight="bold")
    ax_a.set_ylabel("Assets correctly identified")
    fig.supxlabel("Cost per run (USD cents)")
    fig.suptitle(
        "Cost vs Accuracy across 5 model families (no search, one shot, no docs)",
        y=0.995,
        fontsize=13,
        fontweight="bold",
    )

    def _family_handle(slug_seed: str, label: str) -> Line2D:
        glyph = glyph_for_method("parametric")
        return Line2D(
            [0],
            [0],
            color=model_family_color(slug_seed),
            linewidth=0,
            marker=str(glyph["marker"]),
            markersize=6,
            label=label,
        )

    panel_a_handles = [
        _family_handle("claude-opus", "Claude"),
        _family_handle("gpt-5", "GPT"),
        _family_handle("mistral-large", "Mistral"),
    ]
    panel_b_handles = [
        _family_handle("qwen3-max", "Qwen"),
        _family_handle("deepseek-v4", "DeepSeek"),
    ]
    ax_a.legend(handles=panel_a_handles, loc="upper left", fontsize="small")
    ax_b.legend(handles=panel_b_handles, loc="upper left", fontsize="small")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate cost × quality CSV and/or scatter PDF (Experiment 1 only)",
    )
    parser.add_argument("--output", help="Path to write cost_quality.csv")
    parser.add_argument("--figure", help="Path to write scatter PDF")
    parser.add_argument(
        "--xscale",
        choices=("linear", "log"),
        default="log",
        help="x-axis scale for the figure (default: log). "
        "Log mode drops zero-cost models with a warning.",
    )
    args = parser.parse_args()

    if not args.output and not args.figure:
        parser.error("at least one of --output or --figure is required")

    from .measurements import load, records_to_metrics

    # Filter at the boundary: Experiment 1 == p1_base + topup variants.
    records = [r for r in load() if r.result_file and _is_p1_base_row(r.result_file)]
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

    rows = build_cost_quality_rows(metrics, source_by_label=source_by_label)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "model",
                    "family",
                    "median_tp",
                    "min_tp",
                    "max_tp",
                    "median_fp",
                    "min_fp",
                    "max_fp",
                    "median_cost",
                    "min_cost",
                    "max_cost",
                    "mean_cost",
                    "median_f1",
                    "min_f1",
                    "max_f1",
                    "cost_usd",
                ],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
        log.info("Wrote %d rows to %s", len(rows), output_path)

    if args.figure:
        write_pdf(rows, Path(args.figure), xscale=args.xscale)


if __name__ == "__main__":
    main()
