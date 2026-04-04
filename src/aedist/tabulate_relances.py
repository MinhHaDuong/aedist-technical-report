"""Generate multi-turn relances LaTeX table from all_metrics.json.

Usage:
    python -m aedist.tabulate_relances \\
        --input results/summary/all_metrics.json \\
        --output report/inputs/generated/tab_relances.tex

Reads per-run metrics from sweep2_multiturn, groups by model (stripping
-runN suffix), computes medians, and emits a longtable showing how F1
progresses across turns for each model.

If per-turn metrics are not available in all_metrics.json (i.e. no
``turn`` field), falls back to a single-column summary table showing
final multiturn F1 per model.
"""

import argparse
import json
import logging
import statistics
from pathlib import Path

from .tabulate_utils import format_model_name, strip_label

log = logging.getLogger(__name__)

_MULTITURN_PREFIX = "sweep2_multiturn/"


def is_multiturn(entry: dict) -> bool:
    """True if metrics entry comes from a multiturn sweep."""
    return entry.get("label", "").startswith(_MULTITURN_PREFIX)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _has_turn_data(entries: list[dict]) -> bool:
    """Check if any entry carries a 'turn' field for per-turn breakdown."""
    return any("turn" in e for e in entries)


def group_by_model_and_turn(metrics: list[dict]) -> dict[str, dict[int, list[dict]]]:
    """Group multiturn metrics by model slug and turn number.

    Returns {slug: {turn: [entries]}}.
    """
    result: dict[str, dict[int, list[dict]]] = {}
    for entry in metrics:
        if not is_multiturn(entry):
            continue
        slug = strip_label(entry["label"])
        turn = entry.get("turn", -1)
        result.setdefault(slug, {}).setdefault(turn, []).append(entry)
    return result


def group_final_only(metrics: list[dict]) -> list[dict]:
    """Group multiturn metrics by model slug (final results only).

    Returns a list of dicts sorted by median F1 descending.
    """
    groups: dict[str, list[dict]] = {}
    for entry in metrics:
        if not is_multiturn(entry):
            continue
        slug = strip_label(entry["label"])
        groups.setdefault(slug, []).append(entry)

    rows = []
    for slug, entries in groups.items():
        rows.append({
            "slug": slug,
            "local": slug.startswith("padme-"),
            "f1": statistics.median(e["f1"] for e in entries),
            "precision": statistics.median(e["precision"] for e in entries),
            "coverage": statistics.median(e["coverage"] for e in entries),
            "n_matched": int(statistics.median(e["n_matched"] for e in entries)),
            "n_reference": entries[0]["n_reference"],
        })

    rows.sort(key=lambda r: r["f1"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


def _generate_per_turn_table(metrics: list[dict]) -> str:
    """Generate table with columns for each turn (Prompt, Relance 1-3)."""
    grouped = group_by_model_and_turn(metrics)

    # Discover all turn numbers
    all_turns: set[int] = set()
    for turns_dict in grouped.values():
        all_turns.update(turns_dict.keys())
    turn_list = sorted(all_turns)

    # Build column headers
    turn_headers = []
    for t in turn_list:
        if t == 0:
            turn_headers.append("Prompt")
        else:
            turn_headers.append(f"Relance {t}")

    n_cols = 1 + len(turn_list)  # Model + turns
    col_spec = "@{}l" + "r" * len(turn_list) + "@{}"

    lines = [
        "% Auto-generated — do not edit",
        f"\\begin{{longtable}}[]{{{col_spec}}}",
        "\\caption{Multi-turn relances: matched plants per turn"
        " (median of 3 runs)}\\label{tab:relances}\\\\",
        "\\toprule",
        "Model & " + " & ".join(turn_headers) + " \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    # Sort models by final-turn F1
    def final_f1(slug: str) -> float:
        last_turn = max(grouped[slug].keys())
        entries = grouped[slug][last_turn]
        return statistics.median(e["f1"] for e in entries)

    slugs = sorted(grouped.keys(), key=final_f1, reverse=True)

    for slug in slugs:
        name = format_model_name(slug)
        cells = [name]
        for t in turn_list:
            entries = grouped[slug].get(t, [])
            if entries:
                matched = int(statistics.median(e["n_matched"] for e in entries))
                ref = entries[0]["n_reference"]
                cells.append(f"{matched}/{ref}")
            else:
                cells.append("--")
        lines.append(" & ".join(cells) + " \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


def _generate_summary_table(metrics: list[dict]) -> str:
    """Fallback: summary table when per-turn data is not available."""
    rows = group_final_only(metrics)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Multi-turn relances: F1 scores"
        " (median of 3 runs)}\\label{tab:relances}\\\\",
        "\\toprule",
        "Model & F1 & Precision & Recall & Matched \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1 = f'{row["f1"] * 100:.1f}\\%'
        prec = f'{row["precision"] * 100:.1f}\\%'
        recall = f'{row["coverage"] * 100:.1f}\\%'
        matched = f'{row["n_matched"]}/{row["n_reference"]}'
        lines.append(f"{name} & {f1} & {prec} & {recall} & {matched} \\\\")

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


def generate_relances_table(metrics: list[dict]) -> str:
    """Generate a LaTeX longtable for multi-turn relances results.

    If per-turn metrics (``turn`` field) are available, produces a table
    showing plant count progression across turns.  Otherwise falls back
    to a single-column summary.
    """
    mt_entries = [e for e in metrics if is_multiturn(e)]
    if not mt_entries:
        log.warning("No sweep2_multiturn entries found in metrics.")
        return _generate_summary_table(metrics)

    if _has_turn_data(mt_entries):
        return _generate_per_turn_table(metrics)
    return _generate_summary_table(metrics)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate multi-turn relances LaTeX table",
    )
    parser.add_argument("--input", required=True, help="Path to all_metrics.json")
    parser.add_argument("--output", required=True, help="Path to write tab_relances.tex")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path) as f:
        metrics = json.load(f)

    latex = generate_relances_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)

    mt_count = len([e for e in metrics if is_multiturn(e)])
    log.info("Wrote %s (%d multiturn entries)", output_path, mt_count)


if __name__ == "__main__":
    main()
