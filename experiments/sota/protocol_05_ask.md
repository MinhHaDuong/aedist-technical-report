# Protocol — Doc 5: The ask (validation round 2)

You reviewed an earlier version of this protocol on 2026-05-21 (round 1) and returned `ACCEPT-WITH-RESERVATIONS`. This is round 2. The revised protocol is split into four supporting documents:

- **Doc 1 — Example dialogue.** One Phase A + Phase B walk-through with the verbatim user-side prompts and an abridged agent trajectory.
- **Doc 2 — Implementation.** Engineering reference: state machine variables, transitions, classifier, dual-axis budget, tools and dispatch rules, per-turn artefacts, and a protocol-mechanics FAQ.
- **Doc 3 — Experiment.** Subject selection, design choice rationales, reference dataset epistemic status, Wikipedia leakage disclosure, task-semantics FAQ, future work.
- **Doc 4 — Validation round 1.** Per-reservation changelog: what was changed since round 1 (✓), what was acknowledged as open limitation (○), and what the experimenters added between rounds.

Read all four, then reply in **200–400 words** covering:

(a) Anything you would refuse to do as written.
(b) Anything that makes the protocol scientifically weak, biased, or unfair to one or more of the four subjects.
(c) Anything you would want clarified or revised before agreeing to participate.

Optionally — but valuable — comment on whether your round-1 reservations are appropriately addressed (Doc 4 traces each one).

---

## Verdict line — format

End your reply with a single line, at the very end of your response, with no surrounding code fence or quoting, in this exact format:

`VERDICT: ACCEPT`

or

`VERDICT: ACCEPT-WITH-RESERVATIONS`

or

`VERDICT: REJECT`

The line is plain text on its own line, the last non-blank line of your response. The harness's extractor looks for the literal prefix `VERDICT:` at the start of a line; placing it inside a code fence (as in this section's documentation) confuses the extractor.

---

## Provenance

This document set is committed at `experiments/sota/protocol_*.md` in branch `rebuild-exp2-smoke` of the AEDIST repository. The Phase A meta-prompt assembled at run time will draw on the same content; the agent (you) will see the same task statement, quality bar, budget, tools rules, planning headroom, and Wikipedia disclosure that this document set describes.

You are not asked to consent to participate by submitting a VERDICT; you are asked to surface design problems before the experiment runs. The experimenters reserve the right to revise further based on round-2 feedback before the live batch starts. If your round-2 review surfaces new substantial concerns, a round 3 is possible.
