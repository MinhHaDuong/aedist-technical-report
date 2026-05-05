# Experiment roadmap — Does deep research saturate the measurement task?

*Working document. Update after each phase gate.*
*Last revised: 2026-05-05*

---

## Central question

**Does deep research produce a complete, primary-sourced, coherent thermal power
inventory — not only high F1, but across all quality scales the prompt requests?**

This is H1 (reformulated). See §Hypothesis below.

---

## Hypothesis H1 (reformulated)

> **H1 — Deep-research completeness (cloud).** A frontier cloud model running
> `prompt_complete` with reasoning and web search produces an inventory that
> satisfies all four of:
>
> (a) **Plant-table F1 ≥ 0.988** — matches or exceeds the current decomposed-RAG
>     ceiling on the coal-only dev subset.
> (b) **Source-grounding rate ≥ 80%** — at least 80% of emitted citations resolve
>     to a real primary source that contains the claimed fact.
> (c) **No systematic truncation** — `finish_reason = "stop"` on ≥ 2/3 runs;
>     output is not cut short by the token ceiling.
> (d) **Statistical coherence** — the 4 cross-tabulations are internally
>     consistent with the plant inventory table (column/row totals correct).
>
> H1 is supported if ≥ 2 of 3 selected frontier models satisfy all four criteria
> in the pilot (§Phase 1). H1 is falsified if no model satisfies all four, or if
> criterion (a) fails for all models after the evaluator is confirmed correct.
>
> *Note: F1 alone is necessary but not sufficient. A model that scores F1 = 1 on
> a truncated or unsourced response does not satisfy H1.*

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

## Phase 0 — Clear the runway (today)

| Action | Owner | Status | Ticket |
|---|---|---|---|
| Diagnose F1=0.000 runs (evaluator bug or model failure?) | agent | open | 0163 |
| Verify model prices before budgeting | agent | open | 0164 |
| Submit OSF preregistration, get DOI | **human** | pending — form ready | 0150 |
| Prompt meta-review by 3 SOTA agents | agent | needs go-ahead | — |
| Raise output token ceiling (32K → 64K) | agent | **done** | — |

**Gate:** 0163 resolved + evaluator confirmed correct before any pilot run counts.

---

## Phase 1 — Pilot runs (~$5–10)

- **Models:** 3 frontier cloud models (Claude Opus 4.6, DeepSeek R1, + 1 TBD)
- **Prompt:** `prompt_complete.txt`
- **Runs:** 3 per model (9 total)
- **Check after each run:**
  - `finish_reason` — any `"length"` → context ceiling still too low
  - Table row count — < 50 rows suggests model failure or evaluator bug
  - F1 from evaluator (after 0163 confirmed)

**Gate:** If F1 < 0.3 across all models AND evaluator confirmed correct → H1 is
falsified at pilot stage. Stop, diagnose, update argument.

---

## Phase 2 — Raise barriers (this week)

| Action | Ticket | Why needed before full runs |
|---|---|---|
| JobSpec: add seed, provider_order, finish_reason | 0139 | Scientific record integrity; detect truncation in measurements.jsonl |
| Redesign experiment matrix along hypotheses | 0153 | Avoid redundant runs; map each sweep to a hypothesis |
| OSF registration frozen | 0150 | Confirmatory claim requires pre-registration |
| RAG + reasoning intermediate cell | 0144 | Tests H3 (Coherence limit isolation); blocked by 0139 |

---

## Phase 3 — Full runs (~$30–50)

- Full frontier set (10 models) × 3 reps × `prompt_complete`
- Local: `qwen3.5:122b` × 3 reps (parametric — deep research requires harness extension)
- Ablation: module-by-module contribution (ticket 0143)
- RAG + reasoning cell for H3 (ticket 0144)

---

## Phase 4 — Verdict table

| Outcome | H1 verdict | Slides argument |
|---|---|---|
| ≥ 2/3 frontier models satisfy all 4 criteria | **Supported** | Stage 5 works; stage 6 is about method quality (audit, provenance) |
| F1 ≥ 0.988 but sourcing / coherence fails | **Partial** | Stage 5 closes F1 gap; stage 6 adds verifiability |
| F1 0.5–0.95, truncation-free, evaluator correct | **Inconclusive** | Stage 5 insufficient; stage 6 needed to close empirical gap |
| F1 < 0.5 after evaluator fix confirmed | **Falsified** | Deep research does not saturate; stage 6 is necessary, not optional |
| F1 = 0 and evaluator bug | **Measurement failure** — fix evaluator, rerun | — |

---

## Dependency graph

```
0163 (evaluator fix)
  └── Phase 1 pilots
        └── 0139 (JobSpec + finish_reason)
              └── 0144 (RAG+reasoning cell)
                    └── Phase 3 full runs
                          └── H1 verdict

0150 (OSF preregistration)  ← human action, parallel
0153 (experiment redesign)  ← unblocked, parallel
```

---

## Local deep-research agent

Ollama alone is **not sufficient** for deep research. Needed:
1. A model with tool-calling capability — `qwen3.5:122b` ✓
2. A local search backend (Tavily API or self-hosted SearXNG)
3. Harness extension to route web-search tool calls for local models

**Immediate option:** run `qwen3.5:122b` with `prompt_complete` parametrically
(no web). This tests H2 at stage 1–4, not stage 5. Wire local web search as
a separate harness ticket after Phase 1.
