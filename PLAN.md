# Plan: Distinguish refusals from failed parses in ResultSummary.status

## Problem

`_evaluate_qualitative()` in evaluate.py labels every orphan JSON (no CSV
companion) as `status="qualitative"`. That conflates three different things:

- **qualitative**: the prompt intentionally asked for non-table output
- **refusal**: the model explicitly declined to produce the table
- **error**: the model tried to produce a table but extraction failed

Additionally, measurements.jsonl is stale: 27 of 50 "qualitative" records
now have CSV companions (created by ticket 0040) and should be `"ok"`.

### Actual orphan inventory (11 files, no CSV)

**Refusals** (model explicitly said no):
- census/padme-gemma4-e2b-run{1,2,3} — "I am unable to provide..."
- frontier/gpt-5.4-run1 — "I'm sorry, but I can't reliably produce..."
- frontier/grok-4.20-run1 — "I must decline to produce this document..."

**Failed parses** (model tried, extract.py couldn't parse):
- census/padme-qwen3.5-2b-run3 — CSV with no name column
- census/padme-qwen3.5-4b-run3 — pipe-delimited, missing name column
- frontier/ernie-4.5-21b-a3b-thinking-run1 — long prose with pipe tables
- rag/granite3.3-8b-run{1,2,3} — truncated/malformed fenced CSVs

**Empty** (none currently on disk; some referenced files deleted)

## Design

### Status vocabulary (ResultSummary.status)

| Value | Meaning |
|-------|---------|
| `ok` | CSV extracted and scored (existing, unchanged) |
| `refusal` | **New.** Model explicitly declined to produce the table |
| `error` | **New.** Model responded but extraction/parsing failed |
| `empty` | **New.** Response field was missing or blank |
| `qualitative` | Prompt intentionally asked for non-table output |

No dotfiles. The status lives in the existing `.record.json` status field.

### Classification logic

In `_evaluate_qualitative()` (evaluate.py:291), after reading the JSON:

1. Extract the response text (same logic as extract.py: `response` field
   or joined assistant turns).
2. If response is empty/missing → `status="empty"`.
3. If response has content, run extract.py's table-detection functions
   (fenced blocks, pipe tables, inline CSV) on the text:
   - **No table-like content found** → `status="refusal"`.
     The model wrote prose only; it didn't attempt a table.
   - **Table-like content found but no CSV extracted** →
     `status="error"`. The model tried but the output was unparseable.
4. `status="qualitative"` is **never auto-assigned** from the orphan-JSON
   path. Reserved for experiments where the prompt was qualitative by
   design (scenarios, skill_plans under `experiments/qualitative/`).

This reuses existing detection functions from extract.py — no new
heuristics or keyword lists needed.

### Changes

1. **`src/aedist/schema.py`** (~line 151)
   - Update the `status` field description to document the vocabulary:
     `"ok | refusal | error | empty | qualitative"`.

2. **`src/aedist/evaluate.py`** (`_evaluate_qualitative`, ~line 291)
   - Import `extract_fenced_blocks`, `_extract_pipe_tables`,
     `fallback_extract_inline_csv` from `aedist.extract`.
   - Read the response text from the JSON (handle both `response` string
     and `turns` list, same as extract.py lines 304-311).
   - If response is empty → `ResultSummary(status="empty")`.
   - Run table detection on response text. If candidates found →
     `ResultSummary(status="error")`. Else →
     `ResultSummary(status="refusal")`.

3. **`tests/test_evaluate.py`** (or equivalent)
   - Add tests for `_evaluate_qualitative` covering:
     - JSON with prose-only response → status="refusal"
     - JSON with malformed table content → status="error"
     - JSON with empty/missing response → status="empty"
     - JSON with multiturn format, no table → status="refusal"

4. **Rebuild measurements**
   - `make -C experiments rebuild-measurements` to regenerate all
     `.record.json` and `measurements.jsonl`.
   - Expected outcome: 27 former "qualitative" records become "ok"
     (they now have CSVs), ~5 become "refusal", ~6 become "error",
     0 remain "qualitative".

### Files touched

- `src/aedist/schema.py` — field description
- `src/aedist/evaluate.py` — ~15 lines in `_evaluate_qualitative`
- `tests/test_evaluate.py` — new test cases
- `experiments/outputs/**/*.record.json` — regenerated (not hand-edited)
- `measurements.jsonl` — regenerated
