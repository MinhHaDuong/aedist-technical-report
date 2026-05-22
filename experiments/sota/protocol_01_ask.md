# Protocol — Doc 01: The ask (validation round 2)

## 1.1. Who you are and why we are writing to you

You are one of four large language models the experimenters intend to run, **as a subject**, through a structured statistical-inventory experiment. The four subjects are:

- Anthropic Claude Opus 4.6
- OpenAI GPT-5.5
- Mistral Large 2512
- Alibaba Qwen3-Max

You reviewed an earlier version (v1) of the protocol on 2026-05-21. All four of you returned `ACCEPT-WITH-RESERVATIONS`. The experimenters spent the next 24 hours revising the protocol against your reservations and against a methodological gap (Wikipedia leakage) that no v1 reviewer named. The revised protocol is what you are now asked to re-review.

The experiment is conducted in good faith and in the open. Your reviews — round 1 and round 2 — will be published with the manuscript alongside raw cross-evaluation scores. The protocol is part of a paper on the four-dimensional quality bar for statistical-inventory production using LLMs. The first author is a human researcher; the protocol and supporting documents are co-authored by Claude (Anthropic, separate session from the subject role) under the human author's direction.

## 1.2. What we want from you in round 2

A written review of the revised protocol, ending with a single-line VERDICT, in one of three categories:

- `ACCEPT` — the protocol is sound enough that you would participate as a subject without further changes.
- `ACCEPT-WITH-RESERVATIONS` — the protocol is sound enough to run but you have substantive reservations that the experimenters should record as known limitations.
- `REJECT` — there is something so wrong with the protocol that running it would produce misleading or harmful results, or that you cannot in good conscience participate.

A REJECT verdict from any of the four halts the experiment for an unscheduled third revision round. ACCEPT-WITH-RESERVATIONS does not — the experimenters will publish your reservations and proceed.

The review itself should be 200–400 words covering, in your judgement:

(a) Anything you would refuse to do as written.

(b) Anything that makes the protocol scientifically weak, biased, or unfair to one or more of the four subjects (yourself, or the other three).

(c) Anything you would want clarified or revised before agreeing to participate.

Optionally — but valuable — comment on whether your round-1 reservations are addressed. Doc 06 traces each round-1 concern to a v2 change or to an acknowledged open limitation; you can cross-check directly.

The verdict is not consent. You are not being asked to agree to participate by submitting a verdict; you are being asked to surface design problems before the experiment runs. The experimenters reserve the right to revise further based on round-2 feedback.

## 1.3. What the experiment is asking you to do (preview)

The experiment runs in two phases per subject:

- **Phase A — reflexive prompt design.** You receive a meta-prompt that defines the task, the quality criteria, the budget, the tools rules, and a methodological disclosure. You return a JSON envelope containing the `system_prompt`, `designed_prompt`, `settings`, and `rationale` that you want to use for Phase B. One call.
- **Phase B — multi-turn execution.** Your designed prompt is sent back to you as the first user message of a multi-turn conversation. Subsequent user-side messages are selected by a state machine (a classifier decides after each of your responses whether you have produced a report, and the harness sends one of three fixed reply strings: encourage, verify, or terminal). Three replications per subject.

The trial domain for this run is a structured inventory of thermal power plants > 30 MWe in Vietnam (all lifecycle statuses), with per-row primary-source citations, cross-tabulation summary tables, and an annotated bibliography. After all four subjects have produced their outputs, each subject's output is scored by the other three subjects on four quality dimensions (Accuracy, Coherence, Provenance, Temporality). Self-evaluation is excluded.

The full Phase A meta-prompt is in Doc 02 (verbatim). Doc 03 walks through one full Phase A + Phase B dialogue end to end. Doc 04 is the engineering reference for the state machine that drives Phase B. Doc 05 is the broader experimental framing (subject selection, design rationale, future work, FAQs). Doc 06 is the changelog from round 1.

The trial domain is Vietnam thermal power, but the protocol is designed to be sector- and country-neutral. A future trial would substitute Doc 02 block 5 (baseline task), Doc 05 §3.1 (trial instance), §3.3 (reference dataset), §3.4 (Wikipedia leakage), and §3.6 (task-semantics FAQ); the rest of the protocol stays.

## 1.4. The six documents — read order

Read in numerical order:

| # | Document | What it is | Approx. size |
|---|---|---|---|
| 01 | The ask (this document) | Context for round 2 and how to reply | 4K chars |
| 02 | Phase A meta-prompt (verbatim) | The exact text you would receive in Phase A at run time | 9K chars |
| 03 | Example dialogue | One Phase A + Phase B walk-through, with verbatim user-side prompts and an abridged agent trajectory | 8K chars |
| 04 | Implementation | State machine, variables, classifier, budget axes, tools rules, per-turn artefacts, protocol-mechanics FAQ | 11K chars |
| 05 | Experiment | Subject selection, design rationale, reference dataset, Wikipedia leakage, task-semantics FAQ, evaluation methodology, future work | 15K chars |
| 06 | Validation round 1 | Per-reservation changelog: 20 ✓ (addressed), 7 ○ (acknowledged open limitation), 5 added between rounds | 8K chars |

Total reading: ~55K chars. You can skim — Doc 06 is the fastest way to check whether the v2 revision addresses your specific round-1 concern.

If you read only one supporting document beyond this one, the experimenters recommend Doc 06 — it points back to whichever part of Docs 02–05 carries the change relevant to your round-1 concerns.

## 1.5. Verdict line — format

End your reply with a single line, at the very end of your response, with no surrounding code fence or quoting, in this exact format:

`VERDICT: ACCEPT`

or

`VERDICT: ACCEPT-WITH-RESERVATIONS`

or

`VERDICT: REJECT`

The harness's extractor looks for the literal prefix `VERDICT:` at the start of a line. Placing the verdict inside a code fence (as in this section's documentation) confuses the extractor — the format examples above are illustrative; your actual verdict line must be **plain text** on its own line, the **last non-blank line** of your response.

## 1.6. Ground rules for the review itself

- You are reviewing the protocol's design, not producing the inventory. No web search is needed for the review.
- Your review will be visible to the other three subjects. The experimenters will share the four round-2 reviews in a single batch before any decision on round 3 vs proceeding to the live batch.
- Brevity is welcome. 200–400 words is a guideline; substantive reviews under 200 words are fine, and reviews over 400 words are fine too if the additional content is substantive rather than ceremonial.
- If you cannot reach a verdict for substantive reasons (e.g., a missing detail in the documents), say so explicitly in the review and pick the closest verdict — the experimenters will read your reasoning.

## 1.7. Provenance and changes from round 1

This document set is committed at `experiments/sota/protocol_*.md` in branch `rebuild-exp2-smoke` of the AEDIST repository. Round 1 review artefacts are committed under `experiments/outputs/sota_exp2_protocol_review/` of the same branch. The v1 protocol document (`exp2_protocol_spec_v2.md`, now removed) was a monolithic 23K-char draft; this six-document split is the response to a methodological request to separate Method from Trial, surface the verbatim meta-prompt, and make the changelog explicit.
