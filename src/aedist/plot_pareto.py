"""Generate Pareto-front CSV and scatter PDF from measurements.jsonl.

Scope: **Experiment 1 only** (the parametric baseline sweep,
``experiments/outputs/ablation/direct/p1_base/``). Pilot rows under
``p1_base.pilot/`` are excluded.

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

    uv run python -m aedist.plot_pareto \\
        --output slides/inputs/generated/pareto.csv \\
        --figure slides/inputs/generated/fig_pareto.pdf \\
        --xscale log
"""

import argparse
import csv
import logging
from pathlib import Path

from .tabulate_utils import strip_label as slug_from_label
from .util import COLOR_REFERENCE, model_family, model_family_color

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

# Vietnam thermal reference inventory size (Annex A, line 72).
N_REFERENCE_PLANTS = 163


def _is_p1_base_row(result_file: str) -> bool:
    """Return True for direct-baseline rows that count toward Experiment 1.

    Pools the original journal sweep with the post-PR-#379 top-up reps
    (ticket 0198). Excludes pilot runs.
    """
    if P1_PILOT_MARKER in result_file:
        return False
    return any(result_file.startswith(P1_BASE_DIR + sub) for sub in P1_INCLUDED_SUBDIRS)


def build_pareto_rows(
    metrics: list[dict],
    source_by_label: dict[str, str] | None = None,
) -> list[dict]:
    """Build rows for the Pareto chart.

    Returns list of dicts with keys: model, family, median_tp, min_tp,
    max_tp, tp_values (pooled), base_tp_values, topup_tp_values,
    median_f1, min_f1, max_f1, cost_usd. Sorted by median_tp descending —
    the plotted axis. Median / min / max are computed over the **pooled**
    distribution.

    *source_by_label* maps each metric's ``label`` to either ``"base"``
    (original sweep) or ``"topup"`` (post-2026-05-21 reasoning-token
    top-up reps, ticket 0198). Labels not in the map default to
    ``"base"``. The figure uses the per-source partition to draw
    different markers for each cohort.
    """
    import statistics

    if source_by_label is None:
        source_by_label = {}

    tp_by_model: dict[str, list[int]] = {}
    base_tp_by_model: dict[str, list[int]] = {}
    topup_tp_by_model: dict[str, list[int]] = {}
    f1_by_model: dict[str, list[float]] = {}
    cost_by_model: dict[str, list[float]] = {}

    for entry in metrics:
        slug = slug_from_label(entry["label"])
        source = source_by_label.get(entry["label"], "base")
        tp = entry.get("n_matched")
        if tp is not None:
            tp_int = int(tp)
            tp_by_model.setdefault(slug, []).append(tp_int)
            if source == "topup":
                topup_tp_by_model.setdefault(slug, []).append(tp_int)
            else:
                base_tp_by_model.setdefault(slug, []).append(tp_int)
        f1 = entry.get("f1")
        if f1 is not None:
            f1_by_model.setdefault(slug, []).append(f1)
        cost = entry.get("cost_usd")
        if cost is not None and cost > 0:
            cost_by_model.setdefault(slug, []).append(cost)

    rows = []
    for slug, tp_values in tp_by_model.items():
        f1_values = f1_by_model.get(slug, [])
        costs = cost_by_model.get(slug, [])
        row = {
            "model": slug,
            "family": model_family(slug),
            "median_tp": int(statistics.median(tp_values)),
            "min_tp": min(tp_values),
            "max_tp": max(tp_values),
            "tp_values": list(tp_values),
            "base_tp_values": list(base_tp_by_model.get(slug, [])),
            "topup_tp_values": list(topup_tp_by_model.get(slug, [])),
            "median_f1": round(statistics.median(f1_values), 4) if f1_values else 0.0,
            "min_f1": round(min(f1_values), 4) if f1_values else 0.0,
            "max_f1": round(max(f1_values), 4) if f1_values else 0.0,
            "cost_usd": round(sum(costs) / len(costs), 6) if costs else 0.0,
        }
        rows.append(row)
    rows.sort(key=lambda r: r["median_tp"], reverse=True)
    return rows


def write_pdf(rows: list[dict], output: Path, xscale: str = "log") -> None:
    """Write the Pareto scatter (correctly-identified plants vs cost) to *output*.

    Each model gets one **filled circle** at its median TP count and an
    **x marker** for every other rep — the eye sees both the central
    tendency and the full per-rep spread. Colour conveys the
    architectural family via :func:`aedist.util.model_family_color`.
    A horizontal reference line marks ``N_REFERENCE_PLANTS`` (the full
    Vietnam thermal inventory). ``xscale`` accepts ``"linear"`` or
    ``"log"``; log mode drops zero-cost models with a warning.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # Drop cloud models without cost data (legacy behaviour).
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

    fig, ax = plt.subplots(figsize=(7, 4.5))

    for r in filtered:
        colour = model_family_color(r["model"])
        median = r["median_tp"]
        cost_cents = r["cost_usd"] * 100.0  # display axis is USD cents
        # Thin min-max line behind the markers (range cue).
        ax.plot(
            [cost_cents, cost_cents],
            [r["min_tp"], r["max_tp"]],
            color=colour,
            linewidth=0.6,
            alpha=0.7,
            zorder=1,
        )
        # Yesterday's reps (p1_base/, 2026-05-20 journal sweep): unfilled circle.
        base_reps = r.get("base_tp_values") or []
        if base_reps:
            ax.scatter(
                [cost_cents] * len(base_reps),
                base_reps,
                marker="o",
                facecolors="none",
                edgecolors=colour,
                s=36,
                linewidths=1.0,
                zorder=2,
            )
        # Today's reps (p1_base.topup*/, post-PR-#379 reasoning-token top-up): x.
        topup_reps = r.get("topup_tp_values") or []
        if topup_reps:
            ax.scatter(
                [cost_cents] * len(topup_reps),
                topup_reps,
                marker="x",
                color=colour,
                s=30,
                linewidths=1.2,
                zorder=2,
            )
        # Pooled median: filled square (drawn at the computed value, not at a
        # specific rep — the median may interpolate between two reps).
        ax.scatter(
            [cost_cents],
            [median],
            marker="s",
            color=colour,
            s=50,
            zorder=3,
        )

    # Reference line at the full inventory size.
    ax.axhline(
        N_REFERENCE_PLANTS,
        color=COLOR_REFERENCE,
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        zorder=1,
    )

    ax.set_xlabel("Coût par requête (cents USD)")
    ax.set_ylabel("Nombre de centrales bien identifiées")
    ax.set_ylim(0, N_REFERENCE_PLANTS * 1.05)
    if xscale == "log":
        from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

        ax.set_xscale("log")
        # Explicit tick locations: 0.1, 0.5, 1, 5, 10, 20, 30 cents.
        ticks = [0.1, 0.5, 1, 5, 10, 20, 30]
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        # `g` format drops trailing zeros: 1.0 → "1", 0.5 stays "0.5".
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"{x:g}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
    else:
        ax.set_xlim(
            -0.05,
            max((r["cost_usd"] * 100.0 for r in filtered), default=30.0) * 1.05,
        )
    ax.grid(True, alpha=0.3)

    # Architectural-family legend (colour). Cohort glyphs are described in
    # the caption, not on the figure — the figure stays tidy.
    family_handles = [
        Line2D(
            [0],
            [0],
            color=model_family_color(slug_seed),
            linewidth=0,
            marker="s",
            markersize=7,
            label=label,
        )
        for slug_seed, label in (
            ("claude-opus", "Claude"),
            ("gpt-5", "GPT"),
            ("mistral-large", "Mistral"),
            ("qwen3-max", "Qwen"),
            ("deepseek-v4", "DeepSeek"),
        )
    ]
    ax.legend(handles=family_handles, loc="upper right", fontsize="small")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate Pareto CSV and/or scatter PDF (Experiment 1 only)",
    )
    parser.add_argument("--output", help="Path to write pareto.csv")
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

    rows = build_pareto_rows(metrics, source_by_label=source_by_label)

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
