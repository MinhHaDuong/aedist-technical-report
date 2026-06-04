Last updated: 2026-06-03T16:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Post-conference — paper writing runway

Econom'IA 2026 talk delivered at Thema/Cergy 2026-05-27. Next: write the paper.

## Current goal

Write the Exp 2 paper sections (0251–0262) and finish cross-eval scoring (0171). `slides-en.tex` is the single source of truth for slide prose; `slides.tex` (FR) is a derived translation (script in flight, 0389). Clean-room writing build landed (0352/0370): `make report` / `make slides` carry no `uv run`, guarded by adherence tests.

## Status
<!-- generated 2026-06-03T16:00Z -->
**Tickets:** 52 ready · 26 blocked — `erg ready tickets/` for full list
**Recent commits:**
  9ff41e25 tickets: log 0396-collision recurrence on 0390
  cfa08bc1 ticket(0319): close as already-done — stale worktrees 0303-0309
  32429feb tickets: open 0401 + 0402 (level schema / capacity coherence)
  b8892bd4 tickets: renumber 0396/0397 -> 0398/0399/0400
  84a81b18 report: ground the open-world dark figure in bound-coherence (HDR ch.8)

## Workplan

1. Experiments 1/2/3 — DONE (runs, analysis, figures, messages A–D).
2. Manuscript + slides — DONE (conference delivered 2026-05-27).
3. Clean-room build split (0352/0370) — DONE; writing build = artifacts only.
4. Paper writing — ACTIVE: Exp 2 sections (0251–0262), cross-eval scoring (0171).

## Backlog / deferred

- Slides EN→FR translation script (0389), in flight (anteriority + FR-clean guarded).
- Reproducibility oracle (0360); mart 2×2 rename (0364, default won't-do).
- New research track 0396–0400 (latent-truth fusion, quality gates) — needs scoping into bounded sub-tickets.
- Hygiene: `origin/chore/restore-panel-state` (1 unmerged commit) and local `ticket/0345` (3 unmerged commits) need manual review before deletion.
- Mart staleness (0383): full-DAG runs rewrite committed scores until the 0384–0386 redress lands — do not run analysis make targets casually.

Housekeeping: last run 2026-06-04T06:35Z (archived 0319/0353/0366, closed-header fix 0382, pruned merged remote, branch cleanup).
