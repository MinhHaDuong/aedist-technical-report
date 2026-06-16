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

## Worktree paths

In an `EnterWorktree` session, `Edit`/`Write`/`Read` tools accept any absolute path. Edits at `/home/haduong/<repo>/<file>` go to the **main repo**, not the worktree. Always use worktree-rooted paths. Confirm with `pwd` and `git branch --show-current` before committing — if branch is `main`, stop.

## Closing tickets and merge requests

Never close forge tickets or merge requests without explicit user confirmation, even when acceptance criteria appear met. Recommend closures but always ask first, especially never close merge requests belonging to other sessions or worktrees.

## JSON EOF newline policy

All single-object JSON files written by this project end with exactly one trailing newline (`\n`).

**Applies to:** `*.json` output files — `json.dump()` + `f.write("\n")`, and `.write_text(json.dumps(...) + "\n")`, and `.write_text(model.model_dump_json(...) + "\n")`.

**Does not apply to:** JSONL writers (`to_jsonl_line() + "\n"` per record, no extra newline after the last line), or in-memory `json.dumps()` that is not written to a file.

**Why:** Newline-only diffs (`No newline at end of file`) are non-semantic but noisy in reviews and audits. Verified by `tests/test_json_eof_newline.py` (`@pytest.mark.adherence`).
