# Protocol — Doc 06: Validation round 1 — changes made and not made

Round 1 of the validation was run on 2026-05-21. The four subject agents reviewed the v1 protocol; all four returned `ACCEPT-WITH-RESERVATIONS`. This document records, per concern raised, whether the current revision addresses it (and how) or acknowledges it as an open limitation (and why).

Round 1 review artefacts are committed under `experiments/outputs/sota_exp2_protocol_review/`. Companion documents to the present revision: Doc 01 (the ask), Doc 02 (Phase A meta-prompt verbatim), Doc 03 (example dialogue), Doc 04 (implementation), Doc 05 (experiment).

---

## 4.1. Round-1 verdicts

| Agent | Verdict | Top-line concerns |
|---|---|---|
| Claude Opus 4.6 | ACCEPT-WITH-RESERVATIONS | dollar/token parity; classifier bias; small n; reference-dataset provenance; thinking-tokens-in-budget |
| GPT-5.5 | ACCEPT-WITH-RESERVATIONS | task too large for the budget; state-machine biases toward early reporting; classifier bias; dollar/token parity; plant-counting / multi-phase complexes; pre-FID scope; what counts as "primary source"; cross-eval rubric transparency |
| Mistral Large 2512 | ACCEPT-WITH-RESERVATIONS | classifier bias (Mistral classifying Mistral); source-quality criteria; temporal conflict resolution; rubric transparency; budget calculation clarity |
| Qwen3-Max | ACCEPT-WITH-RESERVATIONS | classifier bias; dollar/token parity; strong-citation aggregator policy; local-language source availability |

---

## 4.2. Concerns that the current revision addresses (✓)

| # | Concern (raised by) | How addressed | Where |
|---|---|---|---|
| 1 | Classifier bias — same-vendor pair (all four) | Classifier replaced with `nvidia/nemotron-nano-9b-v2` via OpenRouter; cross-vendor with all four subjects | Doc 04 §2.2; Doc 05 §3.5 |
| 2 | Dollar/token parity (Anthropic, OpenAI, Qwen) | Dual-axis cap: 50K tokens (visible + thinking, retrieval excluded) + $3 dollar guard, per Phase B session | Doc 04 §2.3; Doc 05 §3.5 |
| 3 | State machine biases toward early reporting (OpenAI) | Phase A meta-prompt now includes a planning-headroom paragraph explicitly telling the agent the three-encouragement budget is planning space | Doc 02 (CONTEXT > Planning headroom) |
| 4 | Reference-dataset epistemic status (Anthropic) | §3.3 reframes the reference as a methodological artifact; F1 measures concordance, not correctness | Doc 05 §3.3 |
| 5 | Thinking tokens in budget (Anthropic) | Doc 04 §2.3: thinking tokens counted toward 50K cap; explicit |
| 6 | Cross-evaluation rubric transparency (Anthropic, Mistral, OpenAI) | Commitment to publish the rubric and raw inter-rater scores alongside the manuscript | Doc 05 §3.5 |
| 7 | Plant-counting / multi-phase complexes (OpenAI) | Q3.6.1 — each plant in a power center gets one row; the power center itself is referenced in narratives | Doc 05 §3.6.1 |
| 8 | CHP / industrial captive scope (OpenAI) | Q3.6.2 — all plants > 30 MWe in scope regardless of grid connection or cogeneration | Doc 05 §3.6.2 |
| 9 | Pre-FID / cancelled scope (OpenAI) | Q3.6.3 — all lifecycle statuses in scope; pre-FID counts if in formal planning cycles | Doc 05 §3.6.3 |
| 10 | Source-quality hierarchy (Mistral, OpenAI) | Q3.6.4 — 6-tier method-general hierarchy; no instance-specific source examples | Doc 05 §3.6.4 |
| 11 | Source-conflict resolution (Mistral) | Q3.6.5 — higher-tier as Source 1; equal-tier disagreement noted | Doc 05 §3.6.5 |
| 12 | Secondary aggregator policy (Qwen) | Q3.6.6 — admissible if they cite a verifiable primary | Doc 05 §3.6.6 |
| 13 | Budget calculation clarity (Mistral) | Doc 04 §2.3 explicit table: what counts, what doesn't, on each axis |
| 14 | Refusal handling (implicit in all reviews) | Q2.10.3 — refusal is data; recorded as outcome | Doc 04 §2.10.3 |
| 15 | Subagent dispatch — author addition | §2.5 explicit forbid with per-provider concrete prohibitions; rationale in Doc 05 §3.5 | Doc 04 §2.5; Doc 05 §3.5 |
| 16 | Wikipedia leakage — author addition | §3.4 disclosure; not admissible as Source 1/2; Phase D audit on citation count | Doc 05 §3.4; Doc 04 §2.5 |
| 17 | Verdict line format (Anthropic put in code fence) | Tightened: single line, plain text, no fence, last non-blank line of response | Doc 01 |
| 18 | Local-language source policy (Qwen) | Q3.6.7 — local-language sources are valuable, not required; original + English translation when used | Doc 05 §3.6.7 |
| 19 | Clarifying questions during run (implicit) | Q2.10.5 — clarification is `no_report`, consumes an ENCOURAGE; prefer round-1 review | Doc 04 §2.10.5 |
| 20 | Method-neutrality (author addition) | The protocol is split into Method (Doc 04 + Doc 05 §3.5–3.8) and Trial (Doc 05 §3.1, 3.3–3.4, 3.6); the method is reusable across future trials | Doc 05 framing |

---

## 4.3. Concerns acknowledged but not addressed (○)

| # | Concern (raised by) | Status | Reason |
|---|---|---|---|
| A | Small n = 3 (Anthropic) | Open limitation | Higher N would push past the ~$48 batch ceiling. Documented for future replication |
| B | Task too large for the per-session budget (OpenAI) | Open limitation | Acknowledged in Doc 05 §3.5; the dual-axis cap (50K + $3) is the primary capacity constraint and is more permissive than v1's $10. Mistral's smoke at $0.25 / 12K tokens suggests tractability; Opus / GPT-5.5 may have less slack |
| C | Parametric-recall leakage from training data (implicit) | Open limitation | Cannot be controlled at run time. Post-hoc analysis will flag suspicious parametric-recall fingerprints. See Doc 05 §3.4 |
| D | Energy / CO₂ are not exposed (author addition) | Open limitation | Acknowledged in Doc 04 §2.3 and Doc 05 §3.8. Dollar cap is a proxy; the paper calls for standardised vendor disclosure |
| E | Cross-evaluation incentive structure (Anthropic) | Open limitation | Each agent scores its competitors; systematic stylistic preferences could correlate. A blinded human adjudicator subset is desirable but out-of-scope for this run; documented |
| F | OpenAI's "what counts as a primary source" — was answered with tier hierarchy (Q3.6.4) but the underlying concern is that mid-tier and tier-1 are not always cleanly separable for a given domain | Partially addressed | The tier hierarchy is the experimenter's contract; agent judgement at the boundary is part of the task |
| G | OpenAI's concern that Phase A spending eats into each Phase B replicate | Addressed differently | The per-Phase-B budget ($3) is independent of Phase A; Phase A has its own $1 cap. The aggregate per-agent ($10 = $1 A + 3 × $3 B) holds. See Doc 04 §2.3 |

---

## 4.4. Concerns added by the experimenters between rounds

These were not raised by any round-1 reviewer but the experimenters identified them during revision:

| # | Concern | Addressed in |
|---|---|---|
| α | The reference inventory has been published to Wikipedia by the authors; agents may cite it as a "primary source" without realising it is the experimental reference | Doc 05 §3.4 (disclosure + ban); Doc 04 §2.5 (Wikipedia citation rule) |
| β | Subagent dispatch (panel-of-experts patterns, Claude Task, OpenAI handoff) would externalise cost and silently change what's being measured | Doc 04 §2.5 (forbidden list); Doc 05 §3.5 (rationale) |
| γ | The original protocol was monolithic; reviewers had to re-derive parts of the design | Doc structure: this 5-document split, with a clear method-vs-trial boundary |
| δ | The verdict-line format was not tightly specified in round 1; one reviewer placed it inside a code fence that the extractor caught by luck | Doc 01 — explicit format constraints |
| ε | The method-vs-trial boundary was implicit; round-1 reviewers had to infer which constraints were experimenter-mandated vs trial-specific | Doc 05 framing — Method (sector- and country-neutral) vs Trial (Vietnam thermal) split |
