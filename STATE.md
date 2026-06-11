Last updated: 2026-06-11T15:40Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.tex`** (hand-curated LaTeX, tectonic + CI-built since #969) — report.tex is internal ("no future", author 2026-06-05). Merged 2026-06-11: 0524 conversion, 0533 factual fixes, 0532 ratified abstract/conclusion + 0534 minors (#971 superseding #967/#968), 0542 semantic-LaTeX cleanup. **Author reading-2 deferred until the reading-1 wave lands** (DAG below). Standing authorizations (author 2026-06-11): merge-review-merge cadence — merge each PR on APPROVED + green CI, no long-lived branches; override mode — prose implementing the author's reading-1 briefs merges without pre-blessing, reading-2 of the merged PDF is the review; genuinely new judgment calls stay needs-human. 0171 cross-eval OUT (journal delta).

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

1. **Reading-1 wave (critical path to reading-2):** structural 0537/0538/0540 (parallel worktrees, sequential merges) → 0539 → 0543+0541 together (em-dash overlap) → 0531 macros LAST (settled prose only). Sequencing encoded as Blocked-by in the ticket DAG. After the wave: rebuild manuscript PDF → author reading-2 → arXiv build, sign-off.
2. **0486 RATIFIED (author 2026-06-11):** GEM + Wikipedia, annex, denominator 177 via `reference_plant_count()`. Unblocked (0524 merged).
3. Independent code work any time: 0544 (rapidfuzz threshold validation). Imagines awaiting discussion: 0450, 0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
4. Backlog: 0520 (arm-1D extension, deferred); `erg ready tickets/` for the rest.

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).