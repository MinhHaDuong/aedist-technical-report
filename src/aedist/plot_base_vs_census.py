"""Scatter plot comparing F1 on the census prompt vs the p1_base prompt.

One point per model (intersection of both arms), with the y=x diagonal drawn
and point area proportional to ``log(Δtokens_in + 1)``.  Ticket 0057.
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

from .tabulate_base_vs_census import compute_table
from .tabulate_utils import format_model_name

log = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path("report/inputs/generated/fig_base_vs_census.pdf")
_DEFAULT_P1_BASE_DIR = Path("experiments/outputs/ablation/direct/p1_base")


def _make_figure(table: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = table["rows"]
    if not rows:
        msg = "plot_base_vs_census: no models in intersection — refusing to plot"
        raise SystemExit(msg)

    xs = [row["f1_census"] for row in rows]
    ys = [row["f1_base"] for row in rows]
    sizes = [80 + 60 * math.log1p(max(row["delta_tokens_in"], 0.0)) for row in rows]
    labels = [format_model_name(row["slug"]) for row in rows]

    fig, ax = plt.subplots(figsize=(5.5, 5.0))
    ax.scatter(xs, ys, s=sizes, alpha=0.7, edgecolor="black", linewidth=0.5, zorder=3)

    lo = min([*xs, *ys, 0.0])
    hi = max([*xs, *ys, 1.0])
    pad = 0.02
    ax.plot(
        [lo - pad, hi + pad],
        [lo - pad, hi + pad],
        linestyle="--",
        color="gray",
        linewidth=1,
        zorder=1,
        label="y = x",
    )

    for x, y, name in zip(xs, ys, labels, strict=True):
        ax.annotate(
            name,
            (x, y),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_xlabel("F1 — prompt census (40 mots)")
    ax.set_ylabel("F1 — prompt base (300 mots, structuré)")
    ax.set_title("Base vs census: F1 par modèle (taille $\\propto \\log \\Delta$tok$_\\text{in}$)")
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Scatter plot: base F1 vs census F1")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--p1-base-dir", type=Path, default=_DEFAULT_P1_BASE_DIR)
    args = parser.parse_args(argv)

    table = compute_table(p1_base_dir=args.p1_base_dir)
    if table["model_count"] < 2:
        msg = f"plot_base_vs_census: need >=2 models in intersection, got {table['model_count']}"
        raise SystemExit(msg)

    _make_figure(table, args.output)
    log.info("Wrote %s (%d models)", args.output, table["model_count"])


if __name__ == "__main__":
    main()
