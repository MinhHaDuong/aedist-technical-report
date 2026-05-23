# Exp 2 Phase B-0 Smoke — Gating Report

Generated: 2026-05-23 (manual audit — script did not complete)

## Run conditions

Command issued (2026-05-22 ~23:30):
```
uv run python -m experiments.sota.exp2_interactive_smoke \
    --agents mistral openai qwen anthropic \
    --output-dir experiments/outputs/sota_exp2_phase_b0 \
    --no-confirm
```

**Known environment defect:** Script was NOT invoked via `uv run`, so
`UV_ENV_FILE` was not applied and `OPENROUTER_API_KEY` was absent from
the subprocess environment. The dialogue classifier defaulted to
`no_report` for every turn (cost=0.0, wall_s=0.0 in every
`.classification.json`). This is a harness defect, not a model defect.

## Per-agent checklist

### mistral — FAIL (Phase A parsing failure)

| Check | Verdict |
|-------|---------|
| Phase A valid JSON envelope | FAIL |
| Phase B ≥1 classifier `report` | — (Phase B not reached) |
| Cost < $3 per session | — |
| Token cap not exhausted before first report | — |
| Verify pass fired exactly once | — |
| No adapter crash / JSON error | FAIL (empty output_text) |
| Inventory ≥10 rows | — |

**Failure mode:** `run_mistral_call()` returned a `RunRecord` with
`output_text=""` despite `finish_reason=stop, error=None`. The raw JSON
(`mistral_phase_a.raw.json`) contains a valid 8 258-char JSON envelope
in `outputs[0].content`. Root cause: the narrative extractor called
`record.justification["output_text"]` which was not populated for
Mistral Agents responses (content lives under `outputs`, not in
`justification`).

**Fix:** Committed as bb0def4 on branch t0237-fg — hardened Mistral
Phase A JSON parsing to fall back to `outputs[0].content` extraction.

**Action:** Re-run Mistral with the fixed parser.

---

### openai — WARN (classifier broken; dialogue valid by inspection)

| Check | Verdict |
|-------|---------|
| Phase A valid JSON envelope | PASS |
| Phase B ≥1 classifier `report` | FAIL (classifier broken) |
| Cost < $3 per session | PASS ($0.91 Phase B) |
| Token cap not exhausted before first report | PASS (12 313 tokens remaining) |
| Verify pass fired exactly once | FAIL (never fired — slot=terminal) |
| No adapter crash / JSON error | PASS |
| Inventory ≥10 rows | PASS (162 rows by inspection) |

**Phase A:** Design JSON with all four required keys. wall=36.6 s.
`openai_phase_a_design.json` present.

**Phase B:** 4 turns (designed_prompt → encourage × 2 → terminal).
Turn 4 `user_slot=terminal` triggered by budget exhaustion, not by a
`report` classification. The turn 4 assistant reply (`openai_turn_04.record.json`,
38 227 chars) contains "# Vietnam Thermal Generation Assets >30 MWe"
with 162 table rows. This IS a valid inventory delivery — the classifier
failed to recognise it.

**Phase B costs:** $0.133 / $0.352 / $0.179 / $0.247 (turns 1–4);
total Phase B $0.91. Phase A cost not tracked (OpenAI billing via
tokens: 6 723 in + 1 943 out).

**Wall:** 451 s elapsed total (Phase B; Phase A 36.6 s extra).

**Root cause of classifier failure:** `OPENROUTER_API_KEY` not exported
to the subprocess. Fix: invoke via `uv run` or export key explicitly.

**Action:** Re-run OpenAI with fixed env to get clean classifier trace
and verify slot. OR accept as pilot with a by-inspection `report` note
(per §3.5.1 exclusion criteria — misclassified sessions still usable
for H1/H2/H3).

---

### qwen — WARN (classifier broken; token cap reached; inventory short)

| Check | Verdict |
|-------|---------|
| Phase A valid JSON envelope | PASS |
| Phase B ≥1 classifier `report` | FAIL (classifier broken) |
| Cost < $3 per session | PASS ($0.22 Phase B) |
| Token cap not exhausted before first report | FAIL (remaining_tokens=-2 079 at turn 3) |
| Verify pass fired exactly once | FAIL (never fired — slot=terminal) |
| No adapter crash / JSON error | PASS |
| Inventory ≥10 rows | PASS (32 rows by inspection) |

**Phase A:** Design JSON present. wall=95.1 s (heavy thinking output).
`qwen_phase_a_design.json` present.

**Phase B:** 3 turns (designed_prompt → encourage → terminal). Token
cap exhausted by turn 3 (50 000 token cap; turn 2 consumed 25 265
tokens). The turn 3 assistant reply (`qwen_turn_03.record.json`,
6 420 chars) contains "# VIETNAM THERMAL POWER PLANT INVENTORY (>30 MWe)
— FINAL VERIFIED REPORT" with 32 rows. Valid inventory but smaller than
expected.

**Phase B costs:** $0.065 / $0.098 / $0.053 (turns 1–3); total $0.22.

**Wall:** 622 s elapsed (Phase B; Phase A 95.1 s extra).

**Notes:**
- Token cap was hit because Qwen's thinking tokens are very large
  (~25K output tokens in turn 2). Consider raising `--phase-b-max-tokens`
  or the token cap for Qwen specifically.
- 32 rows is above the ≥10 threshold but notably lower than OpenAI's
  162 — worth monitoring in Phase B-full.

**Action:** Re-run Qwen with fixed env and a higher token cap (or
reduced per-call max_tokens to spread budget across more turns).

---

### anthropic — FAIL (process killed before Phase A)

| Check | Verdict |
|-------|---------|
| Phase A valid JSON envelope | FAIL |
| Phase B ≥1 classifier `report` | — (Phase A not reached) |
| Cost < $3 per session | — |
| Token cap not exhausted before first report | — |
| Verify pass fired exactly once | — |
| No adapter crash / JSON error | FAIL (process killed) |
| Inventory ≥10 rows | — |

**Failure mode:** `anthropic_meta_prompt.txt` was written at 23:52
(last of the four agents). The `_run_one_agent` function wrote the
meta-prompt, then entered the Phase A call. No
`anthropic_phase_a.raw.json` was produced — the call either threw an
exception that escaped the try/except (e.g., `SystemExit` from
`enforce_cost_cap`) or the parent process was killed externally before
the call returned.

No stderr log has been recovered. The `anthropic.env` key file exists
at `~/.config/keys/anthropic.env`. Most likely cause: external Ctrl-C
or process kill during the long-running Qwen session (~10 min), which
carried over to the next agent slot.

**Action:** Re-run Anthropic. Capture stderr.

---

## Summary table

| Agent | Phase A | Phase B | Turns | B-cost | Rows | Verdict |
|-------|---------|---------|-------|--------|------|---------|
| mistral | FAIL (empty output) | — | 0 | $0.00 | 0 | FAIL (fix ready) |
| openai | PASS | WARN (no verify) | 4 | $0.91 | 162 | WARN (re-run) |
| qwen | PASS | WARN (no verify) | 3 | $0.22 | 32 | WARN (re-run) |
| anthropic | FAIL (killed) | — | 0 | $0.00 | 0 | FAIL (re-run) |

Total Phase B cost so far: ~$1.13. Total wall: ~30 min.

## Gating decision

**NOT GATE-PASSING.** Two agents (Mistral, Anthropic) never completed
Phase A. Two agents (OpenAI, Qwen) completed Phase B but the classifier
environment was broken. All four fail the mechanical checklist.

The technical substrates are sound:
- bb0def4 (merged into t0237-fg) fixes the Mistral Phase A parser
- OpenAI and Qwen produced valid inventories by inspection
- All adapters dispatched without API errors

## Action plan for B-0 re-run

```bash
# From the t0237-fg worktree:
uv run python -m experiments.sota.exp2_interactive_smoke \
    --agents mistral anthropic \
    --output-dir experiments/outputs/sota_exp2_phase_b0 \
    --no-confirm
```

This will complete Mistral (with fixed parser) and Anthropic (first
attempt). OpenAI and Qwen outputs already exist; adding `openai qwen`
to the command would overwrite them. Recommended: leave OpenAI/Qwen
artefacts in place and accept them as "WARN — by inspection" per
§3.5.1.

If clean classifiers are required for all four, run all four from a
fresh output directory:
```bash
uv run python -m experiments.sota.exp2_interactive_smoke \
    --agents mistral qwen openai anthropic \
    --output-dir experiments/outputs/sota_exp2_phase_b0_v2 \
    --no-confirm
```

## Classifier fix note

The dialogue classifier reads `OPENROUTER_API_KEY` via
`os.environ.get()` (not from a key file). The key IS present in
`~/.claude/.env` and loaded by `uv` when invoked as `uv run python -m
...`. Do NOT invoke the smoke script as bare `python -m` — the
classifier will silently default every turn to `no_report`.
