"""Generate a LaTeX summary table for Exp2 naive vs optimized arms.

Usage:
    python -m aedist.tabulate_exp2_arms --output report/inputs/generated/tab_exp2_arms.tex

The script reads machine-readable summary JSON files from the Exp2 output
folders and reports comparable per-model medians by arm.
"""

import argparse
import json
import logging
import statistics
from pathlib import Path

from .tabulate_utils import format_model_name

log = logging.getLogger(__name__)

_DEFAULT_NAIVE_SUMMARY = Path("experiments/outputs/sota_exp2_naive_arm/summary_20260522T2342Z.json")
_DEFAULT_OPTIMIZED_SUMMARY = Path("experiments/outputs/sota_exp2_brerun1/summary.json")
_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_DEFAULT_OPTIMIZED_DIR = Path("experiments/outputs/sota_exp2_brerun1")


def _load_summary(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"Summary at {path} must be a JSON array")
    return data


def _is_truncated(raw_payload: dict) -> bool:
    finish_reason = raw_payload.get("finish_reason")
    if finish_reason == "length":
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


def _row_cost_usd(row: dict) -> float:
    value = row.get("total_cost_usd", row.get("cost_usd", 0.0))
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _row_wall_s(row: dict) -> float:
    value = row.get("wall_s", 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _row_turns(row: dict) -> int:
    value = row.get("turns", 1)
    if isinstance(value, int):
        return value
    return 1


def summarize_arm(summary_rows: list[dict], arm_dir: Path, arm_name: str) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in summary_rows:
        model = row.get("model")
        if not isinstance(model, str):
            continue
        grouped.setdefault(model, []).append(row)

    out_rows = []
    for model, rows in grouped.items():
        n_runs = len(rows)
        n_report = sum(1 for row in rows if row.get("classification") == "report")
        n_truncated = 0
        for row in rows:
            agent = row.get("agent")
            run = row.get("run")
            if isinstance(agent, str) and isinstance(run, int):
                n_truncated += int(_run_is_truncated(arm_dir, agent, run))

        turns = [_row_turns(row) for row in rows]
        costs = [_row_cost_usd(row) for row in rows]
        walls = [_row_wall_s(row) for row in rows]

        out_rows.append(
            {
                "arm": arm_name,
                "model": model,
                "n_runs": n_runs,
                "report_rate": (n_report / n_runs) if n_runs else 0.0,
                "trunc_rate": (n_truncated / n_runs) if n_runs else 0.0,
                "median_turns": statistics.median(turns) if turns else 1.0,
                "median_cost_usd": statistics.median(costs) if costs else 0.0,
                "median_wall_s": statistics.median(walls) if walls else 0.0,
            }
        )

    out_rows.sort(key=lambda row: (row["report_rate"], row["model"]), reverse=True)
    return out_rows


def generate_exp2_arms_table(naive_rows: list[dict], optimized_rows: list[dict], naive_dir: Path, optimized_dir: Path) -> str:
    grouped_rows = [
        summarize_arm(naive_rows, naive_dir, "Naive"),
        summarize_arm(optimized_rows, optimized_dir, "Optimized"),
    ]

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

    has_rows = any(group for group in grouped_rows)
    if not has_rows:
        lines.append("(no data) & -- & -- & -- & -- & -- & -- \\\\")
    else:
        for rows in grouped_rows:
            for row in rows:
                model_name = format_model_name(row["model"])
                report_pct = row["report_rate"] * 100
                trunc_pct = row["trunc_rate"] * 100
                turns = row["median_turns"]
                lines.append(
                    f"{row['arm']} & {model_name} & {report_pct:.0f} & {trunc_pct:.0f} & {turns:.1f} & {row['median_cost_usd']:.3f} & {row['median_wall_s']:.1f} \\\\"
                )

    lines.append("\\end{longtable}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate Exp2 naive vs optimized arm summary table",
    )
    parser.add_argument("--output", required=True, help="Path to write tab_exp2_arms.tex")
    parser.add_argument(
        "--naive-summary",
        default=str(_DEFAULT_NAIVE_SUMMARY),
        help="Path to naive-arm summary JSON",
    )
    parser.add_argument(
        "--optimized-summary",
        default=str(_DEFAULT_OPTIMIZED_SUMMARY),
        help="Path to optimized-arm summary JSON",
    )
    parser.add_argument(
        "--naive-dir",
        default=str(_DEFAULT_NAIVE_DIR),
        help="Directory with naive-arm raw run files",
    )
    parser.add_argument(
        "--optimized-dir",
        default=str(_DEFAULT_OPTIMIZED_DIR),
        help="Directory with optimized-arm raw run files",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    naive_summary = _load_summary(Path(args.naive_summary))
    optimized_summary = _load_summary(Path(args.optimized_summary))
    latex = generate_exp2_arms_table(
        naive_summary,
        optimized_summary,
        Path(args.naive_dir),
        Path(args.optimized_dir),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex)
    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()