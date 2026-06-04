"""Compute directional statistical tests comparing arm1 (naive) vs arm2 (optimised).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

Reads tab_exp2_arms_runs_view.csv and produces stat_tests_arm1_vs_arm2.txt with:
1. Sign test across agents on n_matched (arm2 > arm1 direction)
2. Effect size on n_matched: median differences per agent and pooled
3. Coverage (inventory_rows) sign test — uses all runs including zero rows
4. Power caveat note

Usage:
    uv run python -m aedist.tabulate_stat_tests \\
        --input report/inputs/generated/tab_exp2_arms_runs_view.csv \\
        --output report/inputs/generated/stat_tests_arm1_vs_arm2.txt
"""

import argparse
import csv
import math
import statistics
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_row(row: dict) -> dict:
    """Parse a CSV row into typed fields. Returns dict with typed values."""
    n_matched_str = row["n_matched"].strip()
    return {
        "arm": row["arm"].strip(),
        "agent": row["agent"].strip(),
        "run": int(row["run"]),
        "inventory_rows": int(row["inventory_rows"]),
        "n_matched": int(n_matched_str) if n_matched_str else None,
        "classification": row["classification"].strip(),
    }


def binomial_upper_tail(k: int, n: int, p: float = 0.5) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p**i) * ((1 - p) ** (n - i))
    return total


def median_or_none(values: list[float | int]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def compute_stats(records: list[dict]) -> str:
    """Compute all stats and return formatted text."""
    agents = sorted({r["agent"] for r in records})
    lines = []

    lines.append("=" * 70)
    lines.append("Statistical tests: arm1 (naive) vs arm2 (optimised) — Exp 2")
    lines.append("=" * 70)
    lines.append("")

    # -------------------------------------------------------------------------
    # Per-agent data summary
    # -------------------------------------------------------------------------
    lines.append("## Per-agent data summary")
    lines.append("")
    lines.append(
        f"{'Agent':<12} {'arm':<10} {'n_rows':<7} {'rows_valid':<11} "
        f"{'median_rows':<13} {'n_matched_valid':<16} {'median_n_matched'}"
    )
    lines.append("-" * 80)

    agent_data: dict[str, dict] = {}
    for agent in agents:
        agent_data[agent] = {}
        for arm_name, arm_label in [("naive", "arm1"), ("optimised", "arm2")]:
            arm_rows = [r for r in records if r["agent"] == agent and r["arm"] == arm_name]
            # inventory_rows: include all runs (zeros = no_report = real coverage measurement)
            inv_values = [r["inventory_rows"] for r in arm_rows]
            inv_nonzero = [v for v in inv_values if v > 0]
            # n_matched: exclude missing (None) values
            nm_values = [r["n_matched"] for r in arm_rows if r["n_matched"] is not None]

            agent_data[agent][arm_label] = {
                "inventory_rows_all": inv_values,
                "inventory_rows_nonzero": inv_nonzero,
                "n_matched": nm_values,
            }

            lines.append(
                f"{agent:<12} {arm_label:<10} {len(inv_values):<7} "
                f"{len(inv_nonzero):<11} "
                f"{median_or_none(inv_values) or 'N/A':<13} "
                f"{len(nm_values):<16} "
                f"{median_or_none(nm_values) or 'N/A'}"
            )
    lines.append("")

    # -------------------------------------------------------------------------
    # Sign test on n_matched: arm2 > arm1
    # Only agents with >= 3 scored arm2 runs count
    # -------------------------------------------------------------------------
    lines.append("## Sign test on n_matched (arm2 > arm1)")
    lines.append("")
    lines.append("Rule: agent included only if arm2 has >= 3 scored runs.")
    lines.append("")

    eligible_agents = []
    sign_results = []
    for agent in agents:
        arm1_nm = agent_data[agent]["arm1"]["n_matched"]
        arm2_nm = agent_data[agent]["arm2"]["n_matched"]
        n2 = len(arm2_nm)
        status = "included" if n2 >= 3 else f"SKIPPED (arm2 scored: {n2}/5)"
        med1 = median_or_none(arm1_nm)
        med2 = median_or_none(arm2_nm)
        direction = None
        if n2 >= 3 and med1 is not None and med2 is not None:
            direction = med2 > med1
            eligible_agents.append(agent)
            sign_results.append(direction)
        lines.append(
            f"  {agent}: arm1 median={med1}, arm2 median={med2} "
            f"({len(arm1_nm)} / {n2} scored) → {status}"
        )
        if direction is not None:
            lines.append(f"    arm2 > arm1: {direction}")

    lines.append("")
    n_eligible = len(eligible_agents)
    k_positive = sum(sign_results)
    lines.append(f"Eligible agents: {n_eligible} ({', '.join(eligible_agents)})")
    lines.append(f"arm2 > arm1 count: {k_positive}/{n_eligible}")

    if n_eligible > 0:
        p_val = binomial_upper_tail(max(k_positive, 1), n_eligible, 0.5)
        min_p = 1.0 / (2**n_eligible)
        lines.append(f"One-tailed sign test p = {p_val:.4f}")
        lines.append(f"Min attainable p (N={n_eligible}) = {min_p:.4f}")
        lines.append("")
        lines.append(
            "HEADLINE: "
            + (
                f"{k_positive}/{n_eligible} eligible agents show arm2 > arm1 on n_matched "
                f"(p = {p_val:.4f}, one-tailed sign test; N={n_eligible} agents after "
                f"eligibility filter, min attainable p = {min_p:.4f})"
            )
        )
    else:
        lines.append("No eligible agents — sign test not applicable.")
    lines.append("")

    # -------------------------------------------------------------------------
    # Effect size on n_matched: median differences
    # -------------------------------------------------------------------------
    lines.append("## Effect size on n_matched (median arm2 − arm1 per agent)")
    lines.append("")
    diffs_nm = []
    for agent in agents:
        arm1_nm = agent_data[agent]["arm1"]["n_matched"]
        arm2_nm = agent_data[agent]["arm2"]["n_matched"]
        med1 = median_or_none(arm1_nm)
        med2 = median_or_none(arm2_nm)
        if med1 is not None and med2 is not None:
            diff = med2 - med1
            diffs_nm.append(diff)
            lines.append(f"  {agent}: {med2:.1f} − {med1:.1f} = {diff:+.1f}")
        else:
            lines.append(
                f"  {agent}: insufficient data (arm1 n={len(arm1_nm)}, arm2 n={len(arm2_nm)})"
            )
    if diffs_nm:
        pooled_median_diff = statistics.median(diffs_nm)
        lines.append(f"  Median of per-agent diffs: {pooled_median_diff:+.1f}")
    lines.append("")

    # -------------------------------------------------------------------------
    # Sign test on inventory_rows: arm2 > arm1
    # Using ALL runs (zeros = no_report = real 0-coverage measurement)
    # All 4 agents included (no missing data issue)
    # -------------------------------------------------------------------------
    lines.append("## Sign test on inventory_rows (arm2 > arm1)")
    lines.append("")
    lines.append("Rule: all 4 agents included; zeros (no_report) are genuine zeros.")
    lines.append("")

    inv_sign_results = []
    for agent in agents:
        arm1_inv = agent_data[agent]["arm1"]["inventory_rows_all"]
        arm2_inv = agent_data[agent]["arm2"]["inventory_rows_all"]
        med1 = median_or_none(arm1_inv)
        med2 = median_or_none(arm2_inv)
        direction = med2 > med1
        inv_sign_results.append(direction)
        lines.append(
            f"  {agent}: arm1 median={med1}, arm2 median={med2} → arm2 > arm1: {direction}"
        )

    k_inv = sum(inv_sign_results)
    n_inv = len(agents)
    p_inv = binomial_upper_tail(max(k_inv, 1), n_inv, 0.5)
    min_p_inv = 1.0 / (2**n_inv)
    lines.append("")
    lines.append(f"arm2 > arm1 count: {k_inv}/{n_inv}")
    lines.append(f"One-tailed sign test p = {p_inv:.4f}")
    lines.append(f"Min attainable p (N={n_inv}) = {min_p_inv:.4f}")
    lines.append("")
    lines.append(
        "HEADLINE: "
        + (
            f"{k_inv}/{n_inv} agents show arm2 > arm1 on inventory_rows "
            f"(p = {p_inv:.4f}, one-tailed sign test; "
            f"min attainable p = {min_p_inv:.4f})"
        )
    )
    lines.append("")

    # -------------------------------------------------------------------------
    # Effect size on inventory_rows
    # -------------------------------------------------------------------------
    lines.append("## Effect size on inventory_rows (median arm2 − arm1 per agent)")
    lines.append("")
    diffs_inv = []
    for agent in agents:
        arm1_inv = agent_data[agent]["arm1"]["inventory_rows_all"]
        arm2_inv = agent_data[agent]["arm2"]["inventory_rows_all"]
        med1 = median_or_none(arm1_inv)
        med2 = median_or_none(arm2_inv)
        diff = med2 - med1
        diffs_inv.append(diff)
        lines.append(f"  {agent}: {med2:.1f} − {med1:.1f} = {diff:+.1f}")
    pooled_inv_diff = statistics.median(diffs_inv)
    lines.append(f"  Median of per-agent diffs: {pooled_inv_diff:+.1f}")
    lines.append("")

    # -------------------------------------------------------------------------
    # Power caveat
    # -------------------------------------------------------------------------
    lines.append("## Power caveat")
    lines.append("")
    lines.append(
        "N=4 agents, one-tailed sign test: min attainable p = 1/2^4 = 0.0625. "
        "This design cannot reach α=0.05. All results should be interpreted as "
        "directional evidence only, not as hypothesis tests."
    )
    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute directional statistical tests for arm1 vs arm2 in Exp2."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("report/inputs/generated/tab_exp2_arms_runs_view.csv"),
        help="Path to tab_exp2_arms_runs_view.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report/inputs/generated/stat_tests_arm1_vs_arm2.txt"),
        help="Path to write the stat-test results text file",
    )
    args = parser.parse_args()

    rows = read_csv(args.input)
    records = [parse_row(r) for r in rows]

    text = compute_stats(records)
    print(text)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
