"""Render the empirical capability transition matrix for §3.

8×8 heatmap: for each ordered pair (i, j) of capability stages, the
fraction of labs where feature i shipped before feature j (conditional on
both being present). White = no lab made that transition; green = all
labs did. N is labelled per cell.

Data source: ``data/capability_timeline.csv``.

Usage:
    uv run python -m aedist.plot_capability_dag \
        --input data/capability_timeline.csv \
        --output slides/inputs/generated/fig_capability_dag.pdf
"""

import argparse
import csv
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    1: "1. Chat LLM",
    2: "2. Browsing",
    3: "3. Code exec.",
    4: "4. Retrieval",
    5: "5. Reasoning",
    6: "6. Tool use",
    7: "7. Deep research",
    8: "8. Multi-agent",
}

N_STAGES = 8


def load_lab_dates(path: Path) -> dict[str, dict[int, date]]:
    lab_dates: dict[str, dict[int, date]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row["date"].strip()
            if raw:
                try:
                    lab_dates[row["lab"]][int(row["stage"])] = date.fromisoformat(raw)
                except ValueError:
                    logger.warning("unparseable date %r — skipping", raw)
    return dict(lab_dates)


def compute_matrix(
    lab_dates: dict[str, dict[int, date]],
) -> tuple[np.ndarray, np.ndarray]:
    stages = range(1, N_STAGES + 1)
    frac = np.full((N_STAGES, N_STAGES), np.nan)
    counts = np.zeros((N_STAGES, N_STAGES), dtype=int)

    for i in stages:
        for j in stages:
            if i == j:
                continue
            n_before: float = 0
            n_total = 0
            for lab in lab_dates:
                if i in lab_dates[lab] and j in lab_dates[lab]:
                    n_total += 1
                    di, dj = lab_dates[lab][i], lab_dates[lab][j]
                    if di < dj:
                        n_before += 1
                    elif di == dj:
                        n_before += 0.5  # tie: split evenly so (i,j)+(j,i)=100%
            counts[i - 1, j - 1] = n_total
            if n_total >= 2:
                frac[i - 1, j - 1] = n_before / n_total
    return frac, counts


def render(lab_dates: dict[str, dict[int, date]], output: Path) -> None:
    frac, counts = compute_matrix(lab_dates)

    fig, ax = plt.subplots(figsize=(6.5, 5.5))

    masked = np.ma.masked_invalid(frac)
    ax.imshow(masked, cmap=plt.cm.Greens, vmin=0.0, vmax=1.0, aspect="equal", origin="upper")

    for i in range(N_STAGES):
        for j in range(N_STAGES):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color="gray")
                continue
            n = counts[i, j]
            if n < 2:
                ax.text(j, i, f"N={n}", ha="center", va="center", fontsize=6, color="gray")
                continue
            f = frac[i, j]
            text_color = "white" if f > 0.75 else "black"
            label = f"{f:.0%}\nN={n}" if f > 0 else f"N={n}"
            ax.text(j, i, label, ha="center", va="center", fontsize=6, color=text_color)

    labels = [FEATURE_LABELS[s] for s in range(1, N_STAGES + 1)]
    ax.set_xticks(range(N_STAGES))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(N_STAGES))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Feature j (column)", fontsize=8)
    ax.set_ylabel("Feature i (row)", fontsize=8)
    ax.set_title("Fraction of labs where feature i shipped before feature j", fontsize=9, pad=8)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    logger.info("wrote %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/capability_timeline.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("slides/inputs/generated/fig_capability_dag.pdf"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    lab_dates = load_lab_dates(args.input)
    render(lab_dates, args.output)


if __name__ == "__main__":
    main()
