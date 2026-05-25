"""Rerun exp3 arm2 anthropic Phase B for run01–run05 (ticket 0295).

Reuses existing Phase A design from each run directory.  Phase B is
launched sequentially with INTER_REP_PAUSE_S between reps so that the
5-min Anthropic prompt-cache TTL stays warm for cross-rep Turn-1 hits.

Two cache breakpoints are active (see exp2_interactive_smoke.py):
  1. system prompt      — ~4700 tokens, reused on every turn and rep
  2. Turn-1 user prompt — ~300 tokens, reused on turns 2+ within each rep
     and on Turn-1 of subsequent reps when spacing ≤ 5 min

Ledger policy (ticket 0295): in-place merge — each run's summary.json
retains the passing mistral/openai/qwen entries; only the anthropic entry
is replaced.

Usage:
  # Dry-run (no API call; prints design):
  uv run python experiments/sota/rerun_exp3_arm2_anthropic.py --dry-run

  # Single run (test cache activation before launching all 5):
  uv run python experiments/sota/rerun_exp3_arm2_anthropic.py --run 1

  # All 5 runs sequentially:
  uv run python experiments/sota/rerun_exp3_arm2_anthropic.py

After run01 completes, verify cache hits in:
  experiments/outputs/sota_exp3_arm2_batch1/run01/anthropic_run01/
  Check anthropic_turn_01.raw.json → usage.cache_creation_input_tokens > 0
  Check anthropic_turn_02.raw.json → usage.cache_read_input_tokens > 0

Credit precheck: verify ANTHROPIC_API_KEY is loaded and org has balance
before launch.  Log the check timestamp in ticket 0295 log section.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT_BASE = REPO_ROOT / "experiments" / "outputs" / "sota_exp3_arm2_batch1"
INTER_REP_PAUSE_S = 60
BUDGET_CAP_PHASE_B_USD = 5.0
MIN_PHASE_B_MAX_TOKENS = 32_000

log = logging.getLogger(__name__)

sys.path.insert(0, str(REPO_ROOT))

from experiments.sota.exp2_interactive_smoke import (  # noqa: E402
    _run_one_agent,
)


def _make_args(run_num: int, *, output_base: Path, dry_run: bool) -> argparse.Namespace:
    run_dir = output_base / f"run{run_num:02d}"
    return argparse.Namespace(
        output_dir=run_dir,
        run_number=1,
        reuse_phase_a_from=run_dir,
        evidence_pack_manifest=None,
        budget_cap_phase_a=1.0,
        budget_cap_phase_b=BUDGET_CAP_PHASE_B_USD,
        phase_a_max_tokens=8000,
        phase_b_max_tokens=12000,
        min_phase_b_max_tokens=MIN_PHASE_B_MAX_TOKENS,
        stop_after_phase_a=False,
        no_confirm=True,
        dry_run=dry_run,
    )


def _merge_summary(run_dir: Path, new_entry: dict) -> None:
    summary_path = run_dir / "summary.json"
    existing = json.loads(summary_path.read_text(encoding="utf-8"))
    merged = [e if e.get("agent") != "anthropic" else new_entry for e in existing]
    if not any(e.get("agent") == "anthropic" for e in existing):
        merged.append(new_entry)
    summary_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    log.info("summary.json updated (%s): anthropic → %s", run_dir.name, new_entry.get("status"))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Rerun exp3 arm2 anthropic Phase B (ticket 0295).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--run",
        type=int,
        choices=range(1, 6),
        metavar="N",
        default=None,
        help="Run only rep N (1–5).  Omit to run all 5 sequentially.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Phase A design and exit; no API call.",
    )
    p.add_argument(
        "--output-base",
        type=Path,
        default=DEFAULT_OUTPUT_BASE,
        metavar="DIR",
        help="Root of the arm2 batch output tree (default: %(default)s).",
    )
    args = p.parse_args(argv)
    output_base: Path = args.output_base

    runs = [args.run] if args.run is not None else list(range(1, 6))

    for i, run_num in enumerate(runs):
        log.info("=== arm2 anthropic run%02d (%d/%d) ===", run_num, i + 1, len(runs))
        run_args = _make_args(run_num, output_base=output_base, dry_run=args.dry_run)
        result = _run_one_agent(run_args, "anthropic")

        if not args.dry_run:
            run_dir = output_base / f"run{run_num:02d}"
            _merge_summary(run_dir, result)
            log.info(
                "run%02d done: status=%s cost=%.4f turns=%d",
                run_num,
                result.get("status"),
                float(result.get("total_cost_usd", 0.0)),
                int(result.get("turns", 0)),
            )

        if i < len(runs) - 1:
            log.info("Pausing %ds before next run (TTL keepalive)...", INTER_REP_PAUSE_S)
            time.sleep(INTER_REP_PAUSE_S)

    log.info("Rerun complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
