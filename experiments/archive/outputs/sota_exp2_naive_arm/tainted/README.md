# Tainted Runs — Anthropic Arm 1 (naive, no evidence pack)

## Why tainted

These 5 runs (anthropic_run01–05) were **double-constrained** by two harness bugs:

### Bug 1 — search cap `max_uses=5` (binding)

All 5 runs hit the `web_search_20250305` cap on every call:

| Run | Web searches | Cap |
|-----|-------------|-----|
| anthropic_run01 | 5 | 5 (binding) |
| anthropic_run02 | 5 | 5 (binding) |
| anthropic_run03 | 5 | 5 (binding) |
| anthropic_run04 | 5 | 5 (binding) |
| anthropic_run05 | 5 | 5 (binding) |

The correct limit is `max_uses=20` (≈$0.20 per call), as established in PR #489
(merged 2026-05-24).

### Bug 2 — output truncated at `max_tokens` (binding)

All 5 tainted runs hit `stop_reason=max_tokens` at ~16,400 output tokens (confirmed
from `raw_response.usage`). The model was cut off mid-report every time:

| Run | `output_tokens` | `stop_reason` | chars |
|-----|----------------|---------------|-------|
| anthropic_run01 | 16418 | max_tokens | 13957 |
| anthropic_run02 | 16449 | max_tokens | 28162 |
| anthropic_run03 | 16429 | max_tokens | 29083 |
| anthropic_run04 | 16427 | max_tokens | 13774 |
| anthropic_run05 | 16447 | max_tokens | 13505 |

The `max_tokens=32000` parameter (ANTHROPIC_MAX_TOKENS) was set correctly, but adaptive
thinking consumed roughly half the token budget, leaving only ~16K for text output. The
corrected runs with `max_uses=20` produce 38–50K chars (runs hit 32K token output cap, not
thinking-constrained) — substantially more complete reports.

## Why this matters

For the 2×2 factorial analysis (grounding × interaction mode):
- The **interaction mode** contrast (Arm1 single-shot vs Arm2 multi-turn) is
  biased: multi-turn spread searches across turns (3–4/turn), never hitting
  the cap, while single-shot was constrained.
- The **grounding** contrast (Arm1 no-EP vs Arm3 with-EP) is also affected:
  Arm1 was constrained, Arm3 original run used only 4 searches (not binding).

## Disposition

Replaced by corrected runs in the parent directory (`anthropic_run01–05.{json,md}`),
produced with `max_uses=20` after PR #489 merged.

These files are retained for provenance. The analysis pipeline (`tabulate_exp2_arms_runs.py`)
uses `glob("*.json")` on the parent directory and does not recurse into `tainted/`,
so these files are invisible to all downstream analysis.
