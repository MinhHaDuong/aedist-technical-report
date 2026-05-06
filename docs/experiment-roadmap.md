# Experiment roadmap — AEDIST benchmark

*Working document. Update after each phase gate.*
*Last revised: 2026-05-06*

---

## Central question

**Do the method ladder rungs add measurable F1, and does the frontier
still fail the provenance bar even when result quality is acceptable?**

Four confirmatory hypotheses; see `docs/hypotheses.md` for full
operational definitions and decision rules.

---

## Hypotheses at a glance

| ID | Claim | Precondition | Status |
|----|-------|-------------|--------|
| H1 | direct → multiturn adds measurable F1 (Articulation) | None | Ready |
| H2 | multiturn → RAG adds measurable F1 (Coverage) | None | Ready |
| H3 | parametric single-prompt does not achieve recall + verifiable attribution simultaneously | Parser fix 0163 ✓ | Ready |
| H4 | local workstation GPU approaches cloud frontier result quality | None | Ready |

---

## Quality scales in scope

| Scale | Metric | Currently measured? | Ticket |
|---|---|---|---|
| Plant completeness | F1 (recall × precision) on inventory table | Yes | — |
| Attribute accuracy | F1 on fuel / status / capacity fields | Partially | — |
| Source grounding | Fraction of citations that resolve and contain the claim | No | 0097 |
| Confidence calibration | HIGH/MEDIUM/LOW assignments vs. ground truth | No | — |
| Statistical coherence | Cross-tabs consistent with inventory | No | 0163 scope |
| Output completeness | No truncation (finish_reason = stop) | Manual only | 0139 |

---

## Phase 0 — Clear the runway

| Action | Owner | Status | Ticket |
|---|---|---|---|
| Diagnose and fix evaluator on `prompt_complete` output | agent | **Done** 2026-05-05 | 0163 |
| Verify and update model prices | agent | **Done** 2026-05-06 | 0164 |
| Submit OSF preregistration, get DOI | **human** | Pending — form ready | 0150 |
| Prompt meta-review by 3 SOTA agents | agent | Needs go-ahead | — |
| Raise output token ceiling (32K → 64K) | agent | **Done** | — |

**Gate:** OSF preregistration timestamp must precede any confirmatory sweep runs.

---

## Phase 1 — Method ladder sweeps: H1 and H2 (~$2–5)

Run matched 5-model panels for the two ladder rungs.

- **Models:** 5 matched frontier models (same panel for both rungs)
- **Prompts:** `prompt_extract`
- **Conditions:** direct, multiturn, RAG
- **Runs:** 5 models × 3 conditions × 3 reps = 45 runs (multiturn shared)
- **Check:** paired ΔF1 direction and magnitude per rung

**Gate (H1):** Paired multiturn − direct ΔF1. If reversed (direct ≥ multiturn) for ≥3 models → H1 falsified, investigate prompt design.

**Gate (H2):** Paired RAG − multiturn ΔF1. If reversed for ≥3 models → H2 falsified.

---

## Phase 2 — Parametric attribution sweep: H3 (~$5–10)

Test whether asking for per-row attribution depresses recall in the parametric regime.

- **Models:** Same 5 matched frontier models as Phase 1
- **Condition A:** `prompt_extract`, parametric (reuse Phase 1 direct runs)
- **Condition B:** `prompt_complete`, parametric — no web, no RAG (`sweep_direct_complete_no_web`)
- **Runs:** 5 models × 1 new condition × 3 reps = 15 new runs (Condition A shared with Phase 1)
- **Post-run:** citation validity audit on Condition B outputs

| H3 outcome | Finding | Implication |
|---|---|---|
| Mean ΔF1 < −0.10 AND citation validity < 0.50 | **H3 supported** | Trade-off confirmed — attribution request collapses recall and citations are untrustworthy; single-prompt insufficient |
| ΔF1 > −0.05 AND citation validity ≥ 0.50 | **H3 falsified** | Both achievable in single prompt — revisit architecture argument |
| ΔF1 between −0.05 and −0.10, or citation validity mixed | **Inconclusive** | Partial evidence; cannot conclude |

---

## Phase 3 — Local model sweeps: H4 (~$0, local compute)

Comparison baseline: cloud frontier best on `prompt_extract` (current ceiling F1 = 0.988, from existing direct sweeps). No gate on H3.

- **Models:** `qwen3.5:9b` (parametric baseline) + `qwen3.5:122b` (if deep-research harness ready)
- **Prompt:** `prompt_extract` (parametric) and/or `prompt_complete` (if harness extended)
- **Runs:** 2–4 models × 3 reps = 6–12 runs
- **Gap target:** local mean F1 within 0.05 of cloud frontier mean

**Note on local deep-research:** Ollama alone requires extension for web-search tool calls.
Running `qwen3.5:122b` with `prompt_complete` parametrically (no web) tests H4 at stages
1–4; local web search is a separate harness ticket. The qwen3.5:9b F1 = 0.984 result on
direct extraction (n=1) suggests parametric extraction may suffice.

---

## Phase 4 — Exploratory analyses

After H1–H4 are decided:

- **X1:** Method-quality metrics (citation validity, re-extraction agreement) —
  discriminate single-agent vs. multi-agent verification levels. Requires
  new metric infrastructure (ticket 0097).
- **X2:** Prompt-module ablation — which modules contribute most to F1 across
  regimes (`sweep_ablation_*`, ticket 0143).
- Cost-effectiveness analysis (F1 per dollar across all Phase 2 models).

---

## Dependency graph

```
0150 (OSF preregistration) ← human action — must precede all confirmatory runs
      |
      ├── Phase 1 (H1, H2) — unblocked, run in parallel
      |
      ├── Phase 2 (H3) — parametric attribution sweep, independent
      |
      └── Phase 3 (H4) — local model sweep, independent
                  └── Phase 4 (X1, X2) — exploratory, no gate

0139 (JobSpec: seed, provider_order, finish_reason) — parallel, improves record integrity
0144 (RAG+reasoning intermediate cell)              — blocked by 0139; future X1 scope
0153 (experiment matrix redesign)                   — unblocked, parallel
```
