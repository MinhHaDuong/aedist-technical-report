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
| H3 | frontier cloud fails provenance bar despite acceptable recall | Parser fix 0163 ✓ | Ready |
| H4 | local workstation GPU approaches cloud frontier result quality | H3 complete | Pending H3 |

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

## Phase 2 — Frontier deep-research sweeps: H3 (~$30–50)

- **Models:** 12 frontier cloud models (10 labs)
- **Prompt:** `prompt_complete`
- **Runs:** 12 models × 3 reps = 36 runs
- **Post-run:** method-quality audit — citation validity rate for each output
- **Check after each run:** `finish_reason`, table row count, F1

**Gate:** If F1 < 0.3 across all models AND evaluator confirmed correct → deep research does not achieve acceptable recall; H3 is inconclusive (provenance bar moot). Diagnose before Phase 3.

| H3 outcome | Finding | Implication |
|---|---|---|
| ≥3 models F1 ≥ 0.90 AND all citation validity < 0.50 | **H3 supported** | Gap confirmed — specialised architecture needed |
| Any model achieves F1 ≥ 0.90 AND citation validity ≥ 0.90 | **H3 falsified** | Frontier already clears provenance bar — revisit argument |
| F1 < 0.90 across all models | **Inconclusive** | Result quality not yet acceptable; method bar moot |

---

## Phase 3 — Local model sweeps: H4 (~$0, local compute)

Gated on H3 completing (cloud frontier mean required for gap comparison).

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
      └── Phase 2 (H3)
            └── Phase 3 (H4) — gated on Phase 2 cloud mean
                  └── Phase 4 (X1, X2) — exploratory, no gate

0139 (JobSpec: seed, provider_order, finish_reason) — parallel, improves record integrity
0144 (RAG+reasoning intermediate cell)              — blocked by 0139; future X1 scope
0153 (experiment matrix redesign)                   — unblocked, parallel
```
