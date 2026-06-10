Last updated: 2026-06-09T09:23Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.md`** — report.tex is internal ("no future", author 2026-06-05). main.md is structurally complete: v2.1 numbers (reference settled at **173 plants** by 0445; propagated 170→173 across main.md by 0444/PR #781), Annex E (reworked matrix on a landscape page, #771) + two Discussion future-work paragraphs (#767 fusion, #771 zero-reference coherence screen). 0445 blocker cleared. **Figure polish (raid 2026-06-09):** figures renumbered to a gapless 1–7 (0483/#882, "Figure 2b" eliminated, guarded by `test_manuscript_figure_numbering.py`); Figure 4 quality-floor heatmap veto polarity fixed (0487/#883 — Haiku + gpt-oss-120b now correctly disqualified, strong models green; the committed PDF had been stale and a naive rebuild would have wrongly failed every strong model). **Editorial round (0522/#935, merged 2026-06-10):** data-not-model spine, claim-first findings + captions, de-jargon, age-proofing — anchors author-blessed. Acknowledgements confirmed in (author 2026-06-10; full back-matter since 0509). Remaining: full author read, arXiv build, sign-off. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-09T09:23Z -->

**Tickets:** 21 ready · 24 blocked — `erg ready tickets/` for full list
**Recent commits:**
  68b266ef Merge pull request #885 from MinhHaDuong/quickpr/ticket-0492-variability-screen-test-doub-20260609-091450
  c4f8b606 ticket(0492): variability-screen test double-counts colocated reconciliation CSVs
  b1c23310 Merge pull request #884 from MinhHaDuong/quickpr/ticket-0491-heatmap-pdf-glyph-fallback-f-20260609-091045
  5403c9ec ticket(0491): heatmap PDF ≥-glyph fallback follow-up (surfaced in 0487)
  bbb6a1e4 fix(0487): correct inverted-polarity coherence veto in Exp1 quality-floor heatmap

## Sprint 2026-06-05 — CLOSED

Reference v2 (170 plants) adopted end-to-end: snapshot policy → aggregator (#760) → clean resnap (#764, snapshot = sole master copy, durable on main; restore: `git show origin/main:data/reference/raw/pipeline-2026-06-05.ods > <path>`) → adoption (#767: re-score Exp1–3, figures at 170, #547 prose corrected ×3, manuscript annex) → class fix + ratchet ticket (#769, 0447).

## Next actions

1. **0435 finalization** — author read (incl. new coherence-screen paragraph + 0522 editorial pass), arXiv build. Acknowledgements in. 0445 blocker cleared.
2. **0486 needs an AUTHOR DECISION** (deferred in raid 2026-06-09, "conference remark"): the GEM/OSM/Wikipedia coverage table cannot ship as written — Wikipedia is a protocol-banned source (§3.4), OSM-via-Overpass is non-reproducible, and the 173-vs-180 count is contested. Recommendation recorded on the ticket: **GEM-only** (data already in-repo), placed in **Annex B** (line 203 already flags GEM reconciliation as deferred), pinned to **173**. Ratify the 3 choices → quick execute.
3. Raid follow-ups (open, unblocked): 0491 (heatmap PDF "Capacity≥0"→"Capacityz0" ≥-glyph fallback), 0492 (fix `test_variability_screen_regression` regex — matches colocated `reconciliation_*.csv`; the only reason local `make check` fails on padme, **green on fresh checkout/doudou**).
4. 0446-review follow-ons: 0455 (preprint figures EN sweep), 0448 (caption dup), 0449 (Exp2 matrices), 0457 (cohort-filter test); imagines awaiting discussion: 0450/0451/0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
5. Backlog: 0459 (re-derive+wire report.tex Exp3 decomposition table), 0447 (hardcoded-size ratchet), 0441–0443, 0377.

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).

## Open issues

- (resolved by 0444/PR #781) Census now re-scores from `experiments/archive/outputs/` via the wired score.mk archive path; mart on v2.1 (173 plants), 669 rows.
