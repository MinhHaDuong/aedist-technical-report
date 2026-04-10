"""Generate verification tradeoff table.

Reads annotated verification CSVs from derived/verification/ and produces
a precision-coverage tradeoff table by sweeping evidence_score thresholds.

Usage::

    python -m aedist.tabulate_verification \\
        --input derived/verification \\
        --output derived/verification/tradeoff.csv \\
        [--latex report/inputs/generated/tab_verification.tex]
"""

import argparse
import csv
import logging
import re
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

# Pattern: {model}-{mode}-run{N}.csv (not *_filtered.csv)
_CSV_PATTERN = re.compile(r"^(.+)-(\w+)-run(\d+)\.csv$")


def _load_annotated_csvs(verification_dir: Path) -> dict[str, list[list[dict]]]:
    """Load annotated CSVs grouped by mode.

    Returns {mode: [run1_rows, run2_rows, ...]} where each run is a list
    of dicts with at least 'evidence_score' key.
    Skips *_filtered.csv, *_summary.json, and cache files.
    """
    by_mode: dict[str, list[list[dict]]] = defaultdict(list)

    for csv_path in sorted(verification_dir.glob("*.csv")):
        if "_filtered" in csv_path.name or "_summary" in csv_path.name:
            continue
        m = _CSV_PATTERN.match(csv_path.name)
        if not m:
            continue
        mode = m.group(2)
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if rows and "evidence_score" in rows[0]:
            by_mode[mode].append(rows)
            log.info("Loaded %s: %d plants, mode=%s", csv_path.name, len(rows), mode)

    return dict(by_mode)


def compute_tradeoff(verification_dir: Path) -> list[dict]:
    """Compute precision-coverage tradeoff across modes and thresholds.

    For each mode, for each threshold (1-4):
    - Filter to plants with evidence_score >= threshold
    - Report n_retained, n_total, retention_pct
    - If multiple runs exist (stochastic modes), average across runs.

    Returns list of dicts ready for CSV output.
    """
    by_mode = _load_annotated_csvs(verification_dir)
    results = []

    for mode, runs in sorted(by_mode.items()):
        for threshold in range(1, 5):
            n_retained_sum = 0
            n_total_sum = 0

            for run_rows in runs:
                n_total = len(run_rows)
                n_retained = sum(
                    1 for r in run_rows if int(r.get("evidence_score", 0)) >= threshold
                )
                n_retained_sum += n_retained
                n_total_sum += n_total

            n_runs = len(runs)
            avg_retained = n_retained_sum / n_runs
            avg_total = n_total_sum / n_runs
            retention = (avg_retained / avg_total * 100) if avg_total > 0 else 0.0

            results.append(
                {
                    "mode": mode,
                    "threshold": str(threshold),
                    "n_retained": str(round(avg_retained)),
                    "n_total": str(round(avg_total)),
                    "retention_pct": f"{retention:.1f}",
                    "n_runs": str(n_runs),
                }
            )

    return results


def generate_tradeoff_csv(verification_dir: Path, output: Path) -> None:
    """Write tradeoff table as CSV."""
    rows = compute_tradeoff(verification_dir)
    if not rows:
        log.warning("No verification data found in %s", verification_dir)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %s (%d rows)", output, len(rows))


def generate_tradeoff_latex(verification_dir: Path) -> str:
    """Generate a LaTeX tabular from the tradeoff data.

    Columns: Mode, Threshold, Retained, Total, Retention (%).
    Modes are grouped with midrules between them.
    """
    rows = compute_tradeoff(verification_dir)
    if not rows:
        return ""

    lines = [
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Mode & Threshold & Retained & Total & Retention (\%) \\",
        r"\midrule",
    ]

    prev_mode = None
    for r in rows:
        if prev_mode and r["mode"] != prev_mode:
            lines.append(r"\midrule")
        mode_label = r["mode"].capitalize()
        lines.append(
            f"{mode_label} & {r['threshold']} & {r['n_retained']} & "
            f"{r['n_total']} & {r['retention_pct']} \\\\"
        )
        prev_mode = r["mode"]

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Verification tradeoff table")
    parser.add_argument(
        "--input",
        default="derived/verification",
        help="Directory with annotated verification CSVs",
    )
    parser.add_argument(
        "--output",
        default="derived/verification/tradeoff.csv",
        help="Output CSV path",
    )
    parser.add_argument("--latex", help="Optional LaTeX output path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    vdir = Path(args.input)
    generate_tradeoff_csv(vdir, Path(args.output))

    if args.latex:
        tex = generate_tradeoff_latex(vdir)
        Path(args.latex).parent.mkdir(parents=True, exist_ok=True)
        Path(args.latex).write_text(tex)
        log.info("Wrote %s", args.latex)


if __name__ == "__main__":
    main()
