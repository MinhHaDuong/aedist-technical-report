Last updated: 2026-06-12T19:10Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.tex`** (hand-curated LaTeX, tectonic + CI-built since #969) — report.tex is internal ("no future", author 2026-06-05). Landed 2026-06-12: **back-half restructure** (tracker 0560: de-anchored tests 0561, Extensions/Future-research arc 0562, annex reorder A–G 0563; + 0565 KB programme items) and the **final showstopper sweep** (tracker 0571: registration framing dropped 0567 — Exp 2 is a plain 2×2; claims/findings aligned 0568; repetitions compressed 0569; tone polished to author register + paragraph splits 0570). Integration reviews COHERENT both times; full suite green; PDF rebuilt and delivered to author. **Manuscript is ready for author reading-2 → arXiv sign-off.** Standing authorizations (author 2026-06-11): merge-review-merge cadence — merge each PR on APPROVED + green CI, no long-lived branches; genuinely new judgment calls stay needs-human. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-12T19:10Z -->

**Tickets:** 21 ready · 32 blocked — `erg ready tickets/` for full list
**Recent commits:**
  81e484bb Merge pull request #1040 from MinhHaDuong/chore/close-0571
  5bafae2c ticket(0571): close and archive — final showstopper sweep complete
  fe62760c Merge pull request #1039 from MinhHaDuong/t0570
  31671fb0 ticket(0570): close and archive — PR #1039
  61960eb5 0570: tone polish to the author's register + paragraph splits

## Next actions

1. **Author reading-2 of the rebuilt PDF** (sent 2026-06-12) → arXiv build, sign-off. The manuscript has passed restructure + showstopper sweep; remaining edits should be author's-taste only.
2. **In flight (author's bg raid, 2026-06-12 evening):** 0572 + 0566 — macro-source the §exp2 F1 literal pairs and ρ = 0.92 (same emitters, one PR).
3. **Next-paper seeds:** `docs/kb-design-note.md` (KB information-flow topologies + temporal-modal claim model, feeds the follow-on system paper); 0564 enumeration-budget audit (deferred, revisit at follow-on planning).
4. Independent code work any time: 0544 (rapidfuzz threshold validation). Imagines awaiting discussion: 0450, 0454. 0255–0262 deferred (Blocked-by 0435), owed to journal.
5. Backlog: 0520 (arm-1D extension, deferred); `erg ready tickets/` for the rest.

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).