# Agent workflow rules — AEDIST

## Test one before blasting

Before any parallel batch of API calls: (1) dry-run to check prompt assembly, (2) run 1 real call per regime, (3) inspect output tokens, wall time, content quality, (4) then launch the full batch.

**Why:** Phase 1 burned ~$5 on 26 models before anyone noticed they were answering from memory. One test call catches it in 30 seconds.

## Audit before instrumenting

Before building new diagnostic infrastructure (schema changes, sweep options, new tables) for a suspected phenomenon, run a retrospective check on existing data to confirm the phenomenon is actually present. If the premise fails, close the ticket with a documented non-finding and no code.

**Why:** Ticket 0073 proposed schema changes + runner path + tex table to diagnose cold-start drift that a 5-minute check on measurements.jsonl did not support.

## Derive prose from generated artifacts, never from agent enumeration

Rule: harness `rules/prose/_all.md` (every empirical number comes from a committed generated artifact; agent counts are hypotheses until the script runs). Local guard: an adherence test re-derives the number from the artifact via an independent parse (`tests/test_audit_exp2_wiki_citations.py` for the 0452 path).

**Why:** Ticket 0452 (2026-06-06): both the Imagine and Plan agents
surveyed the Exp2 corpus and concluded the Wikipedia-ban violations were
"concentrated in Mistral; the remaining three agents clean." The
feasibility cross-check found an OpenAI optimised-arm violation both had
missed; the run-level detail shifted again when the script ran (one
Mistral violation was bibliography-only). Prose drafted from either
enumeration would have shipped factually wrong — the generated CSV was
right three times where agent surveys were wrong twice.

## Prefer skills over commands

Rule: harness `rules/authoring-skills.md` (a new slash-invocable automation is a skill, not a legacy command). Local scope: user-level skills go to `~/.claude/skills/` (IDH); project-level only for skills inseparable from this repo's harness (e.g. git-erg ticket-* skills). Skills must gracefully degrade when project-specific conventions are absent (not stated in the harness; kept here).
