# 2026-11-09 — adoption of the v8 repository memory (ticket 0687)

Context: the project is active (STATE.md updated 2026-11-04, merges on
2026-11-09) and had no `memory/` directory. Its memory lived in the Claude
Code native auto-memory (197 notes and an index) and in a harness export of
the same store. The ticket's template predates the deployed projects; its
2026-11-09 note names padme, sen-causal-reading, JETP-observer and
climate-finance-het as the reference, and padme's layout was followed.

What was done:
- Inventoried every source ([SOURCES.md](../../SOURCES.md)): 111 notes plus
  one in-repo untracked note consolidated into eight topics with
  attribution; 64 tombstones, 5 stale, 11 harness-generic and 2
  other-project notes dropped; 5 notes left out for audience, since this
  repository is public and has no age-encryption mechanism.
- Facts were checked against the tree before consolidation. Three notes had
  gone stale in detail: the preprint is now `slides/manuscript/main.tex`
  (c911bf0c), the reference counts 177 plants (v2.4), and the erg binary is
  `tickets/erg`.
- AGENTS.md gained a "Project memory" reading section and a `memory/` row
  in its configuration table.
- `memory/DREAM.md` was not created: documented exception (no deployed
  project carries one).

Loading probe (Claude Code, haiku, `claude -p`, tools disallowed, stdin
closed): started in the adoption worktree, the model answered YES and quoted
the section's first sentence ("Read memory/MEMORY.md at task start when it
exists.", link markup removed here);
started in the unmodified primary checkout on main, it answered NO and
listed the existing sections. Codex and Pi were not probed.

Failure scenarios: if `memory/` is absent (older checkout, partial
revert), AGENTS.md says missing memory does not block work and asks for the
incomplete installation to be reported; the documents of record (STATE.md,
MASTERPLAN.md, ADR.md, tickets) are unaffected. If a link breaks (a moved
document or topic), the reader loses one pointer, not the fact: topics name
their source notes by filename and blob id, and a link check over `memory/`
and the AGENTS.md section ran clean at adoption.

The native stores stay active and untouched; rollback is a revert of the
adoption merge.
