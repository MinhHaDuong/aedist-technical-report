Last updated: 2026-06-06T12:19Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.md`** — report.tex is internal ("no future", author 2026-06-05). main.md is structurally complete: v2 numbers, Annex E (reworked matrix on a landscape page, #771) + two Discussion future-work paragraphs (#767 fusion, #771 zero-reference coherence screen). **Blocked-by 0445** (extension-as-unit can move 170→174 and every quoted number — author 2026-06-06). Then: blessed acknowledgements, full author read, arXiv build, sign-off. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-06T12:19Z -->

**Tickets:** 45 ready · 28 blocked — `erg ready tickets/` for full list
**Recent commits:**
  e7ef4f96 Merge pull request #771 from MinhHaDuong/ticket/0446-matrix-figure-rework
  51c0efdb ticket(0446): close and archive — PR #771
  93f6ef2e tickets: drop stale open 0456 — closed+archived on main (superseded by 0457); duplicate ID broke erg check after rebase
  b4b23429 Merge pull request #778 from MinhHaDuong/chore/ticket-0457-cohort-filter-test-gap
  491026a3 ticket(0446): log /gaze round-1 reroll

## Sprint 2026-06-05 — CLOSED

Reference v2 (170 plants) adopted end-to-end: snapshot policy → aggregator (#760) → clean resnap (#764, snapshot = sole master copy, durable on main; restore: `git show origin/main:data/reference/raw/pipeline-2026-06-05.ods > <path>`) → adoption (#767: re-score Exp1–3, figures at 170, #547 prose corrected ×3, manuscript annex) → class fix + ratchet ticket (#769, 0447).

## Next actions

1. **0445** — extension-as-unit net measurement; now BLOCKS 0435 + 0444. mở-rộng FPs re-raised at 0446 review.
2. **0435 finalization** — acknowledgements (blessed wording), author read (incl. new coherence-screen paragraph), arXiv build.
3. 0446-review follow-ons: 0453 (two-level coherence scoring), 0455 (preprint figures EN sweep), 0448 (caption dup), 0449 (Exp2 matrices), 0457 (cohort-filter test); imagines awaiting discussion: 0450/0451/0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
4. Backlog: 0444 (census re-score), 0447 (hardcoded-size ratchet), 0441–0443, 0377.

## Open issues

- Census artifacts rebuild only in the primary checkout (archived outputs invisible from worktrees) — documented limitation, deferral 0444. (`census_bars.csv` untracked there awaits it.)
