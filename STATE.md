Last updated: 2026-05-27T23:15Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Post-conference — paper writing runway

Econom'IA 2026 talk delivered at Thema/Cergy 2026-05-27. Next: write the paper.

## Current goal

Post-conference slides review done (PRs #615/#616). Open paper-writing tickets.

## Status
<!-- generated 2026-05-27T22:00Z -->

**Tickets:** 29 ready · 20 blocked — `erg ready tickets/` for full list
**Recent commits:**
  4948b617 chore: rebuild exp2 generated artifacts (side effect of analysis.mk)
  c3bbdf83 fix(fig): E1 FP bars on coverage; larger condition labels
  e9dc00e5 fix(slides): rebuild figs 16+17 with restored labels; fix hallucinations term
  25018257 slides: hide RAG table (19), soften conclusions wording
  7e0e386a slides(21): top-align Limites frame content

## Workplan

1. **Experiment 3 runs.** DONE.
2. **Experiments analysis.** DONE — Exp 1/2/3 figures produced, take-home messages A–D ratified.
3. **Update manuscript.** DONE — 0313–0318 closed.
4. **Update slides.** DONE — conference delivered 2026-05-27.
5. **Post-conference cleanup.** DONE — PRs #606/#612/#615/#616 merged, regressions fixed.
6. **Paper writing.** Opens next.
7. **Report/ablation cleanup.** Planning done (merged #627): tickets 0360/0361/0362 ready, 0352 re-scoped — see Handoff.

## Handoff — report/ablation cleanup (merged via #627)

Run order: **0361 → 0362 (rebased) → 0352 → 0353 ∥ 0360**. Every ticket body carries its first test + literal scope. NB 0361/0362 are NOT independent: both delete a token from `Makefile:256` (`tables:`) — serialize, do not fan out to parallel worktrees. 0360 is `Blocked-by: 0352` (sequencing), so it starts after 0352, not now.

- **0361** retire §Exp3 modular ablation (designed, never ran; pilot invalidated). NOT a wholesale rm: salvage the verification paragraphs (multi-turn ⊂ verification; per-row sourcing → independent verifier) into **Discussion**; CUT the "information regime" construct (replaced by the observable product-features framing already live in the slides 2×2); acknowledge decomposition (divide & conquer) as non-priority. Deletes `base_vs_census` + the hard-broken figs; fixes the duplicate "Expérience 3" heading (`sec:exp3` vs `sec:rag`). KEEP `sec:direct_complete`.
- **0362** reconcile report Exp2 onto the live 2×2 features design (slides already use `tab_exp2_2x2`; report still on stale `tab_exp2_arms` + 4 arms scripts). Reconciliation, not deletion — Exp2 is live.
- **0352** clean-room report build (no `uv run` in `make report`; rules → `experiments/analysis.mk`), re-scoped to run on the pruned tree. NB its append-only log still says "0358" — historical; real blockers are 0361/0362.
- **0360** clean/cleaner reproducibility oracle (content-diff, **no timestamps**). `Blocked-by: 0352` (sequencing only) — runs after 0352, in parallel with 0353.

Root cause behind the dead figures: the `prompt_version` tag was dropped in the 0297/0344 mart rebuild → census/ablation figures filter to empty (data untagged, not lost).

Gotchas: the prior agent-352 attempt at 0352 (recover/freeze figures) is **abandoned** — discard that WIP branch. 0354 dedup (`experiments/common.mk`) already merged here.

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens now.
- Report/ablation cleanup (0360/0361/0362; 0352 re-scoped + Blocked-by 0361/0362; 0353 after 0352) — see Handoff.
- CI required-checks rule disabled 2026-05-26 — **re-enable** (talk done, no longer blocking).
- Stale remote branches to prune: `origin/score-4-arms-2x2`, `origin/chore/restore-panel-state`.
- `ticket/0345-collapse-exp2-single-producer` local branch has 3 pre-PR commits not in main — manual review before deleting.
