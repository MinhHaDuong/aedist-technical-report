"""Generate the cost × quality scatter PDF from measurements.jsonl.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Figure script only: it emits the PDF. The per-model summary it plots is
derived by the shared :mod:`aedist.exp1_cost_quality` library; the audit CSV
that companions this figure is written by :mod:`aedist.tabulate_cost_quality`,
not by this script (ticket 0436 — figures emit figures only, no side-output
another rule consumes).

Scope: **Experiment 1 only** (the parametric baseline sweep,
``experiments/outputs/ablation/direct/p1_base/``). Pilot rows under
``p1_base.pilot/`` are excluded. The figure is descriptive — no
Pareto-efficient envelope is drawn.

Y axis: per-model **count of correctly identified plants** (true positives,
``n_matched`` in measurements) plotted as median with min/max whiskers
across the 5 reps. A horizontal reference line marks the full reference
inventory size (reference_plant_count() thermal plants).

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
        --figure report/inputs/generated/fig_direct_cost_quality.pdf \\
        --xscale log
"""

import argparse
import logging
from pathlib import Path

from .exp1_cost_quality import N_REFERENCE_PLANTS, load_cost_quality_rows
from .util import (
    COLOR_REFERENCE,
    SLIDE_FIGSIZE_WIDE,
    glyph_for_method,
    glyph_scatter_kwargs,
    model_family_color,
)

log = logging.getLogger(__name__)


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
        description="Generate the cost × quality scatter PDF (Experiment 1 only)",
    )
    parser.add_argument("--figure", required=True, help="Path to write scatter PDF")
    parser.add_argument(
        "--xscale",
        choices=("linear", "log"),
        default="log",
        help="x-axis scale for the figure (default: log). "
        "Log mode drops zero-cost models with a warning.",
    )
    args = parser.parse_args()

    rows = load_cost_quality_rows()
    write_pdf(rows, Path(args.figure), xscale=args.xscale)


if __name__ == "__main__":
    main()
