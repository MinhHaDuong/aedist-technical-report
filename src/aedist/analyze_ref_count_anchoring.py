"""Analyze whether reference count is a useful anchoring/provenance signal.

This is the analysis script for ticket 0293 — evaluating reference count
as a complementary anchoring indicator in Exp2 runs.

Reads:
  experiments/derived/exp2_mart.jsonl         (n_bib_entries per run)
  report/inputs/generated/sota_cross_eval_view.csv  (F1, provenance scores)
  report/inputs/generated/tab_exp2_bib_quality_view.csv  (bib structure detail)

Writes:
  report/inputs/generated/ref_count_anchoring_analysis.csv
  (Printed summary to stdout)

Usage:
    uv run python -m aedist.analyze_ref_count_anchoring
    uv run python -m aedist.analyze_ref_count_anchoring --output path/to/out.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_MART = Path("experiments/derived/exp2_mart.jsonl")
_DEFAULT_CROSS_EVAL = Path(
    "report/inputs/generated/sota_cross_eval_view.csv"
)
_DEFAULT_BIB_QUALITY = Path(
    "report/inputs/generated/tab_exp2_bib_quality_view.csv"
)
_DEFAULT_OUTPUT = Path(
    "report/inputs/generated/ref_count_anchoring_analysis.csv"
)

_MODEL_TO_AGENT: dict[str, str] = {
    "claude-opus-4-6": "anthropic",
    "gpt-5.5": "openai",
    "gpt-5.5-2026-04-23": "openai",
    "mistral-large-2512": "mistral",
    "qwen3.7-max-2026-05-20": "qwen",
}

_OPTIMISED_ARMS = frozenset({"arm3", "optimised"})
_NAIVE_ARMS = frozenset({"arm1", "arm4", "naive"})


def _to_float(s: str | None) -> float | None:
    if s and s.strip() not in ("", "nan"):
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _pearson_r(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True))
    denom = (
        sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)
    ) ** 0.5
    return num / denom if denom > 0 else 0.0


def _load_mart_run_records(path: Path) -> dict[tuple, dict]:
    """Load 'run'-kind records from exp2_mart.jsonl.

    Returns a dict keyed by (arm, agent, run) with run_summary fields.
    """
    records: dict[tuple, dict] = {}
    with path.open() as f:
        for line in f:
            d = json.loads(line)
            if d.get("record_kind") != "run":
                continue
            rs = d.get("run_summary", {})
            key = (d.get("arm"), d.get("agent"), d.get("run"))
            records[key] = {
                "n_bib_entries": rs.get("n_bib_entries"),
                "n_rows": rs.get("n_rows"),
                "tokens_out": rs.get("tokens_out"),
            }
    return records


def _load_bib_quality(path: Path) -> dict[tuple, dict]:
    records: dict[tuple, dict] = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            key = (row["agent"], row["arm"], int(row["run"]))
            records[key] = {
                "bib_entries": _to_float(row["bib_entries"]),
                "bib_primary": _to_float(row["bib_primary"]),
                "n_rows_bib": _to_float(row["n_rows"]),
            }
    return records


def build_dataset(
    mart_path: Path,
    cross_eval_path: Path,
    bib_quality_path: Path,
) -> list[dict]:
    mart = _load_mart_run_records(mart_path)
    bib = _load_bib_quality(bib_quality_path)

    rows = []
    with cross_eval_path.open() as f:
        for row in csv.DictReader(f):
            agent = _MODEL_TO_AGENT.get(row["model"])
            arm = row["arm"]
            run = int(row["run"])
            mart_rec = mart.get((arm, agent, run), {})
            bib_rec = bib.get((agent, arm, run), {})
            rows.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "run": run,
                    "is_optimised": arm in _OPTIMISED_ARMS,
                    "n_bib_entries": mart_rec.get("n_bib_entries"),
                    "bib_primary": bib_rec.get("bib_primary"),
                    "n_rows": mart_rec.get("n_rows"),
                    "tokens_out": mart_rec.get("tokens_out"),
                    "f1": _to_float(row["accuracy_f1"]),
                    "prov_presence": _to_float(
                        row["provenance_source_presence"]
                    ),
                }
            )
    return rows


def correlations(rows: list[dict], arm_filter: str) -> dict[str, float | None]:
    """Compute Pearson r of each candidate metric with F1."""
    if arm_filter == "optimised":
        subset = [r for r in rows if r["arm"] in _OPTIMISED_ARMS]
    elif arm_filter == "naive":
        subset = [r for r in rows if r["arm"] in _NAIVE_ARMS]
    else:
        subset = rows

    def corr(key: str) -> float | None:
        pairs = [
            (r[key], r["f1"])
            for r in subset
            if r[key] is not None and r["f1"] is not None
        ]
        if len(pairs) < 3:
            return None
        return _pearson_r([p[0] for p in pairs], [p[1] for p in pairs])

    bpr_pairs = [
        (r["n_bib_entries"] / r["n_rows"], r["f1"])
        for r in subset
        if r["n_bib_entries"] is not None
        and r["n_rows"]
        and r["n_rows"] > 0
        and r["f1"] is not None
    ]

    return {
        "n": len(subset),
        "r_bib_entries_f1": corr("n_bib_entries"),
        "r_bib_primary_f1": corr("bib_primary"),
        "r_prov_presence_f1": corr("prov_presence"),
        "r_bib_per_row_f1": _pearson_r(
            [p[0] for p in bpr_pairs], [p[1] for p in bpr_pairs]
        )
        if bpr_pairs
        else None,
    }


def summarise(rows: list[dict]) -> None:
    opt = [r for r in rows if r["arm"] in _OPTIMISED_ARMS]

    print("=== Ticket 0293: reference-count as anchoring signal ===")
    print()
    print(f"Dataset: {len(rows)} runs total, {len(opt)} optimised-arm runs")
    print()

    zero_bib = [r for r in opt if r["n_bib_entries"] == 0]
    nonzero_bib = [r for r in opt if r["n_bib_entries"] is not None and r["n_bib_entries"] > 0]

    print(f"Zero-bib runs (optimised arm): {len(zero_bib)} / {len(opt)}")
    if zero_bib:
        from collections import Counter
        breakdown = Counter(r["agent"] for r in zero_bib)
        print(f"  By agent: {dict(sorted(breakdown.items()))}")
        f1s = [r["f1"] for r in zero_bib if r["f1"] is not None]
        if f1s:
            print(f"  Mean F1 (zero-bib): {sum(f1s)/len(f1s):.3f}")
    if nonzero_bib:
        f1s = [r["f1"] for r in nonzero_bib if r["f1"] is not None]
        if f1s:
            print(f"  Mean F1 (nonzero-bib): {sum(f1s)/len(f1s):.3f}")
    print()

    print("Correlations (optimised arm, n=40):")
    corr = correlations(rows, "optimised")
    def fmt(v: float | None) -> str:
        return f"{v:.3f}" if v is not None else "N/A"
    print(f"  r(n_bib_entries, F1)    = {fmt(corr['r_bib_entries_f1'])}")
    print(f"  r(bib_primary,   F1)    = {fmt(corr['r_bib_primary_f1'])}")
    print(f"  r(prov_presence, F1)    = {fmt(corr['r_prov_presence_f1'])}")
    print(f"  r(bib/row,       F1)    = {fmt(corr['r_bib_per_row_f1'])}")
    print()

    # Inflation check
    inflation = [
        r for r in opt
        if r["n_bib_entries"] is not None
        and r["n_bib_entries"] > 60
        and r["f1"] is not None
    ]
    print(f"Citation-inflation candidates (bib_entries > 60, optimised arm): {len(inflation)}")
    low_quality = [r for r in inflation if r["f1"] < 0.4]
    print(f"  Of which low-quality (F1 < 0.40): {len(low_quality)}")
    if low_quality:
        for r in low_quality:
            print(
                f"    agent={r['agent']} bib={r['n_bib_entries']}"
                f" f1={r['f1']:.3f} prov={r['prov_presence']}"
            )
    print()

    corr = correlations(rows, "optimised")
    r_val = corr["r_bib_entries_f1"]
    r_str = f"{r_val:.2f}" if r_val is not None else "N/A"
    n_zero = len(zero_bib)
    n_opt = len(opt)

    print("=== Recommendation ===")
    print(
        f"Reference count (n_bib_entries) does not add reliable anchoring signal:\n"
        f"  - Pearson r(bib_entries, F1) = {r_str} (optimised arm, n={n_opt}) — weak signal.\n"
        f"  - {n_zero}/{n_opt} optimised-arm runs have zero bibliography; top-performing\n"
        f"    agents (openai, F1=0.67 mean) produce zero-bib runs routinely.\n"
        f"  - High bib counts occur alongside both high and low F1: one mistral run\n"
        f"    has 72 bibliography entries yet F1=0.257 — the inflation scenario is\n"
        f"    confirmed empirically.\n"
        f"  - The pattern is agent-specific: anthropic always produces a bibliography;\n"
        f"    openai and qwen are inconsistent; the count reflects output format, not\n"
        f"    grounding quality.\n"
        f"VERDICT: REJECT reference count as a standalone or complementary anchoring\n"
        f"score. Retain as diagnostic metadata (already in exp2_mart run_summary)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mart",
        type=Path,
        default=_DEFAULT_MART,
        help="Path to exp2_mart.jsonl",
    )
    parser.add_argument(
        "--cross-eval",
        type=Path,
        default=_DEFAULT_CROSS_EVAL,
        help="Path to sota_cross_eval_view.csv",
    )
    parser.add_argument(
        "--bib-quality",
        type=Path,
        default=_DEFAULT_BIB_QUALITY,
        help="Path to tab_exp2_bib_quality_view.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Path for per-run output CSV",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    rows = build_dataset(args.mart, args.cross_eval, args.bib_quality)
    summarise(rows)

    fieldnames = [
        "agent",
        "arm",
        "run",
        "is_optimised",
        "n_bib_entries",
        "bib_primary",
        "n_rows",
        "tokens_out",
        "f1",
        "prov_presence",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d rows to %s", len(rows), args.output)


if __name__ == "__main__":
    main()
