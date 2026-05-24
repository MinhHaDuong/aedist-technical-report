"""Render bibliography quality LaTeX table from Exp2 bib quality CSV.

Usage:
    python -m aedist.tabulate_exp2_bib_quality \
        --input report/inputs/generated/tab_exp2_bib_quality_view.csv \
        --output report/inputs/generated/tab_exp2_bib_quality.tex

Reads the flat per-run CSV produced by extract_exp2_bib and generates a
summary table: one row per (agent, arm), showing mean and range across runs.
"""

import argparse
import csv
import logging
import statistics
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_INPUT = Path("report/inputs/generated/tab_exp2_bib_quality_view.csv")

_AGENT_DISPLAY = {
    "anthropic": "Claude",
    "mistral": "Mistral",
    "openai": "GPT",
    "qwen": "Qwen",
}

_AGENT_ORDER = ["anthropic", "openai", "mistral", "qwen"]

_ARM_DISPLAY = {
    "naive": "Naive",
    "optimised": "Optimised",
}

_ARM_ORDER = {"naive": 0, "optimised": 1}


def _int_or_none(val: str) -> int | None:
    """Parse CSV value to int, treating empty string as None."""
    if val == "" or val == "None":
        return None
    return int(val)


def _load_rows(csv_path: Path) -> list[dict]:
    """Load and parse the bib quality CSV."""
    rows = []
    with csv_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            row["run"] = int(row["run"])
            row["n_rows"] = int(row["n_rows"])
            for prefix in ("src1", "src2", "notes"):
                row[f"{prefix}_empty"] = int(row[f"{prefix}_empty"])
                row[f"{prefix}_notfound"] = int(row[f"{prefix}_notfound"])
                row[f"{prefix}_present"] = int(row[f"{prefix}_present"])
            row["src1_valid"] = _int_or_none(row["src1_valid"])
            row["src2_valid"] = _int_or_none(row["src2_valid"])
            row["src1_primary"] = int(row["src1_primary"])
            row["src2_primary"] = int(row["src2_primary"])
            row["bib_entries"] = int(row["bib_entries"])
            row["bib_valid"] = _int_or_none(row["bib_valid"])
            row["bib_primary"] = int(row["bib_primary"])
            rows.append(row)
    return rows


def _fmt_mean_range(values: list[int | float]) -> str:
    """Format as 'mean [min--max]' or just the value if constant."""
    if not values:
        return "--"
    mean = statistics.mean(values)
    lo, hi = min(values), max(values)
    if lo == hi:
        return f"{mean:.0f}"
    return f"{mean:.0f} [{lo:.0f}--{hi:.0f}]"


def _fmt_pct(numerators: list[int], denominators: list[int]) -> str:
    """Format percentage as 'mean%' from paired numerator/denominator lists."""
    pcts = []
    for n, d in zip(numerators, denominators, strict=True):
        pcts.append(100 * n / d if d > 0 else 0.0)
    if not pcts:
        return "--"
    mean = statistics.mean(pcts)
    return f"{mean:.0f}\\%"


def summarize_bib_quality(rows: list[dict]) -> list[dict]:
    """Aggregate per-run rows into per-(agent, arm) summaries."""
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row["agent"], row["arm"])
        grouped.setdefault(key, []).append(row)

    summaries = []
    for (agent, arm), group in grouped.items():
        # Exclude runs with n_rows=0 (empty/degenerate) from means
        valid_runs = [r for r in group if r["n_rows"] > 0]
        n_valid = len(valid_runs)
        n_total = len(group)

        if not valid_runs:
            summaries.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "n_total": n_total,
                    "n_valid": 0,
                    "n_rows": "--",
                    "src1_present_pct": "--",
                    "src2_present_pct": "--",
                    "src1_primary_pct": "--",
                    "notes_present_pct": "--",
                    "bib_entries": "--",
                    "bib_primary": "--",
                }
            )
            continue

        summaries.append(
            {
                "agent": agent,
                "arm": arm,
                "n_total": n_total,
                "n_valid": n_valid,
                "n_rows": _fmt_mean_range([r["n_rows"] for r in valid_runs]),
                "src1_present_pct": _fmt_pct(
                    [r["src1_present"] for r in valid_runs],
                    [r["n_rows"] for r in valid_runs],
                ),
                "src2_present_pct": _fmt_pct(
                    [r["src2_present"] for r in valid_runs],
                    [r["n_rows"] for r in valid_runs],
                ),
                "src1_primary_pct": _fmt_pct(
                    [r["src1_primary"] for r in valid_runs],
                    [r["src1_present"] for r in valid_runs],
                ),
                "notes_present_pct": _fmt_pct(
                    [r["notes_present"] for r in valid_runs],
                    [r["n_rows"] for r in valid_runs],
                ),
                "bib_entries": _fmt_mean_range([r["bib_entries"] for r in valid_runs]),
                "bib_primary": _fmt_mean_range([r["bib_primary"] for r in valid_runs]),
            }
        )

    # Sort by agent order (primary) then arm order (secondary)
    summaries.sort(
        key=lambda r: (
            _AGENT_ORDER.index(r["agent"]) if r["agent"] in _AGENT_ORDER else 99,
            _ARM_ORDER.get(r["arm"], 99),
        )
    )
    return summaries


def generate_latex(summaries: list[dict]) -> str:
    """Render summary rows as a LaTeX longtable (Agent first, Arm second)."""
    lines = [
        "% Auto-generated by tabulate_exp2_bib_quality.py - do not edit",
        "\\begin{longtable}[]{@{}llrrrrrr@{}}",
        "\\caption{Experiment~2: bibliography quality by agent and arm "
        "(mean across valid runs)}\\label{tab:exp2-bib-quality}\\\\",
        "\\toprule",
        "Agent & Arm & Rows & S1 (\\%) & S2 (\\%) & S1 Prim. (\\%) & Notes (\\%) & Bib \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    prev_agent = None
    for row in summaries:
        agent_display = _AGENT_DISPLAY.get(row["agent"], row["agent"].capitalize())
        arm_display = _ARM_DISPLAY.get(row["arm"], row["arm"].replace("-", " ").title())
        valid_note = (
            f" ({row['n_valid']}/{row['n_total']})" if row["n_valid"] < row["n_total"] else ""
        )

        if row["agent"] == prev_agent:
            agent_col = ""
        else:
            if prev_agent is not None:
                lines.append("\\midrule")
            prev_agent = row["agent"]
            agent_col = agent_display

        lines.append(
            f"{agent_col} & {arm_display}{valid_note} & "
            f"{row['n_rows']} & "
            f"{row['src1_present_pct']} & "
            f"{row['src2_present_pct']} & "
            f"{row['src1_primary_pct']} & "
            f"{row['notes_present_pct']} & "
            f"{row['bib_entries']} \\\\"
        )

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 bibliography quality LaTeX table")
    parser.add_argument(
        "--input",
        default=str(_DEFAULT_INPUT),
        help="Path to tab_exp2_bib_quality.csv",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write tab_exp2_bib_quality.tex",
    )
    args = parser.parse_args(argv)

    rows = _load_rows(Path(args.input))
    summaries = summarize_bib_quality(rows)
    latex = generate_latex(summaries)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(latex)
    log.info("Wrote %s", out)


if __name__ == "__main__":
    main()
