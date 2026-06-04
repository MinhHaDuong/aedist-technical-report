"""Generate multi-turn relances LaTeX table from measurements.jsonl.

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Usage:
    python -m aedist.tabulate_relances \\
        --measurements measurements.jsonl \\
        --output report/inputs/generated/tab_relances.tex

Reads per-run metrics from multiturn condition, groups by model (stripping
-runN suffix), computes medians, and emits a longtable showing how F1
progresses across turns for each model.

If per-turn metrics are not available in measurements.jsonl (i.e. no
``turn`` field), falls back to a single-column summary table showing
final multiturn F1 per model.
"""

import argparse
import logging
import statistics
from pathlib import Path

from .tabulate_utils import format_model_name, group_and_summarize, strip_label

log = logging.getLogger(__name__)

_MULTITURN_PREFIX = "multiturn/"


def is_multiturn(entry: dict) -> bool:
    """True if metrics entry comes from the multiturn condition."""
    return entry.get("label", "").startswith(_MULTITURN_PREFIX)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _has_turn_data(entries: list[dict]) -> bool:
    """Check if any entry carries a 'turn' field for per-turn breakdown."""
    return any("turn" in e for e in entries)


def group_by_model_and_turn(mt_entries: list[dict]) -> dict[str, dict[int, list[dict]]]:
    """Group multiturn metrics by model slug and turn number.

    Entries without a ``turn`` field are skipped (they lack per-turn data).

    Args:
        mt_entries: Pre-filtered list of multiturn metric entries.

    Returns {slug: {turn: [entries]}}.
    """
    result: dict[str, dict[int, list[dict]]] = {}
    for entry in mt_entries:
        if "turn" not in entry:
            continue
        slug = strip_label(entry["label"])
        turn = entry["turn"]
        result.setdefault(slug, {}).setdefault(turn, []).append(entry)
    return result


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


def _generate_per_turn_table(mt_entries: list[dict]) -> str:
    """Generate table with columns for each turn (Prompt, Relance 1-3)."""
    grouped = group_by_model_and_turn(mt_entries)

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


def _generate_summary_table(mt_entries: list[dict]) -> str:
    """Fallback: summary table when per-turn data is not available."""
    rows = group_and_summarize(mt_entries)

    lines = [
        "% Auto-generated — do not edit",
        "\\begin{longtable}[]{@{}lrrrr@{}}",
        "\\caption{Multi-turn relances: F1 scores (median of 3 runs)}\\label{tab:relances}\\\\",
        "\\toprule",
        "Model & F1 & Precision & Recall & Matched \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    for row in rows:
        name = format_model_name(row["slug"])
        f1 = f"{row['f1'] * 100:.1f}\\%"
        prec = f"{row['precision'] * 100:.1f}\\%"
        recall = f"{row['coverage'] * 100:.1f}\\%"
        matched = f"{row['n_matched']}/{row['n_reference']}"
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
        log.warning("No multiturn entries found in metrics.")
        return _generate_summary_table([])

    if _has_turn_data(mt_entries):
        return _generate_per_turn_table(mt_entries)
    return _generate_summary_table(mt_entries)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate multi-turn relances LaTeX table",
    )
    parser.add_argument("--output", required=True, help="Path to write tab_relances.tex")
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    from .measurements import load_metrics

    metrics = load_metrics()

    latex = generate_relances_table(metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
