"""Generate method-convergence strip plot from measurements.jsonl.

For each method (Y axis), plots every run as a horizontal bar.
Each bar is a row of dots: 1 dot = 1 plant.
Blue dots = correctly identified (TP). Orange dots = hallucinated (FP).
Dashed green line at 163 = complete inventory.

A good method drives all bars to 163 with nothing in orange.

Usage:
    uv run python -m aedist.plot_method_convergence \
        --output slides/inputs/generated/fig_method_convergence.pdf
"""

import argparse
import csv
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

from .measurements import SYNTHETIC_SUFFIXES, load
from .util import (
    COLOR_HALLUC,
    COLOR_REFERENCE,
    model_family,
    model_family_color,
    normalize_model,
)

_SIZE_CLASS_B = {"edge": 4, "small": 9, "medium": 30, "large": 100, "frontier": 300}

# Confirmed total parameter counts (B) from official sources / tech reports.
# MoE: total params (not active). Undisclosed models fall back to _SIZE_CLASS_B.
_KNOWN_SIZE_B: dict[str, float] = {
    "deepseek-v3.2": 671,  # 671B MoE, 37B active
    "devstral-small-2": 24,  # dense
    "glm-4.7-flash": 30,  # 30B MoE, 3B active
    "glm-5-turbo": 745,  # 745B MoE, 44B active
    "kimi-k2.5": 1000,  # 1T MoE, 32B active
    "llama-4-maverick": 400,  # 400B MoE, 17B active
    "mimo-v2-flash": 309,  # 309B MoE, 15B active
    "mimo-v2-pro": 1000,  # ~1T MoE, 42B active
    "minimax-m2.7": 230,  # 230B MoE, 10B active
    "mistral-large-2512": 675,  # 675B MoE, 41B active (Mistral Large 3)
    "mistral-medium-3-5": 200,  # undisclosed; rough estimate to place between Small (119) and Large (675)
    "mistral-small-2603": 119,  # 119B MoE, 6.5B active (Mistral Small 4 — NOT 24B dense)
    "mistral-small3.2": 24,  # dense
    "nemotron-3-nano": 30,  # 30B MoE, 3B active
    "qwen3.5-plus-02-15": 397,  # 397B MoE, 17B active
    "step-3.5-flash": 196,  # 196B MoE, 11B active
}


def _model_size_b(model: str, size_class: str | None = None) -> float:
    """Effective parameter count in billions for sorting (nano → hexascale).

    Priority: confirmed registry → regex on name → size_class fallback.
    """
    if model in _KNOWN_SIZE_B:
        return _KNOWN_SIZE_B[model]
    matches = re.findall(r"(\d+(?:\.\d+)?)b", model.lower())
    if matches:
        return max(float(m) for m in matches)
    return float(_SIZE_CLASS_B.get(size_class or "", 500))


log = logging.getLogger(__name__)

# Methods to include and display order (bottom to top in plot).
# New vocabulary (ticket 0120): direct, direct+multiturn, rag_livesearch, rag.
# "rag" covers both pure-RAG and decomposed (per_fuel) runs; filter by
# prompt_version if you need to distinguish them.
_METHOD_ORDER = ["direct", "direct+multiturn", "rag_livesearch", "rag"]

# Display names for Y-axis labels
_METHOD_LABELS = {
    "direct": "Single",
    "direct+multiturn": "Multi-turn",
    "rag_livesearch": "Web",
    "rag": "RAG",
}


def load_convergence_data(
    prompt_version: str | None = None,
    result_dir: str | None = None,
) -> list[dict]:
    """Load and clean measurements for the convergence plot.

    Returns list of dicts with keys: method, model, tp, fp, fn.
    prompt_version: if set, only records with that prompt_version are included.
    result_dir: if set, only records whose result_file starts with this prefix.
    """
    rows = []
    for record in load():
        method = record.method.value
        if method not in _METHOD_ORDER:
            continue
        if prompt_version is not None:
            pv = getattr(record.method_params, "prompt_version", None)
            if pv != prompt_version:
                continue
        if result_dir is not None:
            rf = record.result_file or ""
            if not rf.startswith(result_dir):
                continue
        model = normalize_model(record.method_params.model)
        if any(model.endswith(s) for s in SYNTHETIC_SUFFIXES):
            continue
        s = record.result_summary
        if s.tp is None:
            continue
        ex = record.method_params.extra or {}
        rows.append(
            {
                "method": method,
                "model": model,
                "tp": s.tp or 0,
                "fp": s.fp or 0,
                "fn": s.fn or 0,
                "local": ex.get("provider") == "Ollama/Padme",
                "size_class": ex.get("size_class", ""),
            }
        )
    return rows


def core_models(rows: list[dict]) -> set[str]:
    """Find models that appear in all methods."""
    model_methods: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        model_methods[r["model"]].add(r["method"])
    all_methods = set(_METHOD_ORDER)
    return {m for m, methods in model_methods.items() if methods >= all_methods}


def write_csv(rows: list[dict], output: Path) -> None:
    """Write convergence data as CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["method", "model", "tp", "fp", "fn", "local", "size_class"]
        )
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), output)


def write_pdf(
    rows: list[dict],
    output: Path,
    models: set[str] | None = None,
    max_runs_per_model: int = 3,
    max_fp: int = 80,
    method_order: list[str] | None = None,
) -> None:
    """Generate the method convergence strip plot as PDF.

    Each run becomes a thin horizontal line: blue segment from 0 to TP,
    orange segment from 0 to -FP. Within each method band, runs are
    stacked vertically and sorted by TP descending.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    order = method_order or _METHOD_ORDER
    spacing = 0.08
    gap = 0.5

    # Auto-size height based on actual row count
    total_runs = 0
    for method in order:
        method_rows = [r for r in rows if r["method"] == method]
        if models:
            method_rows = [r for r in method_rows if r["model"] in models]
        model_count: Counter[str] = Counter()
        for r in method_rows:
            if model_count[r["model"]] < max_runs_per_model:
                model_count[r["model"]] += 1
        total_runs += sum(model_count.values())
    fig_height = max(4.2, 0.08 * total_runs + 0.5 * len(order))

    fig, ax = plt.subplots(figsize=(10, fig_height))

    y_offset = 0.0
    y_last = 0.0
    method_ticks = []

    for method in order:
        method_rows = [r for r in rows if r["method"] == method]
        if models:
            method_rows = [r for r in method_rows if r["model"] in models]
        if not method_rows:
            continue

        # Limit runs per model
        model_count = Counter()
        filtered = []
        for r in method_rows:
            if model_count[r["model"]] < max_runs_per_model:
                filtered.append(r)
                model_count[r["model"]] += 1
        method_rows = filtered

        # Resolve size per model (not per record). Different reps of the same
        # model can carry different size_class values in the data — take the
        # minimum so that any real registry match (or named size_class) wins
        # over the 500 default fallback when size_class is "unknown".
        model_size: dict[str, float] = {}
        for r in method_rows:
            sz = _model_size_b(r["model"], r.get("size_class"))
            model_size[r["model"]] = min(sz, model_size.get(r["model"], sz))

        # Group by architectural family (alphabetical); within family, larger
        # models go first so they land higher on the inverted Y axis.
        method_rows.sort(
            key=lambda r: (
                model_family(r["model"]),
                -model_size[r["model"]],
                r["model"],
                -r["tp"],
            )
        )

        band_start = y_offset
        model_ys: dict[str, list[float]] = {}
        model_local: dict[str, bool] = {}
        for i, run in enumerate(method_rows):
            y = y_offset + i * spacing
            y_last = y
            model_ys.setdefault(run["model"], []).append(y)
            model_local[run["model"]] = run.get("local", False)
            tp = run["tp"]
            fp_raw = run["fp"]
            fp = min(fp_raw, max_fp)

            color = model_family_color(run["model"])

            # TP dots (right of 0) — 1 dot = 1 plant
            if tp > 0:
                xs = np.arange(1, tp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(xs, ys, s=4, color=color, marker="|", linewidths=0.5, zorder=3)

            # FP dots (left of 0) — 1 dot = 1 hallucinated plant
            if fp > 0:
                xs = -np.arange(1, fp + 1)
                ys = np.full_like(xs, y, dtype=float)
                ax.scatter(xs, ys, s=4, color=color, marker="|", linewidths=0.5, zorder=3)
                if fp_raw > max_fp:
                    ax.text(
                        -fp - 1,
                        y,
                        f"({fp_raw})",
                        fontsize=5,
                        color=color,
                        va="center",
                        ha="right",
                    )

        # Model name labels at x=-5, right-aligned, centered on each model's runs
        for model, ys in model_ys.items():
            y_mid = sum(ys) / len(ys)
            label = f"{model} (local)" if model_local.get(model) else model
            ax.text(
                -5,
                y_mid,
                label,
                ha="right",
                va="center",
                fontsize=13.5,
                color=model_family_color(model),
            )

        band_center = band_start + (len(method_rows) - 1) * spacing / 2
        method_ticks.append((band_center, _METHOD_LABELS.get(method, method)))
        y_offset += len(method_rows) * spacing + gap

    # Reference line at 163
    ax.axvline(x=163, color=COLOR_REFERENCE, linewidth=1, linestyle="--", alpha=0.7, zorder=2)

    # Zero line
    ax.axvline(x=0, color="black", linewidth=0.5, alpha=0.4, zorder=1)

    ax.set_yticks([])
    ax.set_xlabel("Number of power plants", fontsize=11)
    ax.set_xlim(-max_fp - 15, 185)
    # Invert via ylim order (no invert_yaxis) so set_ylim stays predictable
    ax.set_ylim(y_last + spacing, -spacing)
    ax.grid(axis="x", linewidth=0.2, alpha=0.3)
    ax.set_axisbelow(True)

    # Labels at graph level (data coordinates)
    y_top = -spacing * 0.5
    ax.text(
        163,
        y_top,
        "163\nplants",
        color=COLOR_REFERENCE,
        fontsize=16,
        va="bottom",
        ha="center",
    )
    ax.text(
        -75, y_top, "Hallucinations", color=COLOR_HALLUC, fontsize=16, va="bottom", ha="center"
    )
    ax.tick_params(axis="x", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", dpi=300)
    plt.close(fig)
    log.info("Wrote %s", output)


def _build_macros(
    rows: list[dict],
    *,
    prompt_version: str | None = None,
    result_dir: str | None = None,
) -> str:
    n_models = len({r["model"] for r in rows})
    tps = [r["tp"] for r in rows]
    fps = [r["fp"] for r in rows]
    lines = [
        "% Auto-generated by aedist.plot_method_convergence — do not edit",
        f"\\newcommand{{\\NumCensusModels}}{{{n_models}}}",
        f"\\newcommand{{\\CensusTPMin}}{{{min(tps)}}}",
        f"\\newcommand{{\\CensusTPMax}}{{{max(tps)}}}",
        f"\\newcommand{{\\CensusFPMin}}{{{min(fps)}}}",
        f"\\newcommand{{\\CensusFPMax}}{{{max(fps)}}}",
    ]
    if prompt_version is not None or result_dir is not None:
        raw = load()
        subset = []
        for r in raw:
            if prompt_version is not None:
                pv = getattr(r.method_params, "prompt_version", None)
                if pv != prompt_version:
                    continue
            if result_dir is not None and not (r.result_file or "").startswith(result_dir):
                continue
            if any(normalize_model(r.method_params.model).endswith(s) for s in SYNTHETIC_SUFFIXES):
                continue
            subset.append(r)
        lines.append(f"\\newcommand{{\\CensusNumRuns}}{{{len(subset)}}}")
        n_ok = sum(1 for r in subset if (r.result_summary.status or "ok") == "ok")
        n_refusal = sum(1 for r in subset if (r.result_summary.status or "ok") == "refusal")
        costs = [r.resource_use.cost_usd for r in subset if r.resource_use.cost_usd]
        walls = [r.resource_use.wall_s for r in subset if r.resource_use.wall_s]
        lines.append(f"\\newcommand{{\\CensusNumOk}}{{{n_ok}}}")
        lines.append(f"\\newcommand{{\\CensusNumRefusal}}{{{n_refusal}}}")
        if costs:
            lines.append(f"\\newcommand{{\\CensusCostTotal}}{{{sum(costs):.2f}}}")
            lines.append(f"\\newcommand{{\\CensusCostMin}}{{{min(costs):.4f}}}")
            lines.append(f"\\newcommand{{\\CensusCostMax}}{{{max(costs):.4f}}}")
        if walls:
            lines.append(f"\\newcommand{{\\CensusWallMin}}{{{min(walls):.0f}}}")
            lines.append(f"\\newcommand{{\\CensusWallMax}}{{{max(walls):.0f}}}")
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate method-convergence strip plot",
    )
    parser.add_argument("--output", required=True, help="Path to write PDF or CSV")
    parser.add_argument(
        "--csv", default=None, help="Also write run-level CSV (for data inspection)"
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only models tested under all methods",
    )
    parser.add_argument(
        "--methods",
        default=None,
        help="Comma-separated list of methods to include (default: all)",
    )
    parser.add_argument(
        "--prompt-version",
        default=None,
        help="Filter to a single prompt_version (e.g. census, p1_base)",
    )
    parser.add_argument(
        "--output-macros",
        default=None,
        help="Write \\NumCensusModels macro to this .tex file",
    )
    parser.add_argument(
        "--result-dir",
        default=None,
        help="Only include records whose result_file starts with this prefix",
    )
    args = parser.parse_args()

    rows = load_convergence_data(prompt_version=args.prompt_version, result_dir=args.result_dir)
    models = core_models(rows) if args.core_only else None

    if args.methods:
        requested = [m.strip() for m in args.methods.split(",")]
        method_order = [m for m in _METHOD_ORDER if m in requested]
    else:
        method_order = None

    output = Path(args.output)
    if output.suffix == ".pdf":
        write_pdf(rows, output, models=models, method_order=method_order)
    else:
        write_csv(rows, output)

    if args.csv:
        write_csv(rows, Path(args.csv))

    if args.output_macros:
        macros_path = Path(args.output_macros)
        macros_path.parent.mkdir(parents=True, exist_ok=True)
        macros_path.write_text(
            _build_macros(
                rows,
                prompt_version=args.prompt_version,
                result_dir=args.result_dir,
            )
        )
        log.info("Wrote %s", macros_path)


if __name__ == "__main__":
    main()
