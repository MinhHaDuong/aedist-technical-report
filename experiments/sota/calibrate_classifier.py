"""Calibrate a candidate dialogue classifier model against known fixtures.

Loads fixture files from the exp2 smoke run plus a hand-crafted adversarial
planning fixture, then runs them through the same prompt template used by
``dialogue_classifier.py`` — but targeting a candidate model via OpenRouter.

Usage::

    uv run python -m experiments.sota.calibrate_classifier
    uv run python -m experiments.sota.calibrate_classifier --model nvidia/nemotron-nano-9b-v2
    uv run python -m experiments.sota.calibrate_classifier --dry-run   # first fixture only
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import httpx

from experiments.sota.dialogue_classifier import (
    _MAX_NARRATIVE_CHARS,
    CLASSIFIER_PROMPT_TEMPLATE,
    _parse_class,
)

log = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────
DEFAULT_MODEL = "nvidia/nemotron-nano-9b-v2"
OPENROUTER_BASE = "https://openrouter.ai/api"

# Nemotron pricing (OpenRouter listing, 2026-05)
PRICE_PER_MTOK_IN = 0.04
PRICE_PER_MTOK_OUT = 0.16
_TOKENS_PER_MTOK = 1_000_000

SMOKE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "sota_exp2_smoke"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "classifier_calibration"

# ── Hand-crafted adversarial fixture ─────────────────────────────────
# Looks superficially like a report (headings, numbered list, "Sources")
# but contains only future-tense planning — no actual table rows.
FIXTURE_4_TEXT = """\
## Inventory Construction Plan

I will build the structured inventory in three phases:

### Phase 1 — Source Collection
1. Download PDP8 Revised Decision No. 262/QD-TTg (2024) from MOIT portal
2. Cross-reference with GEM Global Coal Plant Tracker (April 2026 release)
3. Extract unit-level records from EVN Annual Report 2025, Tables 3.1–3.7

### Phase 2 — Reconciliation
I will reconcile capacity figures across the three primary sources listed
above. Where discrepancies exceed 5%, I will flag them in a notes column.

### Phase 3 — Table Assembly
The final table will include: Name, Province, Fuel, Technology, Units x MW,
Total MWe, Status, COD, Owner, Source 1, Source 2, Notes.

### Sources I Will Consult
- MOIT Decision 262/QD-TTg: https://moit.gov.vn/documents/262-QD-TTg
- GEM GCPT April 2026: https://globalenergymonitor.org/projects/global-coal-plant-tracker/
- EVN Annual Report 2025: https://evn.com.vn/annual-report-2025

I estimate this will take 2–3 turns to complete with full provenance.
"""


# ── Fixture definitions ──────────────────────────────────────────────
def _build_fixtures() -> list[dict]:
    """Return the four calibration fixtures with expected labels."""
    return [
        {
            "id": "turn_01_planning",
            "path": str(SMOKE_DIR / "mistral_turn_01.report.md"),
            "expected": "no_report",
            "description": "planning preamble — Step-by-Step Execution Plan",
        },
        {
            "id": "turn_02_initial_report",
            "path": str(SMOKE_DIR / "mistral_turn_02.report.md"),
            "expected": "report",
            "description": "initial inventory with sector overview + table",
        },
        {
            "id": "turn_03_polished_report",
            "path": str(SMOKE_DIR / "mistral_turn_03.report.md"),
            "expected": "report",
            "description": "polished inventory — full structured table",
        },
        {
            "id": "fixture_04_adversarial_planner",
            "path": None,
            "expected": "no_report",
            "description": "hand-crafted verbose planner with report-like headings but no table",
            "inline_text": FIXTURE_4_TEXT,
        },
    ]


def _load_fixture_text(fixture: dict) -> str:
    """Return the narrative text for a fixture."""
    if fixture.get("inline_text"):
        return fixture["inline_text"]
    return Path(fixture["path"]).read_text()


def _build_prompt(narrative: str) -> str:
    excerpt = narrative[:_MAX_NARRATIVE_CHARS]
    return CLASSIFIER_PROMPT_TEMPLATE.format(narrative_excerpt=excerpt)


def _compute_cost(usage: dict) -> float:
    tokens_in = int(usage.get("prompt_tokens", 0) or 0)
    tokens_out = int(usage.get("completion_tokens", 0) or 0)
    return (
        tokens_in * PRICE_PER_MTOK_IN / _TOKENS_PER_MTOK
        + tokens_out * PRICE_PER_MTOK_OUT / _TOKENS_PER_MTOK
    )


def _call_openrouter(prompt: str, model: str, api_key: str) -> dict:
    """POST /v1/chat/completions via OpenRouter. Returns full JSON response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://github.com/haduong/aedist-technical-report",
        "X-Title": "AEDIST classifier calibration",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 32,
    }
    with httpx.Client(base_url=OPENROUTER_BASE, headers=headers) as client:
        resp = client.post("/v1/chat/completions", json=body, timeout=60.0)
        resp.raise_for_status()
        return resp.json()


def _run_one(fixture: dict, model: str, api_key: str) -> dict:
    """Classify one fixture and return a result dict."""
    text = _load_fixture_text(fixture)
    prompt = _build_prompt(text)

    t0 = time.monotonic()
    raw = _call_openrouter(prompt, model, api_key)
    wall_s = round(time.monotonic() - t0, 3)

    reply_text = raw.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    verdict = _parse_class(reply_text)
    usage = raw.get("usage", {}) or {}
    cost = _compute_cost(usage)

    correct = verdict == fixture["expected"]

    result = {
        "fixture_id": fixture["id"],
        "description": fixture["description"],
        "expected": fixture["expected"],
        "verdict": verdict,
        "correct": correct,
        "reply_raw": reply_text,
        "model": model,
        "wall_s": wall_s,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost_usd": round(cost, 8),
    }

    log.info(
        "fixture=%s expected=%s verdict=%s correct=%s wall=%.2fs cost=$%.6f raw=%r",
        fixture["id"],
        fixture["expected"],
        verdict,
        correct,
        wall_s,
        cost,
        reply_text,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate a candidate dialogue classifier model")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenRouter model ID (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run only the first fixture to verify API connectivity",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "nemotron_calibration.json",
        help="Path for calibration results JSON (default: %(default)s)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        log.error("OPENROUTER_API_KEY not set in environment. Aborting.")
        raise SystemExit(1)

    fixtures = _build_fixtures()
    if args.dry_run:
        fixtures = fixtures[:1]
        log.info("Dry-run mode: running first fixture only")

    results = []
    for fixture in fixtures:
        result = _run_one(fixture, args.model, api_key)
        results.append(result)

    # Summary
    n_correct = sum(1 for r in results if r["correct"])
    n_total = len(results)
    total_cost = sum(r["cost_usd"] for r in results)
    passed = n_correct >= 3 if n_total == 4 else n_correct == n_total

    summary = {
        "model": args.model,
        "n_correct": n_correct,
        "n_total": n_total,
        "total_cost_usd": round(total_cost, 6),
        "passed": passed,
        "threshold": "3/4" if n_total == 4 else f"{n_total}/{n_total}",
    }

    output = {
        "summary": summary,
        "results": results,
    }

    # Write results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    log.info("Results written to %s", args.output)

    # Print human-readable summary
    print(f"\n{'=' * 60}")
    print(f"Calibration: {args.model}")
    print(f"{'=' * 60}")
    for r in results:
        mark = "PASS" if r["correct"] else "FAIL"
        print(
            f"  [{mark}] {r['fixture_id']}: expected={r['expected']} got={r['verdict']} raw={r['reply_raw']!r}"
        )
    print(
        f"\nScore: {n_correct}/{n_total}  |  Cost: ${total_cost:.6f}  |  {'PASSED' if passed else 'FAILED'}"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
