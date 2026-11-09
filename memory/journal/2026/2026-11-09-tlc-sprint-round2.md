# TLC sprint round 2: rules map landed, rules trim parked (2026-11-09)

Team-lead run 16:55Z-17:30Z, unattended, two tooling tickets.

## Events

- Ticket 0677's premise was stale on three counts. The per-edit
  injection hook it targets was deleted (harness ticket 0976); the
  manifest now feeds `prose_predicate.py --axes` for review routing.
  `slides/manuscript/main.tex` is `\documentclass{article}` and English,
  not a French techreport. A blanket `lang = "fr"` would have mislabelled
  the preprint, the English deck, README and most docs. The manifest
  landed with `default_lang = "en"` and French mapped explicitly:
  `report/**/*.tex`, `slides/slides.tex`, `ADR.md` and three `docs/`
  notes (PR #1200).
- Gaze's first pass on #1200 caught the French Markdown files; the second
  ran a stopword scan over 940 tracked prose files. One French file is
  still unmapped: `publications/journal-article/notes/arbitrage-2026-02/options.md`
  (no doctype; harmless unless a prose MR edits it with a manuscript).
- Ticket 0682: the harness inventory doc it cites
  (`docs/2026-10-09-t0375-project-rules-inventory.md`) does not exist.
  Several "promoted" rules are stated in the harness only for one doctype
  (`doctype/article.md`) or only for skills (`authoring-skills.md`), so
  deleting them would narrow their scope to the preprint. Gaze found the
  first trim lost a graceful-degradation clause and narrowed the
  heading and bibliography rules; the fix kept them locally. The gate
  ruled NEEDS-AUTHOR (PR #1201): three listed rules are kept rather than
  removed, which departs from the ticket's first exit criterion.

## References

PRs #1200 (merged at e608b588), #1201 (open, NEEDS-AUTHOR); tickets
0677, 0682; reviews rv-20261109-pr-1200-353f, rv-20261109-pr-1201-a576.
