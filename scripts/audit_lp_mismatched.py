"""Sweep all Exp1 batch2 model outputs and audit LP Mismatched pairs.

For every exp1_batch2 model CSV, runs the LP reconciler and collects every
pair that the LP labelled "Mismatched" (similarity < threshold but forced
by the cost structure).  Emits two outputs:

  experiments/derived/exp1_mismatched_audit.csv
      All Mismatched pairs across all 70 runs, with similarity score,
      capacity difference, and before/after accounting flag.

  STDOUT
      Per-model accounting delta (tp before → after fix) and the top-10
      hardest cases (highest similarity among all Mismatched pairs).

Usage:
    uv run python scripts/audit_lp_mismatched.py
    uv run python scripts/audit_lp_mismatched.py --output path/to/out.csv
"""

import argparse
import csv
import logging
from pathlib import Path

import pandas as pd

from aedist.config import DEFAULT_REFERENCE
from aedist.evaluate import load_plants_csv
from aedist.matching.lp import reconcile as reconcile_lp
from aedist.reconcile import plants_to_dataframe

log = logging.getLogger(__name__)

_REPO = Path(__file__).parent.parent
_EXP1_DIR = _REPO / "experiments" / "outputs" / "exp1_batch2"
_DEFAULT_OUT = _REPO / "experiments" / "derived" / "exp1_mismatched_audit.csv"

_OUTPUT_COLS = [
    "model",
    "run",
    "ref_name",
    "sys_name",
    "ref_name_clean",
    "sys_name_clean",
    "similarity_score",
    "ref_capacity",
    "sys_capacity",
    "capacity_diff_pct",
    "verdict",
]


def _cap_diff_pct(cap1: float | None, cap2: float | None) -> float | None:
    if cap1 is None or cap2 is None or cap1 == 0:
        return None
    return round(abs(cap1 - cap2) / cap1 * 100, 1)


def _run_label(csv_path: Path) -> tuple[str, str]:
    """Return (model, run) from a filename like 'claude-sonnet-4.6-run5.csv'."""
    stem = csv_path.stem
    parts = stem.rsplit("-run", 1)
    model = parts[0] if len(parts) == 2 else stem
    run = f"run{parts[1]}" if len(parts) == 2 else "run?"
    return model, run


def sweep(ref_csv: Path, exp1_dir: Path) -> list[dict]:
    """Return one row per Mismatched LP pair across all exp1 CSVs."""
    ref_plants = load_plants_csv(ref_csv)
    ref_df = plants_to_dataframe(ref_plants)

    rows: list[dict] = []
    csv_files = sorted(exp1_dir.glob("*-run*.csv"))
    if not csv_files:
        log.warning("No run CSVs found in %s", exp1_dir)
        return rows

    for csv_path in csv_files:
        model, run = _run_label(csv_path)
        sys_plants = load_plants_csv(csv_path)
        if not sys_plants:
            continue
        sys_df = plants_to_dataframe(sys_plants)

        try:
            result = reconcile_lp(ref_df, sys_df)
        except Exception as exc:
            log.warning("LP failed for %s: %s", csv_path.name, exc)
            continue

        mismatched = result[result["status"] == "Mismatched"]
        for _, r in mismatched.iterrows():
            cap1 = r.get("capacity_file1")
            cap2 = r.get("capacity_file2")
            try:
                cap1 = float(cap1) if cap1 is not None and not pd.isna(cap1) else None
            except (ValueError, TypeError):
                cap1 = None
            try:
                cap2 = float(cap2) if cap2 is not None and not pd.isna(cap2) else None
            except (ValueError, TypeError):
                cap2 = None

            sim = r.get("similarity_score")
            rows.append(
                {
                    "model": model,
                    "run": run,
                    "ref_name": r.get("name_file1") or "",
                    "sys_name": r.get("name_file2") or "",
                    "ref_name_clean": r.get("name_clean_file1") or "",
                    "sys_name_clean": r.get("name_clean_file2") or "",
                    "similarity_score": round(float(sim), 1)
                    if sim is not None and not pd.isna(sim)
                    else None,
                    "ref_capacity": cap1,
                    "sys_capacity": cap2,
                    "capacity_diff_pct": _cap_diff_pct(cap1, cap2),
                    "verdict": "hard"
                    if (sim is not None and not pd.isna(sim) and float(sim) >= 80)
                    else "clear",
                }
            )

    return rows


def _print_summary(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    if df.empty:
        print("No Mismatched pairs found — fix verified clean.")
        return

    print(f"\n=== Mismatched pairs: {len(df)} total across {df['model'].nunique()} models ===\n")

    # Per-model delta
    print("Per-model Mismatched count (each = 1 inflated tp before fix):")
    by_model = df.groupby("model").size().sort_values(ascending=False)
    for model, count in by_model.items():
        hard = df[(df["model"] == model) & (df["verdict"] == "hard")].shape[0]
        print(f"  {model:<40} {count:3d} total  ({hard} hard, sim≥80)")

    # Top-10 hardest cases (highest similarity — most plausible wrong matches)
    hard = df[df["verdict"] == "hard"].sort_values("similarity_score", ascending=False)
    if hard.empty:
        print("\nNo hard cases (sim≥80) found.")
        return

    print(f"\nTop-{min(10, len(hard))} hardest cases (sim≥80, sorted by similarity):")
    print(f"{'sim':>5}  {'ref_name':<40}  {'sys_name':<40}  {'model'}")
    print("-" * 110)
    for _, r in hard.head(10).iterrows():
        print(
            f"  {r['similarity_score']:>4.1f}  {r['ref_name']:<40}  {r['sys_name']:<40}  {r['model']}/{r['run']}"
        )


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ref", default=str(DEFAULT_REFERENCE), help="Reference CSV path")
    p.add_argument("--exp1-dir", default=str(_EXP1_DIR), help="exp1_batch2 output directory")
    p.add_argument("--output", default=str(_DEFAULT_OUT), help="Output audit CSV path")
    args = p.parse_args(argv)

    ref_csv = Path(args.ref)
    exp1_dir = Path(args.exp1_dir)
    out_path = Path(args.output)

    rows = sweep(ref_csv, exp1_dir)
    _print_summary(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_OUTPUT_COLS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nAudit CSV written: {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
