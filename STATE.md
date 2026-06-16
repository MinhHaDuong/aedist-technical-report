Last updated: 2026-06-16T08:09Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: dissemination → arXiv

Preprint (`slides/manuscript/main.tex`) diffused to Econom'IA 2026 participants; tagged `economia-2026-report` (2da83d04, 65 pp) and **released on GitHub with the PDF (0666)**. Prior: reading-2/3 waves + a 4-reviewer external panel (tracker 0644 — prose findings fixed, experiments deferred post-arXiv). **Dissemination tracker 0663**: HAL deposit (0664, gated/SWORD) is the next step → arXiv-via-HAL (0665), homepage (0667), CIRED (0668). **Spring-cleanup tracker 0669** (publications/ rehome, data+derived→experiments, root tidy) is parked behind dissemination. Standing auth: merge-review-merge cadence; new judgment calls stay needs-human.

## Status
<!-- generated 2026-06-16T08:09Z -->

**Tickets:** 37 ready · 49 blocked — `erg ready tickets/` for full list
**Recent commits:**
  ac4ebe19 Merge pull request #1153 from MinhHaDuong/worktree-t0673
  40c84165 ticket(0673): close and archive — PR #1153
  8cf420cd test(0673): land NumRefPlants single-source adherence guard
  9cdc9a8b Merge pull request #1150 from MinhHaDuong/quickpr/tickets-open-0673-land-the-numrefplants--20260616-055417
  020ce284 fix(0673): drop invalid Ticket-ref erg header (PR-body convention, not a file header)

## Next: general reading skills (prose-quality pass)

Build 3 reusable IDH skills, applied after every substantial rewrite, for all texts (specced 2026-06-14):
1. **descaffold** — strip instruction/scaffolding leak from prose (generalises 0592; mechanical-first).
2. **voiceprint** — flag LLMisms / dry-academism vs the author's voice. PARKED (corpus, not recon): chemin-de-voix `author-voice-{en,fr}` is email-dominated — sampling by volume learns email register, not article voice. Needs an article-prose corpus (publication PDFs from minh.haduong.com, manuscripts) stratified away from the email majority (emails = contrast class only), reusing reading-1 work (closed 0532/0570), THEN author ratifies the trait list before it enforces.
3. **caption-altitude** — figure captions one reading level below body, non-redundant (FR readability).
Each = mechanical helper + LLM lens + editorial-brief entry + /review-pr-prose lens → then one global main.tex pass → arXiv sign-off. Follow-ups open: 0594 (report.tex Qwen), 0595 (test scanner). Backlog via `erg ready` (kb-design-note system paper, 0564, 0544).

## Next: methods contribution

Ratified internal-coherence run-screen roadmap captured under **tracker 0464** (Paper A, manuscript MVP: 0201 scorer → 0466 model-grain floor heatmap → 0467 run-grain validation → 0468 table move → 0469 slides sync). The 0466 heatmap's coherence-veto column was rendering inverted (fixed by **0487/#883**, 2026-06-09); 0488 was closed void (its premise — missing coherence columns — was false; 0453 had already added them). **0464 remains blocked by 0201** (the full reference-free composite scorer, post-preprint, contested aggregation unresolved). Fil rouge = §2 conjunctive quality bar = zero-is-trash. Information fusion (run-as-unit) deferred to **tracker 0465** (Paper B: 0470/0471/0398/0399-consensus/0293).
