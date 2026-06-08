Last updated: 2026-06-08T11:10Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.md`** — report.tex is internal ("no future", author 2026-06-05). main.md is structurally complete: v2.1 numbers (reference settled at **173 plants** by 0445; propagated 170→173 across main.md by 0444/PR #781), Annex E (reworked matrix on a landscape page, #771) + two Discussion future-work paragraphs (#767 fusion, #771 zero-reference coherence screen). 0445 blocker cleared. Remaining: blessed acknowledgements, full author read, arXiv build, sign-off. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-08T10:18Z -->

**Tickets:** 47 ready · 28 blocked — `erg ready tickets/` for full list
**Recent commits:**
  752fef5f Merge pull request #787 from MinhHaDuong/quickpr/ticket-0462-file-fix-parse-time-wildcard-20260608-095106
  265286cb ticket(0462): file — fix parse-time wildcard fragility in armN_flat stamp prereqs
  1011b3a1 Merge pull request #786 from MinhHaDuong/quickpr/ticket-0461-file-delete-on-error-across--20260608-094224
  d1998900 Merge pull request #783 from MinhHaDuong/chore/retire-erg-skills
  d8e783a9 ticket(0461): file — .DELETE_ON_ERROR across all build makefiles + adherence guard

## Sprint 2026-06-05 — CLOSED

Reference v2 (170 plants) adopted end-to-end: snapshot policy → aggregator (#760) → clean resnap (#764, snapshot = sole master copy, durable on main; restore: `git show origin/main:data/reference/raw/pipeline-2026-06-05.ods > <path>`) → adoption (#767: re-score Exp1–3, figures at 170, #547 prose corrected ×3, manuscript annex) → class fix + ratchet ticket (#769, 0447).

## Next actions

1. **0435 finalization** — acknowledgements (blessed wording), author read (incl. new coherence-screen paragraph), arXiv build. 0445 blocker cleared (173 settled + propagated).
2. 0446-review follow-ons: 0453 (two-level coherence scoring), 0455 (preprint figures EN sweep), 0448 (caption dup), 0449 (Exp2 matrices), 0457 (cohort-filter test); imagines awaiting discussion: 0450/0451/0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
3. Backlog: 0459 (re-derive+wire report.tex Exp3 decomposition table), 0461 (.DELETE_ON_ERROR build-wide + adherence guard), 0462 (armN stamp wildcard parse-time fragility), 0447 (hardcoded-size ratchet), 0441–0443, 0377.

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).

## Open issues

- (resolved by 0444/PR #781) Census now re-scores from `experiments/archive/outputs/` via the wired score.mk archive path; mart on v2.1 (173 plants), 669 rows.
