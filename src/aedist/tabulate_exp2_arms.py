"""Generate a LaTeX summary table for Exp2 naive vs optimised arms.

Usage:
    python -m aedist.tabulate_exp2_arms --input report/inputs/generated/tab_exp2_arms_runs.csv \\
        --output report/inputs/generated/tab_exp2_arms.tex

Reads the flat per-run CSV produced by tabulate_exp2_arms_runs and reports
per-model medians by arm.  The truncation check reads paired *.raw.json files
from the arm directories.
"""

import argparse
import csv
import json
import logging
import statistics
from pathlib import Path

from .tabulate_utils import format_model_name

log = logging.getLogger(__name__)

_DEFAULT_INPUT = Path("report/inputs/generated/tab_exp2_arms_runs.csv")
_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_DEFAULT_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")


def _is_truncated(raw_payload: dict) -> bool:
    if raw_payload.get("finish_reason") == "length":
        return True
    usage = raw_payload.get("usage")
    if not isinstance(usage, dict):
        return False
    completion_tokens = usage.get("completion_tokens")
    max_tokens = raw_payload.get("max_tokens")
    if isinstance(completion_tokens, int) and isinstance(max_tokens, int):
        return completion_tokens >= max_tokens
    return False


def _run_is_truncated(arm_dir: Path, agent: str, run: int) -> bool:

    raw_path = arm_dir / f"{agent}_run{run:02d}.raw.json"
    if not raw_path.exists():
        return False
    payload = json.loads(raw_path.read_text())
    if not isinstance(payload, dict):
        return False
    return _is_truncated(payload)


def _arm_dir(arm_label: str, naive_dir: Path, optimised_dir: Path) -> Path:
    return naive_dir if arm_label == "naive" else optimised_dir


def _load_runs(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            row["run"] = int(row["run"])
            row["narrative_chars"] = int(row["narrative_chars"])
            row["inventory_rows"] = (
                int(row["inventory_rows"]) if row["inventory_rows"] not in ("", "None") else None
            )
            row["cost_usd"] = float(row["cost_usd"])
            row["wall_s"] = float(row["wall_s"])
            row["turns"] = int(row["turns"])
            rows.append(row)
    return rows


def summarize_arms(runs: list[dict], naive_dir: Path, optimised_dir: Path) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in runs:
        key = (row["arm"], row["model"])
        grouped.setdefault(key, []).append(row)

    out_rows = []
    for (arm, model), rows in grouped.items():
        arm_dir = _arm_dir(arm, naive_dir, optimised_dir)
        n_runs = len(rows)
        n_report = sum(1 for r in rows if r["classification"] == "report")
        n_truncated = sum(int(_run_is_truncated(arm_dir, r["agent"], r["run"])) for r in rows)
        costs = [r["cost_usd"] for r in rows]
        walls = [r["wall_s"] for r in rows]
        turns_list = [r["turns"] for r in rows]

        out_rows.append(
            {
                "arm": arm,
                "model": model,
                "n_runs": n_runs,
                "report_rate": n_report / n_runs if n_runs else 0.0,
                "trunc_rate": n_truncated / n_runs if n_runs else 0.0,
                "median_turns": statistics.median(turns_list) if turns_list else 1.0,
                "median_cost_usd": statistics.median(costs) if costs else 0.0,
                "median_wall_s": statistics.median(walls) if walls else 0.0,
            }
        )

    out_rows.sort(key=lambda r: (r["arm"], -r["report_rate"], r["model"]))
    return out_rows


def generate_latex(summary_rows: list[dict]) -> str:
    lines = [
        "% Auto-generated - do not edit",
        "\\begin{longtable}[]{@{}llrrrrr@{}}",
        "\\caption{Experiment 2 arm-level operational summary (N=5 per model and arm)}\\label{tab:exp2-arms}\\\\",
        "\\toprule",
        "Arm & Model & Report (\\%) & Truncated (\\%) & Median turns & Median cost (\\$) & Median wall (s) \\\\",
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endlastfoot",
    ]

    if not summary_rows:
        lines.append("(no data) & -- & -- & -- & -- & -- & -- \\\\")
    else:
        lines.extend(
            f"{row['arm'].capitalize()} & {format_model_name(row['model'])} & "
            f"{row['report_rate'] * 100:.0f} & {row['trunc_rate'] * 100:.0f} & "
            f"{row['median_turns']:.1f} & {row['median_cost_usd']:.3f} & "
            f"{row['median_wall_s']:.1f} \\\\"
            for row in summary_rows
        )

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Generate Exp2 arm summary LaTeX table")
    parser.add_argument(
        "--input", default=str(_DEFAULT_INPUT), help="Path to tab_exp2_arms_runs.csv"
    )
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_arms.tex")
    parser.add_argument("--naive-dir", default=str(_DEFAULT_NAIVE_DIR))
    parser.add_argument("--optimised-dir", default=str(_DEFAULT_OPTIMISED_DIR))
    args = parser.parse_args(argv)

    runs = _load_runs(Path(args.input))
    summary = summarize_arms(runs, Path(args.naive_dir), Path(args.optimised_dir))
    latex = generate_latex(summary)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(latex)
    log.info("Wrote %s", out)


if __name__ == "__main__":
    main()
