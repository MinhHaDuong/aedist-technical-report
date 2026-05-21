"""Generate Pareto-front CSV and scatter PDF from measurements.jsonl.

Scope: **Experiment 1 only** (the parametric baseline sweep,
``experiments/outputs/ablation/direct/p1_base/``). Pilot rows under
``p1_base.pilot/`` are excluded. The figure does not draw a frontier
envelope — points are plotted as median F1 with min/max whiskers across
the 5 reps per model.

Writes a CSV with columns: model, median_f1, min_f1, max_f1, cost_usd
sorted by median F1 descending. Optionally writes a PDF scatter plot.

Family colouring: per-model colour comes from ``aedist.util.family_color()``
(palette.toml, language-family axis). Three families today: EN / FR / ZH.
The figure carries a single marker per model; the colour conveys family.

x-axis scale: controlled by ``--xscale {linear,log}`` (default linear).
For log mode, models reporting ``cost_usd <= 0`` are dropped with a
warning — clamping to an ε or pinning to a dedicated "\\$0" tick would
mis-represent the scale. All Experiment 1 models are cloud and carry
non-zero costs, so this branch does not fire on current data; it
becomes relevant when the script is reused for Experiments 2/3.

Usage::

    uv run python -m aedist.plot_pareto \\
        --output slides/inputs/generated/pareto.csv \\
        --figure slides/inputs/generated/fig_pareto.pdf \\
        --xscale linear
"""

import argparse
import csv
import logging
from pathlib import Path

from .tabulate_utils import strip_label as slug_from_label
from .util import family_color

log = logging.getLogger(__name__)

P1_BASE_PATH_PREFIX = "experiments/outputs/ablation/direct/p1_base/"
P1_PILOT_MARKER = "/p1_base.pilot/"


def _is_p1_base_row(result_file: str) -> bool:
    """Return True for direct-baseline rows (Experiment 1), excluding pilots."""
    return result_file.startswith(P1_BASE_PATH_PREFIX) and P1_PILOT_MARKER not in result_file


def build_pareto_rows(metrics: list[dict]) -> list[dict]:
    """Build rows for the Pareto chart.

    Returns list of dicts with keys: model, median_f1, min_f1, max_f1, cost_usd.
    Sorted by median_f1 descending.

    Per-model statistics are computed across the rep distribution in *metrics*:
    median F1, min F1, max F1, mean cost. The caller is responsible for
    pre-filtering *metrics* to the desired scope (e.g. Experiment 1 rows
    only via ``_is_p1_base_row``).
    """
    import statistics

    f1_by_model: dict[str, list[float]] = {}
    cost_by_model: dict[str, list[float]] = {}

    for entry in metrics:
        slug = slug_from_label(entry["label"])
        f1 = entry.get("f1")
        if f1 is not None:
            f1_by_model.setdefault(slug, []).append(f1)
        cost = entry.get("cost_usd")
        if cost is not None and cost > 0:
            cost_by_model.setdefault(slug, []).append(cost)

    rows = []
    for slug, f1_values in f1_by_model.items():
        costs = cost_by_model.get(slug, [])
        rows.append(
            {
                "model": slug,
                "median_f1": round(statistics.median(f1_values), 4),
                "min_f1": round(min(f1_values), 4),
                "max_f1": round(max(f1_values), 4),
                "cost_usd": round(sum(costs) / len(costs), 6) if costs else 0.0,
            }
        )
    rows.sort(key=lambda r: r["median_f1"], reverse=True)
    return rows


def write_pdf(rows: list[dict], output: Path, xscale: str = "linear") -> None:
    """Write a Pareto scatter plot (F1 vs cost) to *output* as PDF.

    Each model is rendered as one point at its median F1 with whiskers
    spanning min/max across the 5 reps. Colour conveys language family
    via :func:`aedist.util.family_color`. ``xscale`` accepts ``"linear"``
    or ``"log"``; log mode drops zero-cost models with a warning.
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
        colour = family_color(r["model"])
        median = r["median_f1"]
        lo = median - r["min_f1"]
        hi = r["max_f1"] - median
        ax.errorbar(
            [r["cost_usd"]],
            [median],
            yerr=[[lo], [hi]],
            fmt="o",
            color=colour,
            ecolor=colour,
            elinewidth=1.0,
            capsize=3,
            markersize=6,
            zorder=3,
        )

    ax.set_xlabel("Coût par requête (USD)")
    ax.set_ylabel("F1 (niveau ligne)")
    ax.set_ylim(0, 1.0)
    if xscale == "log":
        ax.set_xscale("log")
    else:
        ax.set_xlim(-0.005, max((r["cost_usd"] for r in filtered), default=0.30) * 1.05)
    ax.grid(True, alpha=0.3)

    # Language-family legend (EN/FR/ZH) — colour-only entries; marker
    # carries no extra information.
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=family_color(code),
            linewidth=0,
            marker="o",
            markersize=7,
            label=label,
        )
        for code, label in (
            ("EN", "EN — Anthropic / OpenAI"),
            ("FR", "FR — Mistral"),
            ("ZH", "ZH — Alibaba / DeepSeek"),
        )
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize="small")

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
        default="linear",
        help="x-axis scale for the figure (default: linear). "
        "Log mode drops zero-cost models with a warning.",
    )
    args = parser.parse_args()

    if not args.output and not args.figure:
        parser.error("at least one of --output or --figure is required")

    from .measurements import load, records_to_metrics

    # Filter at the boundary: Experiment 1 == direct/p1_base/ (no pilots).
    records = [r for r in load() if r.result_file and _is_p1_base_row(r.result_file)]
    metrics = records_to_metrics(records)
    rows = build_pareto_rows(metrics)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["model", "median_f1", "min_f1", "max_f1", "cost_usd"]
            )
            writer.writeheader()
            writer.writerows(rows)
        log.info("Wrote %d rows to %s", len(rows), output_path)

    if args.figure:
        write_pdf(rows, Path(args.figure), xscale=args.xscale)


if __name__ == "__main__":
    main()
