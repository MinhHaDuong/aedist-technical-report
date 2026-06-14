Last updated: 2026-06-14T03:45Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.tex`** (hand-curated LaTeX, tectonic + CI-built). **Reading-2 fix wave COMPLETE 2026-06-14** (tracker 0578: 13 children 0579–0592 + prereq 0575, each Sonnet-gated + verify-checked; integration review PASS, manuscript builds clean). Prior landings: back-half restructure (0560), showstopper sweep (0571). **Ready for arXiv sign-off** pending (a) author confirm-close 0578, (b) the general-reading-skills prose pass below. Standing auth (2026-06-11): merge-review-merge cadence; new judgment calls stay needs-human.

## Status
<!-- generated 2026-06-14T03:45Z -->
**Tickets:** 27 ready — `erg ready tickets/` for full list
**Recent commits:**
  ebac7e01 Merge #1066 — annotate 0578 wave complete; file 0595
  654c42a7 Merge #1065 — 0592 register/promises sweep (last child)
  ec81cfb8 Merge #1064 — 0591 codename/code-ref sweep
  (reading-2 wave 0579–0592 + prereq 0575 all merged)

## Next: general reading skills (prose-quality pass)

Build 3 reusable IDH skills, applied after every substantial rewrite, for all texts (specced 2026-06-14):
1. **descaffold** — strip instruction/scaffolding leak from prose (generalises 0592; mechanical-first).
2. **voiceprint** — flag LLMisms / dry-academism vs the author's voice. PARKED (corpus, not recon): chemin-de-voix `author-voice-{en,fr}` is email-dominated — sampling by volume learns email register, not article voice. Needs an article-prose corpus (publication PDFs from minh.haduong.com, manuscripts) stratified away from the email majority (emails = contrast class only), reusing reading-1 work (closed 0532/0570), THEN author ratifies the trait list before it enforces.
3. **caption-altitude** — figure captions one reading level below body, non-redundant (FR readability).
Each = mechanical helper + LLM lens + editorial-brief entry + /review-pr-prose lens → then one global main.tex pass → arXiv sign-off. Follow-ups open: 0594 (report.tex Qwen), 0595 (test scanner). Backlog via `erg ready` (kb-design-note system paper, 0564, 0544).

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).
