"""Canary gate analysis for ticket 0198.

Compares canary (topup run 1) F1 against baseline 5-rep range per model.
Gate: canary F1 ∈ [mean - 2σ, mean + 2σ] → pool with original 5 reps.

GPT-5.5 refusals are data, not drift — classified separately.
Deterministic models (σ=0) use ±0.01 tolerance to absorb rounding.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path


def load_baseline_stats(base_dir: Path) -> dict:
    stats: dict[str, list[float | None]] = defaultdict(list)
    for rj in sorted(base_dir.glob("*.record.json")):
        rec = json.loads(rj.read_text())
        model = rec["method_params"]["model"]
        f1 = rec["result_summary"].get("f1")
        status = rec["result_summary"].get("status", "ok")
        if status == "declined":
            stats[model].append(None)
        elif f1 is not None:
            stats[model].append(f1)
    return dict(stats)


def load_canary(topup_dir: Path) -> dict[str, dict]:
    results = {}
    for jf in sorted(topup_dir.glob("*-run1.json")):
        if jf.name.startswith("reconciliation_"):
            continue
        rec = json.loads(jf.read_text())
        model = rec["model"]
        usage = rec.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        reasoning_tokens = details.get("reasoning_tokens") if isinstance(details, dict) else None
        # Avoid Path.with_suffix — model slugs like "claude-haiku-4.5" confuse it
        rj = jf.parent / (jf.name[: -len(".json")] + ".record.json")
        f1 = None
        status = "ok"
        if rj.exists():
            record = json.loads(rj.read_text())
            f1 = record["result_summary"].get("f1")
            status = record["result_summary"].get("status", "ok")
        results[model] = {
            "f1": f1,
            "status": status,
            "reasoning_tokens": reasoning_tokens,
            "tokens_out": usage.get("completion_tokens"),
            "cost_usd": rec.get("cost_usd", 0),
        }
    return results


def run_gate(base_dir: Path, topup_dir: Path) -> list[dict]:
    baseline = load_baseline_stats(base_dir)
    canary = load_canary(topup_dir)

    rows = []
    for model in sorted(set(list(baseline.keys()) + list(canary.keys()))):
        base_vals = [v for v in baseline.get(model, []) if v is not None]
        n_declined = sum(1 for v in baseline.get(model, []) if v is None)
        c = canary.get(model, {})
        canary_f1 = c.get("f1")
        canary_status = c.get("status", "missing")

        row: dict = {
            "model": model,
            "n_base": len(base_vals),
            "n_declined": n_declined,
            "canary_f1": canary_f1,
            "canary_status": canary_status,
            "reasoning_tokens": c.get("reasoning_tokens"),
            "tokens_out": c.get("tokens_out"),
            "cost_usd": c.get("cost_usd"),
        }

        if canary_status == "declined":
            row["gate"] = "DECLINED"
            row["note"] = "refusal — data, not drift"
        elif canary_f1 is None:
            row["gate"] = "NO_F1"
            row["note"] = "canary produced no F1"
        elif len(base_vals) < 2:
            row["gate"] = "SKIP"
            row["note"] = f"insufficient baseline reps ({len(base_vals)})"
        else:
            mean = statistics.mean(base_vals)
            sd = statistics.stdev(base_vals)
            tol = max(sd, 0.005)
            lo = max(0, mean - 2 * tol)
            hi = min(1, mean + 2 * tol)
            row["base_mean"] = round(mean, 4)
            row["base_sd"] = round(sd, 4)
            row["gate_lo"] = round(lo, 4)
            row["gate_hi"] = round(hi, 4)

            if lo <= canary_f1 <= hi:
                row["gate"] = "PASS"
                row["note"] = "pool with baseline"
            else:
                row["gate"] = "DRIFT"
                row["note"] = f"canary F1={canary_f1:.4f} outside [{lo:.4f}, {hi:.4f}]"

        rows.append(row)

    return rows


def print_report(rows: list[dict]) -> None:
    print(
        f"{'Model':<45} {'Base':>4} {'Canary F1':>9} {'Mean±2σ':>16}  {'Gate':>8}  {'Reasoning':>9}  Note"
    )
    print("-" * 130)

    total_cost = 0.0
    for r in rows:
        model = r["model"]
        n = r["n_base"]
        cf1 = f"{r['canary_f1']:.4f}" if r["canary_f1"] is not None else "---"
        gate_range = ""
        if "base_mean" in r:
            gate_range = f"[{r['gate_lo']:.4f}, {r['gate_hi']:.4f}]"
        gate = r["gate"]
        reasoning = str(r.get("reasoning_tokens") or "---")
        note = r.get("note", "")
        cost = r.get("cost_usd") or 0
        total_cost += cost
        print(f"{model:<45} {n:>4} {cf1:>9} {gate_range:>16}  {gate:>8}  {reasoning:>9}  {note}")

    print("-" * 130)
    passed = sum(1 for r in rows if r["gate"] == "PASS")
    drift = sum(1 for r in rows if r["gate"] == "DRIFT")
    declined = sum(1 for r in rows if r["gate"] == "DECLINED")
    print(
        f"PASS: {passed}  DRIFT: {drift}  DECLINED: {declined}  Total canary cost: ${total_cost:.4f}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Canary gate analysis (ticket 0198)")
    parser.add_argument(
        "--base", default="outputs/ablation/direct/p1_base", help="Baseline output dir"
    )
    parser.add_argument(
        "--topup", default="outputs/ablation/direct/p1_base.topup", help="Topup output dir"
    )
    args = parser.parse_args()

    rows = run_gate(Path(args.base), Path(args.topup))
    print_report(rows)
