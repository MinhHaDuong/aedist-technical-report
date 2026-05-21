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

x-axis scale: controlled by ``--xscale {linear,log}`` (default log).
For log mode, models reporting ``cost_usd <= 0`` are dropped with a
warning — clamping to an ε or pinning to a dedicated "\\$0" tick would
mis-represent the scale. All Experiment 1 models are cloud and carry
non-zero costs, so this branch does not fire on current data; it
becomes relevant when the script is reused for Experiments 2/3.

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

P1_BASE_PATH_PREFIX = "experiments/outputs/ablation/direct/p1_base/"
P1_PILOT_MARKER = "/p1_base.pilot/"

# Vietnam thermal reference inventory size (Annex A, line 72).
N_REFERENCE_PLANTS = 163


def _is_p1_base_row(result_file: str) -> bool:
    """Return True for direct-baseline rows (Experiment 1), excluding pilots."""
    return result_file.startswith(P1_BASE_PATH_PREFIX) and P1_PILOT_MARKER not in result_file


def build_pareto_rows(metrics: list[dict]) -> list[dict]:
    """Build rows for the Pareto chart.

    Returns list of dicts with keys: model, family, median_tp, min_tp,
    max_tp, median_f1, min_f1, max_f1, cost_usd.  Sorted by median_tp
    descending — the plotted axis.

    Per-model statistics are computed across the rep distribution in
    *metrics*: median / min / max for both correctly-identified plant
    counts (``n_matched``) and row-level F1; mean cost per call. The
    caller is responsible for pre-filtering *metrics* to the desired
    scope (e.g. Experiment 1 rows only via ``_is_p1_base_row``).
    """
    import statistics

    tp_by_model: dict[str, list[int]] = {}
    f1_by_model: dict[str, list[float]] = {}
    cost_by_model: dict[str, list[float]] = {}

    for entry in metrics:
        slug = slug_from_label(entry["label"])
        tp = entry.get("n_matched")
        if tp is not None:
            tp_by_model.setdefault(slug, []).append(int(tp))
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

    Each model is rendered as one point at its median TP count with
    whiskers spanning min/max across the 5 reps. Colour conveys the
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
        lo = median - r["min_tp"]
        hi = r["max_tp"] - median
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

    # Reference line at the full inventory size.
    ax.axhline(
        N_REFERENCE_PLANTS,
        color=COLOR_REFERENCE,
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        zorder=1,
    )

    ax.set_xlabel("Coût par requête (USD)")
    ax.set_ylabel("Nombre de centrales bien identifiées")
    ax.set_ylim(0, N_REFERENCE_PLANTS * 1.05)
    if xscale == "log":
        ax.set_xscale("log")
    else:
        ax.set_xlim(-0.005, max((r["cost_usd"] for r in filtered), default=0.30) * 1.05)
    ax.grid(True, alpha=0.3)

    # Architectural-family legend — order matches Exp 1 lineup density.
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=model_family_color(slug_seed),
            linewidth=0,
            marker="o",
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
        default="log",
        help="x-axis scale for the figure (default: log). "
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
            )
            writer.writeheader()
            writer.writerows(rows)
        log.info("Wrote %d rows to %s", len(rows), output_path)

    if args.figure:
        write_pdf(rows, Path(args.figure), xscale=args.xscale)


if __name__ == "__main__":
    main()
