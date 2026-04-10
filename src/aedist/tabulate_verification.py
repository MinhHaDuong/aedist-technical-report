"""Generate verification tradeoff table.

Reads annotated verification CSVs from derived/verification/ and produces
a precision-coverage tradeoff table by sweeping evidence_score thresholds.
Evaluates each filtered subset against the reference to compute precision,
coverage, and F1.

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

from .evaluate import load_plants_csv, plants_from_dicts
from .metrics import compute_metrics
from .reconcile import reconcile

log = logging.getLogger(__name__)

_DEFAULT_REF = (
    Path(__file__).parent.parent.parent / "data" / "reference" / "vietnam_thermal_v1.csv"
)

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
        if csv_path.name == "tradeoff.csv":
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


def _evaluate_subset(rows: list[dict], ref_plants: list) -> dict:
    """Evaluate a subset of plants against the reference.

    Returns dict with precision, coverage, f1, tp, fp, fn.
    """
    if not rows:
        return {"precision": 0.0, "coverage": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0}

    system_plants = plants_from_dicts(rows)
    entries = reconcile(ref_plants, system_plants)
    m = compute_metrics(entries)
    return {
        "precision": round(m.precision, 4),
        "coverage": round(m.coverage, 4),
        "f1": round(m.f1, 4),
        "tp": m.n_matched,
        "fp": m.n_hallucinated,
        "fn": m.n_missed,
    }


def compute_tradeoff(verification_dir: Path, reference: Path | None = None) -> list[dict]:
    """Compute precision-coverage tradeoff across modes and thresholds.

    For each mode, for each threshold (1-4):
    - Filter to plants with evidence_score >= threshold
    - Evaluate filtered subset against reference
    - Report n_retained, retention_pct, precision, coverage, f1
    - If multiple runs exist (stochastic modes), average across runs.

    Returns list of dicts ready for CSV output.
    """
    ref_path = reference or _DEFAULT_REF
    ref_plants = load_plants_csv(ref_path)

    by_mode = _load_annotated_csvs(verification_dir)
    results = []

    for mode, runs in sorted(by_mode.items()):
        for threshold in range(1, 5):
            n_retained_sum = 0
            n_total_sum = 0
            precision_sum = 0.0
            coverage_sum = 0.0
            f1_sum = 0.0

            for run_rows in runs:
                n_total = len(run_rows)
                filtered = [r for r in run_rows if int(r.get("evidence_score", 0)) >= threshold]
                n_retained = len(filtered)
                n_retained_sum += n_retained
                n_total_sum += n_total

                metrics = _evaluate_subset(filtered, ref_plants)
                precision_sum += metrics["precision"]
                coverage_sum += metrics["coverage"]
                f1_sum += metrics["f1"]

            n_runs = len(runs)
            avg_retained = n_retained_sum / n_runs
            avg_total = n_total_sum / n_runs
            retention = (avg_retained / avg_total * 100) if avg_total > 0 else 0.0

            results.append({
                "mode": mode,
                "threshold": threshold,
                "n_retained": round(avg_retained),
                "n_total": round(avg_total),
                "retention_pct": round(retention, 1),
                "precision": round(precision_sum / n_runs, 4),
                "coverage": round(coverage_sum / n_runs, 4),
                "f1": round(f1_sum / n_runs, 4),
                "n_runs": n_runs,
            })

    return results


_TRADEOFF_FIELDS = [
    "mode",
    "threshold",
    "n_retained",
    "n_total",
    "retention_pct",
    "precision",
    "coverage",
    "f1",
    "n_runs",
]


def write_tradeoff_csv(rows: list[dict], output: Path) -> None:
    """Write tradeoff rows as CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TRADEOFF_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %s (%d rows)", output, len(rows))


def format_tradeoff_latex(rows: list[dict]) -> str:
    """Format tradeoff rows as a LaTeX tabular.

    Modes are grouped with midrules between them.
    """
    if not rows:
        return ""

    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Mode & Threshold & Retained & Precision (\%) & Coverage (\%) & F1 (\%) \\",
        r"\midrule",
    ]

    prev_mode = None
    for r in rows:
        if prev_mode and r["mode"] != prev_mode:
            lines.append(r"\midrule")
        mode_label = r["mode"].capitalize()
        prec_pct = f"{r['precision'] * 100:.1f}"
        cov_pct = f"{r['coverage'] * 100:.1f}"
        f1_pct = f"{r['f1'] * 100:.1f}"
        lines.append(
            f"{mode_label} & {r['threshold']} & {r['n_retained']} & "
            f"{prec_pct} & {cov_pct} & {f1_pct} \\\\"
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
    rows = compute_tradeoff(vdir)
    if not rows:
        log.warning("No verification data found in %s", vdir)
        return

    write_tradeoff_csv(rows, Path(args.output))

    if args.latex:
        tex = format_tradeoff_latex(rows)
        Path(args.latex).parent.mkdir(parents=True, exist_ok=True)
        Path(args.latex).write_text(tex)
        log.info("Wrote %s", args.latex)


if __name__ == "__main__":
    main()
