Last updated: 2026-06-11T09:10Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.tex`** (hand-curated LaTeX, tectonic-built — 0524 dropped pandoc/pandoc-crossref) — report.tex is internal ("no future", author 2026-06-05). The manuscript is structurally complete on the **177-plant reference (v2.4)**, reconciled by 0501/#909 (2026-06-10). **Figure polish (raid 2026-06-09):** gapless figures 1–7 (0483/#882), quality-floor veto polarity fixed (0487/#883). **Editorial round (0522/#935, 2026-06-10):** data-not-model spine, claim-first findings + captions, de-jargon, age-proofing — anchors author-blessed. Acknowledgements confirmed in (author 2026-06-10; full back-matter since 0509). Remaining: full author read, arXiv build, sign-off. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-10T21:15Z -->

**Tickets:** 24 ready · 33 blocked — `erg ready tickets/` for full list
**Recent commits:**
  ca25823d Merge pull request #936 from MinhHaDuong/quickpr/state-acknowledgements-confirmed-in-reco-20260610-210418
  6d2a876b STATE: acknowledgements confirmed in; record 0522 editorial round merged
  e5d4634f Merge pull request #935 from MinhHaDuong/claude/ticket-0522-editorial-reframe
  c04f003b ticket(0522): close and archive — PR #935
  90556531 0522: log anchor approval + full-pass execution

## Next actions

1. **0435 finalization, critical path (re-sequenced 2026-06-11):** 0524 execute (md→LaTeX conversion, decided Option 1) → 0531 macros-everywhere → 0532/0533 (author judgment: claim strength, factual fixes) → 0534 minors → 0486 → rebuild → re-review → send. Pre-arXiv prose panel (2026-06-11) verdict: not ready — stale numbers + claim-strength majors, filed as 0531–0534 (PR #948).
2. **0486 RATIFIED (author 2026-06-11):** the 2026-06-09 scope-lock stands — GEM + Wikipedia, annex, denominator 177 via `reference_plant_count()`. (The earlier "needs decision / GEM-only / 173" entry here was stale autogen; design dialogue trumps.) Ready to execute after 0524.
3. Imagines awaiting discussion: 0450, 0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
4. Backlog: 0520 (arm-1D wider-model extension, deferred); `erg ready tickets/` for the rest.

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).