# Agent workflow rules — AEDIST

## Test one before blasting

Before any parallel batch of API calls: (1) dry-run to check prompt assembly, (2) run 1 real call per regime, (3) inspect output tokens, wall time, content quality, (4) then launch the full batch.

**Why:** Phase 1 burned ~$5 on 26 models before anyone noticed they were answering from memory. One test call catches it in 30 seconds.

## Audit before instrumenting

Before building new diagnostic infrastructure (schema changes, sweep options, new tables) for a suspected phenomenon, run a retrospective check on existing data to confirm the phenomenon is actually present. If the premise fails, close the ticket with a documented non-finding and no code.

**Why:** Ticket 0073 proposed schema changes + runner path + tex table to diagnose cold-start drift that a 5-minute check on measurements.jsonl did not support.

## Derive prose from generated artifacts, never from agent enumeration

When manuscript or report prose quotes empirical numbers, the numbers come
from the committed generated artifact (CSV, macros file) produced by the
pipeline — never from an upstream agent's grep notes, plan enumeration, or
ticket annotations. Treat agent-surveyed counts as hypotheses to verify:
(1) run the script, (2) inspect the artifact, (3) write the prose from it,
(4) guard the literal with an adherence test that re-derives the number
from the artifact via an independent parse.

**Why:** Ticket 0452 (2026-06-06): both the Imagine and Plan agents
surveyed the Exp2 corpus and concluded the Wikipedia-ban violations were
"concentrated in Mistral; the remaining three agents clean." The
feasibility cross-check found an OpenAI optimised-arm violation both had
missed; the run-level detail shifted again when the script ran (one
Mistral violation was bibliography-only). Prose drafted from either
enumeration would have shipped factually wrong — the generated CSV was
right three times where agent surveys were wrong twice.

## Prefer skills over commands

New slash-invocable automation → `.claude/skills/<name>/SKILL.md`, never `.claude/commands/*.md` (legacy format). User-level skills go to `~/.claude/skills/` (IDH); project-level only for skills inseparable from this repo's harness (e.g. git-erg ticket-* skills). Skills must gracefully degrade when project-specific conventions are absent.
